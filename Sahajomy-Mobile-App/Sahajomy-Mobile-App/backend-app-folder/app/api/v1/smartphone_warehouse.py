"""Device-assisted, permission-controlled warehouse operations."""

import re
import secrets
from datetime import datetime
from decimal import Decimal
from typing import Literal
from uuid import UUID

from app.core.audit import log_action
from app.core.dependencies import get_customer
from app.core.workspace_security import WorkspaceContext, require_permission
from app.database import get_db
from app.models.air_cargo import ExpressAirCargoBooking
from app.models.cargo_customs import (
    CargoCustomer,
    ManualCargoIntake,
    ManualCargoIntakeItem,
)
from app.models.cargo_workspace import CargoBranch, CargoCompany
from app.models.container import Container, SeaBooking
from app.models.shipping_mark import ShippingMark
from app.models.smartphone_warehouse import (
    LoadingScan,
    LoadingSession,
    ParcelBookingLink,
    ParcelScanEvent,
    ShipmentMilestone,
    WarehouseParcel,
)
from app.models.user import User
from app.services.manual_cargo_tracking import create_manual_intake_tracking_event
from app.services.realtime_notifications import create_notification
from app.services.subscriptions import consume_usage, require_feature
from app.services.tracking_number import ensure_manual_intake_tracking_number
from app.services.warehouse_tracking import (
    platform_label_reference,
    record_booking_warehouse_event,
)
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import or_
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

cargo_router = APIRouter(
    prefix="/cargo/warehouse-mobile", tags=["Warehouse Device Operations"]
)
customer_router = APIRouter(
    prefix="/customer/smart-parcels", tags=["Customer Warehouse Parcels"]
)


def require_automation_permission(key: str):
    permission_dependency = require_permission(key)

    def dependency(
        ctx: WorkspaceContext = Depends(permission_dependency),
        db: Session = Depends(get_db),
    ) -> WorkspaceContext:
        require_feature(db, ctx.company_id, "warehouse_automation")
        return ctx

    return dependency


def _consume_automation(
    db: Session,
    ctx: WorkspaceContext,
    action: str,
    *,
    idempotency_key: str | None = None,
) -> None:
    consume_usage(
        db,
        ctx.company_id,
        "automation_events",
        action=action,
        created_by_id=ctx.user.id,
        idempotency_key=idempotency_key,
    )


def _branch(
    db: Session, ctx: WorkspaceContext, branch_id: UUID | None = None
) -> CargoBranch:
    selected = branch_id or ctx.branch_id
    if not selected:
        raise HTTPException(
            422, "Select a cargo branch before performing warehouse work."
        )
    row = (
        db.query(CargoBranch)
        .filter(
            CargoBranch.id == selected,
            CargoBranch.company_id == ctx.company_id,
            CargoBranch.status == "active",
        )
        .first()
    )
    if not row or not row.warehouse_id:
        raise HTTPException(404, "The selected branch has no active warehouse.")
    if ctx.membership.role.scope != "company" and row.id != ctx.branch_id:
        raise HTTPException(403, "You are not assigned to this branch.")
    return row


def _customer(db: Session, ctx: WorkspaceContext, customer_id: UUID) -> CargoCustomer:
    company = db.query(CargoCompany).filter(CargoCompany.id == ctx.company_id).one()
    row = (
        db.query(CargoCustomer)
        .filter(
            CargoCustomer.id == customer_id,
            CargoCustomer.cargo_admin_id == company.created_by_user_id,
            CargoCustomer.status == "active",
        )
        .first()
    )
    if not row:
        raise HTTPException(404, "Customer is not available in this cargo company.")
    return row


def _parcel(
    db: Session, ctx: WorkspaceContext, parcel_id: UUID, lock=False
) -> WarehouseParcel:
    query = db.query(WarehouseParcel).filter(
        WarehouseParcel.id == parcel_id, WarehouseParcel.company_id == ctx.company_id
    )
    if ctx.branch_id and ctx.membership.role.scope != "company":
        query = query.filter(WarehouseParcel.branch_id == ctx.branch_id)
    row = query.with_for_update().first() if lock else query.first()
    if not row:
        raise HTTPException(404, "Parcel was not found in the active workspace.")
    return row


def _payload(row: WarehouseParcel) -> dict:
    return {
        "id": str(row.id),
        "intake_id": str(row.intake_id) if row.intake_id else None,
        "parcel_code": row.parcel_code,
        "tracking_number": row.tracking_number,
        "shipping_mark": row.shipping_mark,
        "carrier": row.carrier,
        "condition": row.condition,
        "status": row.status,
        "carton_count": row.carton_count,
        "weight_kg": float(row.weight_kg or 0),
        "length_cm": float(row.length_cm or 0),
        "width_cm": float(row.width_cm or 0),
        "height_cm": float(row.height_cm or 0),
        "cbm": float(row.cbm or 0),
        "photo_urls": row.photo_urls or [],
        "notes": row.notes,
        "customer_id": str(row.customer_id),
        "customer_name": row.customer.name if row.customer else None,
        "branch_id": str(row.branch_id),
        "warehouse_id": str(row.warehouse_id),
        "received_at": row.received_at.isoformat(),
    }


class ScanInput(BaseModel):
    code: str = Field(min_length=2, max_length=4000)
    idempotency_key: str = Field(min_length=8, max_length=80)


class ParcelInput(BaseModel):
    customer_id: UUID
    scan_event_id: UUID | None = None
    tracking_number: str | None = Field(None, max_length=100)
    shipping_mark: str | None = Field(None, max_length=100)
    carrier: str | None = Field(None, max_length=120)
    condition: Literal["good", "damaged", "wet", "opened", "unknown"] = "good"
    carton_count: int = Field(1, ge=1, le=100000)
    weight_kg: Decimal = Field(Decimal("0"), ge=0)
    length_cm: Decimal = Field(Decimal("0"), ge=0)
    width_cm: Decimal = Field(Decimal("0"), ge=0)
    height_cm: Decimal = Field(Decimal("0"), ge=0)
    photo_urls: list[str] = Field(default_factory=list, max_length=12)
    notes: str | None = Field(None, max_length=2000)


def _scan_booking_match(db: Session, ctx: WorkspaceContext, raw_code: str, code: str):
    """Resolve a platform label, booking tracking number, or shipping mark."""
    company = db.query(CargoCompany).filter(CargoCompany.id == ctx.company_id).one()
    label_reference = platform_label_reference(raw_code)
    sea_booking = None
    air_booking = None
    mark = None

    if label_reference and label_reference[0] == "sea":
        sea_booking = (
            db.query(SeaBooking)
            .join(Container)
            .filter(
                SeaBooking.id == label_reference[1],
                Container.admin_id == company.created_by_user_id,
            )
            .first()
        )
    elif label_reference and label_reference[0] == "air":
        air_booking = (
            db.query(ExpressAirCargoBooking)
            .filter(
                ExpressAirCargoBooking.id == label_reference[1],
                ExpressAirCargoBooking.cargo_admin_id == company.created_by_user_id,
            )
            .first()
        )

    if not sea_booking and not air_booking:
        mark = (
            db.query(ShippingMark)
            .filter(ShippingMark.shipping_mark_code == code)
            .first()
        )
        if mark and mark.sea_booking:
            container = mark.sea_booking.container
            sea_booking = (
                mark.sea_booking
                if container and container.admin_id == company.created_by_user_id
                else None
            )
        elif mark and mark.air_booking:
            air_booking = (
                mark.air_booking
                if mark.air_booking.cargo_admin_id == company.created_by_user_id
                else None
            )

    if not sea_booking and not air_booking:
        air_booking = (
            db.query(ExpressAirCargoBooking)
            .filter(
                ExpressAirCargoBooking.cargo_admin_id == company.created_by_user_id,
                or_(
                    ExpressAirCargoBooking.tracking_number == code,
                    ExpressAirCargoBooking.airway_bill_number == code,
                ),
            )
            .first()
        )

    booking = sea_booking or air_booking
    if booking and not mark:
        mark = booking.shipping_mark
    owner_user_id = (
        sea_booking.user_id
        if sea_booking
        else air_booking.customer_id if air_booking else None
    )
    customer = (
        db.query(CargoCustomer)
        .filter(
            CargoCustomer.cargo_admin_id == company.created_by_user_id,
            CargoCustomer.linked_user_id == owner_user_id,
            CargoCustomer.status == "active",
        )
        .first()
        if owner_user_id
        else None
    )
    return sea_booking, air_booking, mark, customer


class ParcelPatch(BaseModel):
    condition: Literal["good", "damaged", "wet", "opened", "unknown"] | None = None
    status: (
        Literal[
            "received",
            "booked",
            "loading",
            "loaded",
            "in_transit",
            "arrived",
            "ready",
            "collected",
            "held",
        ]
        | None
    ) = None
    weight_kg: Decimal | None = Field(None, ge=0)
    length_cm: Decimal | None = Field(None, ge=0)
    width_cm: Decimal | None = Field(None, ge=0)
    height_cm: Decimal | None = Field(None, ge=0)
    photo_urls: list[str] | None = Field(None, max_length=12)
    notes: str | None = Field(None, max_length=2000)


class BookingSelection(BaseModel):
    booking_type: Literal["sea", "air", "shipment"]
    booking_id: UUID
    parcel_ids: list[UUID] = Field(min_length=1, max_length=500)


class LoadingStart(BaseModel):
    booking_type: Literal["sea", "air", "shipment"]
    booking_id: UUID
    reference: str = Field(min_length=2, max_length=100)


class LoadingCode(BaseModel):
    code: str = Field(min_length=2, max_length=120)


class MilestoneInput(BaseModel):
    booking_type: Literal["sea", "air", "shipment"]
    booking_id: UUID
    milestone: Literal[
        "loaded", "departed", "in_transit", "arrived", "customs", "ready_for_collection"
    ]
    location: str | None = Field(None, max_length=160)
    note: str | None = Field(None, max_length=2000)
    occurred_at: datetime | None = None


@cargo_router.post("/scan-events")
def register_scan(
    body: ScanInput,
    db: Session = Depends(get_db),
    ctx: WorkspaceContext = Depends(require_automation_permission("parcel.receive")),
):
    branch = _branch(db, ctx)
    existing = (
        db.query(ParcelScanEvent)
        .filter(
            ParcelScanEvent.company_id == ctx.company_id,
            ParcelScanEvent.idempotency_key == body.idempotency_key,
        )
        .first()
    )
    if existing:
        metadata = existing.metadata_json or {}
        return {
            "scan_event_id": str(existing.id),
            "result": existing.result,
            "confidence": float(existing.confidence),
            "parcel_id": str(existing.parcel_id) if existing.parcel_id else None,
            **metadata,
        }
    _consume_automation(
        db,
        ctx,
        "warehouse_device_parcel_scanned",
        idempotency_key=f"warehouse-scan:{ctx.company_id}:{body.idempotency_key}",
    )
    normalized = re.sub(r"[^A-Z0-9-]", "", body.code.upper())[:120]
    parcel = (
        db.query(WarehouseParcel)
        .filter(
            WarehouseParcel.company_id == ctx.company_id,
            or_(
                WarehouseParcel.parcel_code == normalized,
                WarehouseParcel.tracking_number == normalized,
                WarehouseParcel.shipping_mark == normalized,
            ),
        )
        .first()
    )
    company = db.query(CargoCompany).filter(CargoCompany.id == ctx.company_id).one()
    sea_booking, air_booking, mark, booking_customer = _scan_booking_match(
        db, ctx, body.code, normalized
    )
    customer = booking_customer or (
        db.query(CargoCustomer)
        .filter(
            CargoCustomer.cargo_admin_id == company.created_by_user_id,
            CargoCustomer.customer_reference == normalized,
        )
        .first()
    )
    result = (
        "duplicate"
        if parcel
        else "matched" if customer or sea_booking or air_booking else "unmatched"
    )
    confidence = (
        Decimal("100")
        if parcel or customer or sea_booking or air_booking
        else Decimal("0")
    )
    metadata = {
        "customer_id": str(customer.id) if customer else None,
        "booking_type": "sea" if sea_booking else "air" if air_booking else None,
        "booking_id": (
            str((sea_booking or air_booking).id) if sea_booking or air_booking else None
        ),
        "sea_booking_id": str(sea_booking.id) if sea_booking else None,
        "air_booking_id": str(air_booking.id) if air_booking else None,
        "tracking_number": (air_booking.tracking_number if air_booking else None),
        "shipping_mark": mark.shipping_mark_code if mark else None,
        "match_reason": (
            "Exact Sahajomy booking label"
            if sea_booking or air_booking
            else "Exact customer reference" if customer else None
        ),
    }
    event = ParcelScanEvent(
        company_id=ctx.company_id,
        branch_id=branch.id,
        warehouse_id=branch.warehouse_id,
        parcel_id=parcel.id if parcel else None,
        raw_code=body.code,
        normalized_code=normalized,
        result=result,
        confidence=confidence,
        metadata_json=metadata,
        idempotency_key=body.idempotency_key,
        scanned_by_id=ctx.user.id,
    )
    db.add(event)
    db.commit()
    db.refresh(event)
    log_action(
        db,
        "warehouse_parcel_scanned",
        ctx.user.id,
        "parcel_scan_event",
        event.id,
        {
            "company_id": str(ctx.company_id),
            "branch_id": str(branch.id),
            "result": result,
        },
    )
    db.commit()
    return {
        "scan_event_id": str(event.id),
        "result": result,
        "confidence": float(confidence),
        "customer_id": str(customer.id) if customer else None,
        "parcel": _payload(parcel) if parcel else None,
        **metadata,
    }


@cargo_router.get("/unmatched-scans")
def unmatched_scans(
    db: Session = Depends(get_db),
    ctx: WorkspaceContext = Depends(require_automation_permission("parcel.view")),
):
    branch = _branch(db, ctx)
    rows = (
        db.query(ParcelScanEvent)
        .filter(
            ParcelScanEvent.company_id == ctx.company_id,
            ParcelScanEvent.branch_id == branch.id,
            ParcelScanEvent.result == "unmatched",
        )
        .order_by(ParcelScanEvent.created_at.desc())
        .limit(200)
        .all()
    )
    return [
        {
            "id": str(r.id),
            "code": r.normalized_code,
            "raw_code": r.raw_code,
            "created_at": r.created_at.isoformat(),
        }
        for r in rows
    ]


@cargo_router.get("/customers")
def list_company_customers(
    db: Session = Depends(get_db),
    ctx: WorkspaceContext = Depends(require_automation_permission("parcel.view")),
):
    company = db.query(CargoCompany).filter(CargoCompany.id == ctx.company_id).one()
    rows = (
        db.query(CargoCustomer)
        .filter(
            CargoCustomer.cargo_admin_id == company.created_by_user_id,
            CargoCustomer.status == "active",
        )
        .order_by(CargoCustomer.name)
        .limit(1000)
        .all()
    )
    return {
        "customers": [
            {
                "id": str(r.id),
                "name": r.name,
                "customer_reference": r.customer_reference,
                "phone": r.phone,
            }
            for r in rows
        ]
    }


@cargo_router.post("/parcels")
def receive_parcel(
    body: ParcelInput,
    db: Session = Depends(get_db),
    ctx: WorkspaceContext = Depends(require_automation_permission("parcel.receive")),
):
    branch = _branch(db, ctx)
    _consume_automation(db, ctx, "warehouse_device_parcel_received")
    customer = _customer(db, ctx, body.customer_id)
    company = db.query(CargoCompany).filter(CargoCompany.id == ctx.company_id).one()
    event = None
    metadata = {}
    if body.scan_event_id:
        event = (
            db.query(ParcelScanEvent)
            .filter(
                ParcelScanEvent.id == body.scan_event_id,
                ParcelScanEvent.company_id == ctx.company_id,
                ParcelScanEvent.branch_id == branch.id,
            )
            .with_for_update()
            .first()
        )
        if not event:
            raise HTTPException(404, "Scan event was not found.")
        if event.parcel_id:
            raise HTTPException(409, "This scan has already been registered.")
        metadata = event.metadata_json or {}

    sea_booking = None
    air_booking = None
    if metadata.get("sea_booking_id"):
        sea_booking = (
            db.query(SeaBooking)
            .join(Container)
            .filter(
                SeaBooking.id == metadata["sea_booking_id"],
                Container.admin_id == company.created_by_user_id,
            )
            .first()
        )
    if metadata.get("air_booking_id"):
        air_booking = (
            db.query(ExpressAirCargoBooking)
            .filter(
                ExpressAirCargoBooking.id == metadata["air_booking_id"],
                ExpressAirCargoBooking.cargo_admin_id == company.created_by_user_id,
            )
            .first()
        )
    if sea_booking and sea_booking.user_id != customer.linked_user_id:
        raise HTTPException(409, "The selected customer does not own this sea booking.")
    if air_booking and air_booking.customer_id != customer.linked_user_id:
        raise HTTPException(409, "The selected customer does not own this air booking.")

    tracking_number = (
        body.tracking_number or metadata.get("tracking_number") or ""
    ).strip().upper() or None
    shipping_mark = (
        body.shipping_mark or metadata.get("shipping_mark") or ""
    ).strip().upper() or None
    code = (
        tracking_number or shipping_mark or f"SHP-{datetime.utcnow():%y%m%d%H%M%S%f}"
    ).upper()
    cbm = (
        body.length_cm
        * body.width_cm
        * body.height_cm
        * body.carton_count
        / Decimal("1000000")
    )
    duplicate_intake = None
    if tracking_number:
        duplicate_intake = (
            db.query(ManualCargoIntake)
            .filter(
                ManualCargoIntake.cargo_admin_id == company.created_by_user_id,
                ManualCargoIntake.external_tracking_number == tracking_number,
            )
            .first()
        )
    if not duplicate_intake and sea_booking:
        duplicate_intake = (
            db.query(ManualCargoIntake)
            .filter_by(
                cargo_admin_id=company.created_by_user_id,
                sea_booking_id=sea_booking.id,
            )
            .first()
        )
    if not duplicate_intake and air_booking:
        duplicate_intake = (
            db.query(ManualCargoIntake)
            .filter_by(
                cargo_admin_id=company.created_by_user_id,
                air_booking_id=air_booking.id,
            )
            .first()
        )
    if duplicate_intake:
        raise HTTPException(409, "This parcel is already registered.")

    cargo_type = "air" if air_booking else "sea"
    intake = ManualCargoIntake(
        cargo_admin_id=company.created_by_user_id,
        intake_number=f"WRA-{datetime.utcnow().year}-{secrets.token_hex(6).upper()}",
        external_tracking_number=tracking_number,
        customer_id=customer.id,
        warehouse_id=branch.warehouse_id,
        cargo_type=cargo_type,
        charge_basis="kg" if cargo_type == "air" else "cbm",
        rate_currency="USD",
        status="received",
        intake_method="scan" if event else "assisted_scan",
        carrier=(body.carrier or "").strip() or None,
        shipping_mark=shipping_mark,
        payment_status="unpaid",
        collection_status="not_ready",
        received_at=datetime.utcnow(),
        received_by=ctx.user.id,
        intake_confirmed_by=ctx.user.id,
        sea_booking_id=sea_booking.id if sea_booking else None,
        air_booking_id=air_booking.id if air_booking else None,
        extraction_metadata={
            "scan_event_id": str(event.id) if event else None,
            "condition": body.condition,
            "dimensions_cm": {
                "length": float(body.length_cm),
                "width": float(body.width_cm),
                "height": float(body.height_cm),
            },
            "photo_urls": body.photo_urls,
        },
        notes=body.notes,
        total_cartons=body.carton_count,
        total_gross_weight_kg=body.weight_kg,
        total_cbm=cbm,
    )
    ensure_manual_intake_tracking_number(db, intake)
    intake_item = ManualCargoIntakeItem(
        intake=intake,
        sort_order=0,
        item_name="Warehouse parcel",
        item_description=body.notes or "Parcel received and verified at the warehouse",
        item_photo_url=body.photo_urls[0] if body.photo_urls else None,
        carton_count=body.carton_count,
        length_cm=body.length_cm,
        width_cm=body.width_cm,
        height_cm=body.height_cm,
        cbm_per_carton=cbm / body.carton_count if body.carton_count else 0,
        total_cbm=cbm,
        gross_weight_per_carton_kg=(
            body.weight_kg / body.carton_count if body.carton_count else 0
        ),
        total_gross_weight_kg=body.weight_kg,
        charge_basis=intake.charge_basis,
        rate_currency="USD",
    )
    db.add_all([intake, intake_item])
    db.flush()

    row = WarehouseParcel(
        company_id=ctx.company_id,
        branch_id=branch.id,
        warehouse_id=branch.warehouse_id,
        customer_id=body.customer_id,
        intake_id=intake.id,
        parcel_code=code,
        tracking_number=tracking_number,
        shipping_mark=shipping_mark,
        carrier=body.carrier,
        condition=body.condition,
        carton_count=body.carton_count,
        weight_kg=body.weight_kg,
        length_cm=body.length_cm,
        width_cm=body.width_cm,
        height_cm=body.height_cm,
        cbm=cbm,
        photo_urls=body.photo_urls,
        notes=body.notes,
        received_by_id=ctx.user.id,
    )
    db.add(row)
    try:
        db.flush()
        if event:
            event.parcel_id = row.id
            event.result = "matched"
            event.confidence = 100
        create_manual_intake_tracking_event(
            db,
            intake,
            event_type="manual_cargo_received",
            description=f"Cargo received at {row.warehouse.name}",
            triggered_by=ctx.user.id,
            condition=body.condition,
            warehouse_parcel_id=str(row.id),
        )
        if sea_booking or air_booking:
            record_booking_warehouse_event(
                db,
                sea_booking=sea_booking,
                air_booking=air_booking,
                event_type="warehouse_cargo_received",
                description=f"Cargo received at {row.warehouse.name}",
                logistics_stage="cargo_received",
                actor_id=ctx.user.id,
                location=row.warehouse.name or row.warehouse.location,
                status="received_at_warehouse",
                extra_data={
                    "manual_intake_id": str(intake.id),
                    "warehouse_parcel_id": str(row.id),
                    "tracking_number": intake.tracking_number,
                },
            )
        log_action(
            db,
            "warehouse_parcel_received",
            ctx.user.id,
            "warehouse_parcel",
            row.id,
            {"company_id": str(ctx.company_id), "branch_id": str(branch.id)},
        )
        if customer.linked_user_id:
            create_notification(
                db,
                customer.linked_user_id,
                "warehouse_parcel_received",
                f"Parcel {intake.tracking_number} was received at {row.warehouse.name}.",
                target_type="manual_cargo_intake",
                target_id=intake.id,
            )
        db.commit()
        db.refresh(row)
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            409, "This parcel code is already registered in the company."
        ) from exc
    return _payload(row)


@cargo_router.get("/parcels")
def list_parcels(
    status: str | None = None,
    customer_id: UUID | None = None,
    db: Session = Depends(get_db),
    ctx: WorkspaceContext = Depends(require_automation_permission("parcel.view")),
):
    branch = _branch(db, ctx)
    query = db.query(WarehouseParcel).filter(
        WarehouseParcel.company_id == ctx.company_id,
        WarehouseParcel.branch_id == branch.id,
    )
    if status:
        query = query.filter(WarehouseParcel.status == status)
    if customer_id:
        query = query.filter(WarehouseParcel.customer_id == customer_id)
    return {
        "parcels": [
            _payload(r)
            for r in query.order_by(WarehouseParcel.received_at.desc()).limit(500).all()
        ]
    }


@cargo_router.patch("/parcels/{parcel_id}")
def update_parcel(
    parcel_id: UUID,
    body: ParcelPatch,
    db: Session = Depends(get_db),
    ctx: WorkspaceContext = Depends(require_automation_permission("parcel.edit")),
):
    _consume_automation(db, ctx, "warehouse_device_parcel_updated")
    row = _parcel(db, ctx, parcel_id, True)
    for key, value in body.model_dump(exclude_unset=True).items():
        setattr(row, key, value)
    if any(v is not None for v in (body.length_cm, body.width_cm, body.height_cm)):
        row.cbm = (
            Decimal(row.length_cm or 0)
            * Decimal(row.width_cm or 0)
            * Decimal(row.height_cm or 0)
            * row.carton_count
            / Decimal("1000000")
        )
    log_action(
        db,
        "warehouse_parcel_updated",
        ctx.user.id,
        "warehouse_parcel",
        row.id,
        {"fields": list(body.model_dump(exclude_unset=True))},
    )
    db.commit()
    db.refresh(row)
    return _payload(row)


@cargo_router.post("/booking-selection")
def link_booking(
    body: BookingSelection,
    db: Session = Depends(get_db),
    ctx: WorkspaceContext = Depends(require_automation_permission("booking.manage")),
):
    _consume_automation(db, ctx, "warehouse_device_booking_linked")
    rows = [_parcel(db, ctx, parcel_id, True) for parcel_id in body.parcel_ids]
    for row in rows:
        exists = (
            db.query(ParcelBookingLink)
            .filter_by(
                parcel_id=row.id,
                booking_type=body.booking_type,
                booking_id=body.booking_id,
            )
            .first()
        )
        if not exists:
            db.add(
                ParcelBookingLink(
                    company_id=ctx.company_id,
                    parcel_id=row.id,
                    booking_type=body.booking_type,
                    booking_id=body.booking_id,
                    linked_by_id=ctx.user.id,
                )
            )
        row.status = "booked"
    log_action(
        db,
        "warehouse_parcels_linked_to_booking",
        ctx.user.id,
        "cargo_booking",
        body.booking_id,
        {"parcel_ids": [str(x.id) for x in rows], "booking_type": body.booking_type},
    )
    db.commit()
    return {"linked_count": len(rows)}


@cargo_router.post("/loading-sessions")
def start_loading(
    body: LoadingStart,
    db: Session = Depends(get_db),
    ctx: WorkspaceContext = Depends(require_automation_permission("shipment.update")),
):
    branch = _branch(db, ctx)
    _consume_automation(db, ctx, "warehouse_device_loading_started")
    row = LoadingSession(
        company_id=ctx.company_id,
        branch_id=branch.id,
        booking_type=body.booking_type,
        booking_id=body.booking_id,
        reference=body.reference,
        started_by_id=ctx.user.id,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return {"id": str(row.id), "status": row.status, "reference": row.reference}


@cargo_router.post("/loading-sessions/{session_id}/scan")
def scan_loading(
    session_id: UUID,
    body: LoadingCode,
    db: Session = Depends(get_db),
    ctx: WorkspaceContext = Depends(require_automation_permission("shipment.update")),
):
    _consume_automation(db, ctx, "warehouse_device_loading_scanned")
    session = (
        db.query(LoadingSession)
        .filter(
            LoadingSession.id == session_id, LoadingSession.company_id == ctx.company_id
        )
        .with_for_update()
        .first()
    )
    if not session or session.status != "open":
        raise HTTPException(409, "Loading session is not open.")
    code = body.code.strip().upper()
    label_reference = platform_label_reference(body.code)
    parcel_query = db.query(WarehouseParcel).filter(
        WarehouseParcel.company_id == ctx.company_id
    )
    if label_reference:
        booking_type, booking_id = label_reference
        parcel_query = parcel_query.join(
            ManualCargoIntake, ManualCargoIntake.id == WarehouseParcel.intake_id
        ).filter(
            ManualCargoIntake.sea_booking_id == booking_id
            if booking_type == "sea"
            else ManualCargoIntake.air_booking_id == booking_id
        )
    else:
        parcel_query = parcel_query.filter(
            or_(
                WarehouseParcel.parcel_code == code,
                WarehouseParcel.tracking_number == code,
                WarehouseParcel.shipping_mark == code,
            )
        )
    parcel = parcel_query.first()
    if not parcel:
        result, message = "red", "Parcel not found in this cargo company."
    elif parcel.branch_id != session.branch_id:
        result, message = "red", "Parcel belongs to another branch."
    elif (
        db.query(LoadingScan)
        .filter(
            LoadingScan.session_id == session.id,
            LoadingScan.parcel_id == parcel.id,
            LoadingScan.result == "green",
        )
        .first()
    ):
        result, message = "duplicate", "Parcel was already loaded in this session."
    elif (
        not db.query(ParcelBookingLink)
        .filter_by(
            parcel_id=parcel.id,
            booking_type=session.booking_type,
            booking_id=session.booking_id,
        )
        .first()
    ):
        result, message = "amber", "Parcel exists but is not assigned to this booking."
    else:
        result, message = "green", "Parcel loaded successfully."
        parcel.status = "loaded"
        intake = (
            db.get(ManualCargoIntake, parcel.intake_id) if parcel.intake_id else None
        )
        if intake:
            create_manual_intake_tracking_event(
                db,
                intake,
                event_type="warehouse_parcel_loaded",
                description=f"Cargo loaded for {session.reference}",
                triggered_by=ctx.user.id,
                status="loaded",
                logistics_stage="loaded_container",
                location=intake.warehouse.name if intake.warehouse else None,
                loading_reference=session.reference,
            )
        sea_booking = (
            db.get(SeaBooking, session.booking_id)
            if session.booking_type == "sea"
            else None
        )
        air_booking = (
            db.get(ExpressAirCargoBooking, session.booking_id)
            if session.booking_type == "air"
            else None
        )
        if sea_booking or air_booking:
            record_booking_warehouse_event(
                db,
                sea_booking=sea_booking,
                air_booking=air_booking,
                event_type="warehouse_parcel_loaded",
                description=f"Cargo loaded for {session.reference}",
                logistics_stage="loaded_container",
                actor_id=ctx.user.id,
                location=parcel.warehouse.name if parcel.warehouse else None,
                status="loaded",
                extra_data={"loading_reference": session.reference},
            )
    db.add(
        LoadingScan(
            session_id=session.id,
            parcel_id=parcel.id if parcel else None,
            scanned_code=code,
            result=result,
            message=message,
            scanned_by_id=ctx.user.id,
        )
    )
    db.commit()
    return {
        "result": result,
        "message": message,
        "parcel": _payload(parcel) if parcel else None,
    }


@cargo_router.post("/loading-sessions/{session_id}/complete")
def complete_loading(
    session_id: UUID,
    db: Session = Depends(get_db),
    ctx: WorkspaceContext = Depends(require_automation_permission("shipment.update")),
):
    _consume_automation(db, ctx, "warehouse_device_loading_completed")
    row = (
        db.query(LoadingSession)
        .filter(
            LoadingSession.id == session_id, LoadingSession.company_id == ctx.company_id
        )
        .with_for_update()
        .first()
    )
    if not row or row.status != "open":
        raise HTTPException(409, "Loading session is not open.")
    row.status = "completed"
    row.completed_at = datetime.utcnow()
    db.commit()
    return {"id": str(row.id), "status": row.status}


@cargo_router.post("/milestones")
def add_milestone(
    body: MilestoneInput,
    db: Session = Depends(get_db),
    ctx: WorkspaceContext = Depends(require_automation_permission("shipment.update")),
):
    branch = _branch(db, ctx)
    _consume_automation(db, ctx, "warehouse_device_milestone_recorded")
    row = ShipmentMilestone(
        company_id=ctx.company_id,
        branch_id=branch.id,
        booking_type=body.booking_type,
        booking_id=body.booking_id,
        milestone=body.milestone,
        location=body.location,
        note=body.note,
        occurred_at=body.occurred_at or datetime.utcnow(),
        created_by_id=ctx.user.id,
    )
    db.add(row)
    log_action(
        db,
        "shipment_milestone_recorded",
        ctx.user.id,
        "cargo_booking",
        body.booking_id,
        {"milestone": body.milestone, "branch_id": str(branch.id)},
    )
    stage_map = {
        "loaded": "loaded_container",
        "departed": "departed_china",
        "in_transit": "in_transit",
        "arrived": "destination_arrival",
        "customs": "customs_clearance",
        "ready_for_collection": "ready_for_pickup",
    }
    sea_booking = (
        db.get(SeaBooking, body.booking_id) if body.booking_type == "sea" else None
    )
    air_booking = (
        db.get(ExpressAirCargoBooking, body.booking_id)
        if body.booking_type == "air"
        else None
    )
    if sea_booking or air_booking:
        record_booking_warehouse_event(
            db,
            sea_booking=sea_booking,
            air_booking=air_booking,
            event_type="warehouse_shipment_milestone",
            description=f"Shipment update: {body.milestone.replace('_', ' ')}",
            logistics_stage=stage_map[body.milestone],
            actor_id=ctx.user.id,
            location=body.location,
            status=body.milestone,
            extra_data={"note": body.note, "occurred_at": row.occurred_at.isoformat()},
        )
    recipients = (
        db.query(CargoCustomer.linked_user_id)
        .join(WarehouseParcel, WarehouseParcel.customer_id == CargoCustomer.id)
        .join(ParcelBookingLink, ParcelBookingLink.parcel_id == WarehouseParcel.id)
        .filter(
            ParcelBookingLink.company_id == ctx.company_id,
            ParcelBookingLink.booking_type == body.booking_type,
            ParcelBookingLink.booking_id == body.booking_id,
            CargoCustomer.linked_user_id.isnot(None),
        )
        .distinct()
        .all()
    )
    for (user_id,) in recipients:
        create_notification(
            db,
            user_id,
            "shipment_milestone",
            f"Shipment update: {body.milestone.replace('_', ' ')}.",
            target_type="cargo_booking",
            target_id=body.booking_id,
        )
    db.commit()
    return {
        "id": str(row.id),
        "milestone": row.milestone,
        "occurred_at": row.occurred_at.isoformat(),
    }


@customer_router.get("")
def my_smart_parcels(
    db: Session = Depends(get_db), customer: User = Depends(get_customer)
):
    rows = (
        db.query(WarehouseParcel)
        .join(CargoCustomer, CargoCustomer.id == WarehouseParcel.customer_id)
        .filter(CargoCustomer.linked_user_id == customer.id)
        .order_by(WarehouseParcel.received_at.desc())
        .all()
    )
    totals = {
        "parcel_count": len(rows),
        "cartons": sum(r.carton_count for r in rows),
        "weight_kg": sum(float(r.weight_kg or 0) for r in rows),
        "cbm": sum(float(r.cbm or 0) for r in rows),
    }
    return {"parcels": [_payload(r) for r in rows], "totals": totals}
