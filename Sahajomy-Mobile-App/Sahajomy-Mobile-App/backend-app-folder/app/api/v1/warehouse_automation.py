"""Secure, optional automation APIs layered on existing manual cargo intakes."""

from __future__ import annotations

import hashlib
import hmac
import re
import secrets
from datetime import datetime, timedelta
from typing import Literal
from uuid import UUID

from app.core.audit import log_action
from app.core.config import settings
from app.core.dependencies import get_cargo_admin, get_customer, get_super_admin
from app.database import get_db
from app.models.air_cargo import ExpressAirCargoBooking
from app.models.cargo_customs import (
    CargoCustomer,
    ManualCargoIntake,
    ManualCargoIntakeItem,
)
from app.models.container import Container, SeaBooking, Warehouse
from app.models.shipping_mark import ShippingMark
from app.models.user import User
from app.models.warehouse_automation import (
    CargoAdminFeatureEntitlement,
    WarehouseCollectionRequest,
    WarehouseCollectionRequestItem,
)
from app.services.manual_cargo_tracking import create_manual_intake_tracking_event
from app.services.realtime_notifications import create_notification
from app.services.subscriptions import (
    company_for_operator,
    consume_usage,
    entitlement_map,
    get_current_subscription,
    require_feature,
    subscription_is_usable,
    usage_payload,
)
from app.services.tracking_number import ensure_manual_intake_tracking_number
from app.services.warehouse_tracking import (
    platform_label_reference,
    record_booking_warehouse_event,
)
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import or_
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, joinedload

cargo_router = APIRouter(
    prefix="/cargo_admin/warehouse-automation", tags=["Warehouse Automation"]
)
customer_router = APIRouter(
    prefix="/customer/warehouse-access", tags=["Customer Warehouse Access"]
)
super_admin_router = APIRouter(
    prefix="/super_admin/warehouse-automation",
    tags=["Super Admin Warehouse Automation"],
)

COLLECTION_REQUEST_TTL_MINUTES = 15
TRACKING_PATTERN = re.compile(r"\b[A-Z0-9][A-Z0-9-]{5,99}\b", re.IGNORECASE)
LABEL_PATTERNS = {
    "tracking_number": re.compile(
        r"(?:TRACKING(?:\s*(?:NUMBER|NO))?|AWB|WAYBILL)\s*[:#-]?\s*([A-Z0-9-]{6,100})",
        re.IGNORECASE,
    ),
    "shipping_mark": re.compile(
        r"(?:SHIPPING\s*MARK|MARK)\s*[:#-]?\s*([A-Z0-9-]{3,100})", re.IGNORECASE
    ),
    "customer_code": re.compile(
        r"(?:CUSTOMER\s*(?:CODE|ID)|CLIENT\s*(?:CODE|ID))\s*[:#-]?\s*([A-Z0-9-]{2,100})",
        re.IGNORECASE,
    ),
    "booking_reference": re.compile(
        r"(?:BOOKING|ORDER|REFERENCE|REF)\s*(?:NUMBER|NO)?\s*[:#-]?\s*([A-Z0-9-]{3,100})",
        re.IGNORECASE,
    ),
    "carrier": re.compile(
        r"(?:CARRIER|COURIER)\s*[:#-]?\s*([^\n\r]{2,120})", re.IGNORECASE
    ),
    "recipient_name": re.compile(
        r"(?:RECIPIENT|CONSIGNEE)\s*[:#-]?\s*([^\n\r]{2,150})", re.IGNORECASE
    ),
    "phone_number": re.compile(
        r"(?:PHONE|MOBILE|TEL)\s*[:#-]?\s*([+0-9][0-9 ()-]{5,30})", re.IGNORECASE
    ),
    "parcel_count": re.compile(
        r"(?:PARCELS?|CARTONS?|PACKAGES?|PCS)\s*[:#-]?\s*(\d{1,6})", re.IGNORECASE
    ),
    "weight_kg": re.compile(
        r"(?:WEIGHT|GROSS\s*WEIGHT)\s*[:#-]?\s*(\d+(?:\.\d+)?)\s*KG", re.IGNORECASE
    ),
}


def _digest(value: str) -> str:
    return hmac.new(
        settings.SECRET_KEY.encode(), value.encode(), hashlib.sha256
    ).hexdigest()


def _utc_iso(value: datetime | None) -> str | None:
    """Make the UTC semantics of the project's naive UTC datetimes explicit to browsers."""
    return f"{value.isoformat()}Z" if value else None


def _extract_label_fields(raw: str) -> tuple[dict, list[str]]:
    extracted: dict = {}
    for field, pattern in LABEL_PATTERNS.items():
        match = pattern.search(raw)
        if match:
            value = match.group(1).strip()
            extracted[field] = (
                int(value)
                if field == "parcel_count"
                else float(value) if field == "weight_kg" else value
            )
    candidates = TRACKING_PATTERN.findall(raw.upper())
    ignored = {
        "TRACKING",
        "NUMBER",
        "SHIPPING",
        "CUSTOMER",
        "BOOKING",
        "REFERENCE",
        "RECIPIENT",
        "CONSIGNEE",
        "CARRIER",
        "COURIER",
        "WEIGHT",
        "CARTONS",
        "PACKAGES",
    }
    machine_tokens = [
        token
        for token in candidates
        if token not in ignored and any(character.isdigit() for character in token)
    ]
    keys = [
        extracted.get("tracking_number"),
        extracted.get("shipping_mark"),
        extracted.get("booking_reference"),
        *machine_tokens,
    ]
    keys = list(
        dict.fromkeys(
            value.upper() for value in keys if isinstance(value, str) and value
        )
    )[:20]
    if not extracted.get("tracking_number") and keys:
        extracted["tracking_number"] = keys[0]
    return extracted, keys


def _safe_extraction_metadata(values: dict) -> dict:
    allowed = set(LABEL_PATTERNS)
    cleaned: dict = {}
    for key, value in values.items():
        if key not in allowed or not isinstance(value, (str, int, float)):
            continue
        cleaned[key] = value.strip()[:500] if isinstance(value, str) else value
    return cleaned


def _require_enabled(
    db: Session,
    admin_id,
    *,
    action: str | None = None,
    created_by_id=None,
):
    company = company_for_operator(db, admin_id)
    subscription = get_current_subscription(db, company.id) if company else None
    if company and subscription:
        require_feature(db, company.id, "warehouse_automation")
        if action:
            consume_usage(
                db,
                company.id,
                "automation_events",
                action=action,
                created_by_id=created_by_id,
            )
        return subscription
    entitlement = (
        db.query(CargoAdminFeatureEntitlement)
        .filter(CargoAdminFeatureEntitlement.cargo_admin_id == admin_id)
        .first()
    )
    if not entitlement or not entitlement.warehouse_automation_enabled:
        raise HTTPException(
            status_code=403,
            detail="Warehouse automation is not enabled for this Cargo Admin",
        )
    return entitlement


def _warehouse_for_admin(db: Session, admin_id, warehouse_id: UUID) -> Warehouse:
    warehouse = (
        db.query(Warehouse)
        .filter(Warehouse.id == warehouse_id, Warehouse.admin_id == admin_id)
        .first()
    )
    if not warehouse:
        raise HTTPException(status_code=404, detail="Warehouse not found")
    return warehouse


def _warehouse_from_token(db: Session, token: str) -> Warehouse:
    if not token or len(token) > 256:
        raise HTTPException(status_code=404, detail="Warehouse access link is invalid")
    warehouse = (
        db.query(Warehouse)
        .filter(
            Warehouse.automation_access_token_hash == _digest(token),
            Warehouse.automation_token_revoked_at.is_(None),
        )
        .first()
    )
    if not warehouse:
        raise HTTPException(
            status_code=404,
            detail="Warehouse access link is invalid or has been revoked",
        )
    _require_enabled(db, warehouse.admin_id)
    return warehouse


def _intake_payload(row: ManualCargoIntake) -> dict:
    return {
        "id": str(row.id),
        "intake_number": row.intake_number,
        "tracking_number": row.tracking_number,
        "external_tracking_number": row.external_tracking_number,
        "shipping_mark": row.shipping_mark,
        "carrier": row.carrier,
        "received_at": _utc_iso(row.received_at),
        "cargo_type": row.cargo_type,
        "total_cartons": row.total_cartons,
        "total_weight_kg": float(row.total_gross_weight_kg or 0),
        "payment_status": row.payment_status,
        "collection_status": row.collection_status,
        "eligible_for_collection": row.payment_status == "paid"
        and row.collection_status == "ready",
        "intake_method": row.intake_method,
        "customer_name": row.customer.name if row.customer else None,
        "warehouse_name": row.warehouse.name if row.warehouse else None,
    }


def _customer_intakes(db: Session, customer_id, warehouse: Warehouse):
    return (
        db.query(ManualCargoIntake)
        .join(CargoCustomer)
        .filter(
            CargoCustomer.linked_user_id == customer_id,
            ManualCargoIntake.warehouse_id == warehouse.id,
            ManualCargoIntake.cargo_admin_id == warehouse.admin_id,
            ManualCargoIntake.status.in_(
                ["received", "ready_for_packing_list", "finalized"]
            ),
            ManualCargoIntake.collection_status != "collected",
        )
    )


class EntitlementInput(BaseModel):
    enabled: bool


class ScanMatchInput(BaseModel):
    warehouse_id: UUID
    scan_text: str = Field(min_length=2, max_length=4000)


class ConfirmIntakeInput(BaseModel):
    warehouse_id: UUID
    customer_id: UUID
    cargo_type: Literal["sea", "air"] = "sea"
    tracking_number: str | None = Field(default=None, max_length=100)
    external_tracking_number: str | None = Field(default=None, max_length=100)
    shipping_mark: str | None = Field(default=None, max_length=100)
    carrier: str | None = Field(default=None, max_length=120)
    item_name: str = Field(min_length=1, max_length=200)
    item_description: str = Field(min_length=1, max_length=500)
    carton_count: int = Field(default=1, ge=1)
    total_weight_kg: float = Field(default=0, ge=0)
    intake_method: Literal["scan", "barcode", "assisted_scan"] = "assisted_scan"
    extracted_fields: dict = Field(default_factory=dict)
    sea_booking_id: UUID | None = None
    air_booking_id: UUID | None = None


class CollectionSelectionInput(BaseModel):
    intake_ids: list[UUID] = Field(min_length=1, max_length=50)


class CollectionCodeInput(BaseModel):
    code: str | None = Field(default=None, min_length=6, max_length=512)
    pin: str | None = Field(default=None, min_length=6, max_length=12)


class CollectionReadinessInput(BaseModel):
    """Separate financial approval from physical handover confirmation."""

    payment_status: Literal["unpaid", "paid"]
    collection_status: Literal["not_ready", "ready"]


@super_admin_router.get("/cargo-admins")
def list_cargo_admin_entitlements(
    db: Session = Depends(get_db), _: User = Depends(get_super_admin)
):
    admins = db.query(User).filter(User.role == "cargo_admin").order_by(User.name).all()
    flags = {
        row.cargo_admin_id: row for row in db.query(CargoAdminFeatureEntitlement).all()
    }
    return {
        "cargo_admins": [
            {
                "id": str(admin.id),
                "name": admin.name,
                "email": admin.email,
                "warehouse_automation_enabled": bool(
                    flags.get(admin.id) and flags[admin.id].warehouse_automation_enabled
                ),
            }
            for admin in admins
        ]
    }


@super_admin_router.put("/cargo-admins/{cargo_admin_id}")
def set_cargo_admin_entitlement(
    cargo_admin_id: UUID,
    body: EntitlementInput,
    db: Session = Depends(get_db),
    super_admin: User = Depends(get_super_admin),
):
    admin = (
        db.query(User)
        .filter(User.id == cargo_admin_id, User.role == "cargo_admin")
        .first()
    )
    if not admin:
        raise HTTPException(status_code=404, detail="Cargo Admin not found")
    company = company_for_operator(db, admin.id)
    if company and get_current_subscription(db, company.id):
        raise HTTPException(
            status_code=409,
            detail="Warehouse automation is controlled by the company subscription. Use Super Admin Subscriptions to change the plan.",
        )
    entitlement = (
        db.query(CargoAdminFeatureEntitlement)
        .filter(CargoAdminFeatureEntitlement.cargo_admin_id == admin.id)
        .first()
    )
    if not entitlement:
        entitlement = CargoAdminFeatureEntitlement(cargo_admin_id=admin.id)
        db.add(entitlement)
    entitlement.warehouse_automation_enabled = body.enabled
    entitlement.updated_by_id = super_admin.id
    log_action(
        db,
        "warehouse_automation_entitlement_changed",
        super_admin.id,
        "cargo_admin",
        admin.id,
        {"enabled": body.enabled},
    )
    db.commit()
    return {
        "cargo_admin_id": str(admin.id),
        "warehouse_automation_enabled": body.enabled,
    }


@cargo_router.get("/status")
def automation_status(
    db: Session = Depends(get_db), admin: User = Depends(get_cargo_admin)
):
    company = company_for_operator(db, admin.id)
    subscription = get_current_subscription(db, company.id) if company else None
    if subscription:
        feature = entitlement_map(subscription).get("warehouse_automation")
        enabled = bool(
            feature and feature.enabled and subscription_is_usable(subscription)
        )
        billing = usage_payload(db, company.id)
    else:
        enabled = bool(
            db.query(CargoAdminFeatureEntitlement.warehouse_automation_enabled)
            .filter(CargoAdminFeatureEntitlement.cargo_admin_id == admin.id)
            .scalar()
        )
        billing = None
    warehouses = db.query(Warehouse).filter(Warehouse.admin_id == admin.id).all()
    return {
        "enabled": enabled,
        "billing": billing,
        "warehouses": [
            {
                "id": str(w.id),
                "name": w.name,
                "has_access_qr": bool(w.automation_access_token_hash),
            }
            for w in warehouses
        ],
    }


@cargo_router.get("/operations")
def warehouse_operations(
    db: Session = Depends(get_db), admin: User = Depends(get_cargo_admin)
):
    """Mobile operations feed; manual receipts and scanned receipts share this list."""
    _require_enabled(db, admin.id)
    rows = (
        db.query(ManualCargoIntake)
        .options(
            joinedload(ManualCargoIntake.customer),
            joinedload(ManualCargoIntake.warehouse),
        )
        .filter(ManualCargoIntake.cargo_admin_id == admin.id)
        .order_by(ManualCargoIntake.received_at.desc())
        .limit(250)
        .all()
    )
    today = datetime.utcnow().date()
    return {
        "summary": {
            "arrivals_today": sum(
                1 for row in rows if row.received_at and row.received_at.date() == today
            ),
            "ready_for_collection": sum(
                1
                for row in rows
                if row.payment_status == "paid" and row.collection_status == "ready"
            ),
            "collected_today": sum(
                1
                for row in rows
                if row.collected_at and row.collected_at.date() == today
            ),
            "unmatched_scans": sum(
                1
                for row in rows
                if row.intake_method != "manual"
                and not row.external_tracking_number
                and not row.shipping_mark
            ),
        },
        "intakes": [_intake_payload(row) for row in rows],
    }


@cargo_router.post("/warehouses/{warehouse_id}/access-token")
def rotate_warehouse_access_token(
    warehouse_id: UUID,
    db: Session = Depends(get_db),
    admin: User = Depends(get_cargo_admin),
):
    _require_enabled(
        db,
        admin.id,
        action="warehouse_access_token_rotated",
        created_by_id=admin.id,
    )
    warehouse = _warehouse_for_admin(db, admin.id, warehouse_id)
    token = secrets.token_urlsafe(32)
    warehouse.automation_access_token_hash = _digest(token)
    warehouse.automation_token_created_at = datetime.utcnow()
    warehouse.automation_token_revoked_at = None
    log_action(
        db, "warehouse_access_token_rotated", admin.id, "warehouse", warehouse.id
    )
    db.commit()
    return {
        "warehouse_id": str(warehouse.id),
        "access_token": token,
        "access_url": f"{settings.public_app_url}/customer/warehouse-access/{token}",
    }


@cargo_router.delete("/warehouses/{warehouse_id}/access-token", status_code=204)
def revoke_warehouse_access_token(
    warehouse_id: UUID,
    db: Session = Depends(get_db),
    admin: User = Depends(get_cargo_admin),
):
    _require_enabled(db, admin.id)
    warehouse = _warehouse_for_admin(db, admin.id, warehouse_id)
    warehouse.automation_access_token_hash = None
    warehouse.automation_token_revoked_at = datetime.utcnow()
    log_action(
        db, "warehouse_access_token_revoked", admin.id, "warehouse", warehouse.id
    )
    db.commit()


@cargo_router.post("/intake/match")
def match_scanned_intake(
    body: ScanMatchInput,
    db: Session = Depends(get_db),
    admin: User = Depends(get_cargo_admin),
):
    _require_enabled(
        db, admin.id, action="warehouse_label_matched", created_by_id=admin.id
    )
    _warehouse_for_admin(db, admin.id, body.warehouse_id)
    scan = body.scan_text.strip()
    extracted, keys = _extract_label_fields(scan)
    label_reference = platform_label_reference(scan)
    token = keys[0] if keys else scan[:100].upper()
    duplicate_filters = [
        ManualCargoIntake.tracking_number.in_(keys or [token]),
        ManualCargoIntake.external_tracking_number.in_(keys or [token]),
    ]
    if label_reference:
        booking_type, booking_id = label_reference
        duplicate_filters.append(
            ManualCargoIntake.sea_booking_id == booking_id
            if booking_type == "sea"
            else ManualCargoIntake.air_booking_id == booking_id
        )
    duplicate = (
        db.query(ManualCargoIntake)
        .filter(
            ManualCargoIntake.cargo_admin_id == admin.id,
            or_(*duplicate_filters),
        )
        .first()
    )
    if duplicate:
        extracted["tracking_number"] = (
            duplicate.external_tracking_number or duplicate.tracking_number
        )
        return {
            "confidence": "high",
            "duplicate": True,
            "intake": _intake_payload(duplicate),
            "extracted": extracted,
        }
    mark = (
        db.query(ShippingMark)
        .options(
            joinedload(ShippingMark.air_booking),
            joinedload(ShippingMark.sea_booking).joinedload(SeaBooking.container),
        )
        .filter(ShippingMark.shipping_mark_code.in_(keys or [token]))
        .first()
    )
    if mark and not (
        (mark.air_booking and mark.air_booking.cargo_admin_id == admin.id)
        or (
            mark.sea_booking
            and mark.sea_booking.container
            and mark.sea_booking.container.admin_id == admin.id
        )
    ):
        mark = None
    air_booking = (
        db.query(ExpressAirCargoBooking)
        .filter(
            ExpressAirCargoBooking.cargo_admin_id == admin.id,
            (
                ExpressAirCargoBooking.id == label_reference[1]
                if label_reference and label_reference[0] == "air"
                else or_(
                    ExpressAirCargoBooking.tracking_number.in_(keys or [token]),
                    ExpressAirCargoBooking.airway_bill_number.in_(keys or [token]),
                )
            ),
        )
        .first()
    )
    sea_query = db.query(SeaBooking).join(Container)
    if label_reference and label_reference[0] == "sea":
        sea_booking = sea_query.filter(
            Container.admin_id == admin.id,
            SeaBooking.id == label_reference[1],
        ).first()
    else:
        sea_booking = (
            sea_query.join(SeaBooking.shipping_mark)
            .filter(
                Container.admin_id == admin.id,
                ShippingMark.shipping_mark_code.in_(keys or [token]),
            )
            .first()
        )
    if not mark and sea_booking and sea_booking.shipping_mark:
        mark = sea_booking.shipping_mark
    if not mark and air_booking and air_booking.shipping_mark:
        mark = air_booking.shipping_mark
    if label_reference:
        scanned_booking_id = label_reference[1].upper()
        if str(extracted.get("tracking_number") or "").upper() == scanned_booking_id:
            extracted.pop("tracking_number", None)
        if air_booking and air_booking.tracking_number:
            extracted["tracking_number"] = air_booking.tracking_number
    customer_search = str(
        extracted.get("customer_code") or extracted.get("recipient_name") or token
    ).strip()
    customer_matches = (
        db.query(CargoCustomer)
        .filter(
            CargoCustomer.cargo_admin_id == admin.id,
            or_(
                CargoCustomer.customer_reference.ilike(f"%{customer_search}%"),
                CargoCustomer.name.ilike(f"%{customer_search}%"),
            ),
        )
        .limit(5)
        .all()
    )
    if mark:
        extracted["shipping_mark"] = mark.shipping_mark_code
    if mark:
        owner_user_id = (
            mark.air_booking.customer_id
            if mark.air_booking
            else mark.sea_booking.user_id
        )
        cargo_customer = (
            db.query(CargoCustomer)
            .filter(
                CargoCustomer.cargo_admin_id == admin.id,
                CargoCustomer.linked_user_id == owner_user_id,
            )
            .first()
            if owner_user_id
            else None
        )
        return {
            "confidence": "high",
            "duplicate": False,
            "extracted": extracted,
            "suggested_customer_id": str(cargo_customer.id) if cargo_customer else None,
            "sea_booking_id": (
                str(mark.sea_booking_id) if mark.sea_booking_id else None
            ),
            "air_booking_id": str(mark.air_booking_id) if mark.air_booking_id else None,
            "booking_reference": str(mark.booking_id),
            "reason": "Exact shipping mark match",
        }
    if air_booking:
        cargo_customer = (
            db.query(CargoCustomer)
            .filter(
                CargoCustomer.cargo_admin_id == admin.id,
                CargoCustomer.linked_user_id == air_booking.customer_id,
            )
            .first()
            if air_booking.customer_id
            else None
        )
        return {
            "confidence": "high",
            "duplicate": False,
            "extracted": extracted,
            "booking_reference": str(air_booking.id),
            "air_booking_id": str(air_booking.id),
            "suggested_customer_id": str(cargo_customer.id) if cargo_customer else None,
            "reason": "Exact Express Air Cargo booking match; staff must confirm the customer",
        }
    if sea_booking:
        cargo_customer = (
            db.query(CargoCustomer)
            .filter(
                CargoCustomer.cargo_admin_id == admin.id,
                CargoCustomer.linked_user_id == sea_booking.user_id,
            )
            .first()
            if sea_booking.user_id
            else None
        )
        return {
            "confidence": "high",
            "duplicate": False,
            "extracted": extracted,
            "booking_reference": str(sea_booking.id),
            "sea_booking_id": str(sea_booking.id),
            "suggested_customer_id": str(cargo_customer.id) if cargo_customer else None,
            "reason": "Exact sea booking shipping mark; staff must confirm the customer",
        }
    return {
        "confidence": "medium" if customer_matches else "low",
        "duplicate": False,
        "extracted": extracted,
        "customers": [
            {"id": str(c.id), "name": c.name, "reference": c.customer_reference}
            for c in customer_matches
        ],
        "reason": (
            "Customer suggestion requires staff confirmation"
            if customer_matches
            else "No reliable match; enter the receipt manually"
        ),
    }


@cargo_router.post("/intake/confirm")
def confirm_automated_intake(
    body: ConfirmIntakeInput,
    db: Session = Depends(get_db),
    admin: User = Depends(get_cargo_admin),
):
    _require_enabled(
        db, admin.id, action="warehouse_intake_confirmed", created_by_id=admin.id
    )
    warehouse = _warehouse_for_admin(db, admin.id, body.warehouse_id)
    customer = (
        db.query(CargoCustomer)
        .filter(
            CargoCustomer.id == body.customer_id,
            CargoCustomer.cargo_admin_id == admin.id,
        )
        .first()
    )
    if not customer:
        raise HTTPException(status_code=404, detail="Cargo customer not found")
    item_name = body.item_name.strip()
    item_description = body.item_description.strip()
    if not item_name or not item_description:
        raise HTTPException(
            status_code=422, detail="Item name and description cannot be blank"
        )
    if body.sea_booking_id and body.air_booking_id:
        raise HTTPException(
            status_code=422,
            detail="Select either a sea booking or an air booking, not both",
        )
    sea_booking = None
    air_booking = None
    if body.sea_booking_id:
        sea_booking = (
            db.query(SeaBooking)
            .join(Container)
            .filter(
                SeaBooking.id == body.sea_booking_id,
                Container.admin_id == admin.id,
            )
            .first()
        )
        if not sea_booking:
            raise HTTPException(
                status_code=404, detail="Container sea_booking not found"
            )
    if body.air_booking_id:
        air_booking = (
            db.query(ExpressAirCargoBooking)
            .filter(
                ExpressAirCargoBooking.id == body.air_booking_id,
                ExpressAirCargoBooking.cargo_admin_id == admin.id,
            )
            .first()
        )
        if not air_booking:
            raise HTTPException(
                status_code=404, detail="Express Air Cargo booking not found"
            )
    external_tracking = (
        body.external_tracking_number or body.tracking_number or ""
    ).strip().upper() or None
    if (
        external_tracking
        and db.query(ManualCargoIntake)
        .filter(
            ManualCargoIntake.cargo_admin_id == admin.id,
            ManualCargoIntake.external_tracking_number == external_tracking,
        )
        .first()
    ):
        raise HTTPException(status_code=409, detail="Parcel already registered")
    row = ManualCargoIntake(
        cargo_admin_id=admin.id,
        intake_number=f"WRA-{datetime.utcnow().year}-{secrets.token_hex(6).upper()}",
        external_tracking_number=external_tracking,
        customer_id=customer.id,
        warehouse_id=warehouse.id,
        cargo_type=body.cargo_type,
        charge_basis="kg" if body.cargo_type == "air" else "cbm",
        rate_currency="USD",
        status="received",
        intake_method=body.intake_method,
        shipping_mark=(body.shipping_mark or "").strip().upper() or None,
        carrier=(body.carrier or "").strip() or None,
        payment_status="unpaid",
        collection_status="not_ready",
        received_at=datetime.utcnow(),
        received_by=admin.id,
        intake_confirmed_by=admin.id,
        sea_booking_id=sea_booking.id if sea_booking else None,
        air_booking_id=air_booking.id if air_booking else None,
        extraction_metadata={
            "fields": _safe_extraction_metadata(body.extracted_fields),
            "confirmed_at": _utc_iso(datetime.utcnow()),
        },
    )
    item = ManualCargoIntakeItem(
        intake=row,
        sort_order=0,
        item_name=item_name,
        item_description=item_description,
        carton_count=body.carton_count,
        total_gross_weight_kg=body.total_weight_kg,
        gross_weight_per_carton_kg=(
            body.total_weight_kg / body.carton_count if body.carton_count else 0
        ),
        charge_basis=row.charge_basis,
        rate_currency="USD",
    )
    row.total_cartons = body.carton_count
    row.total_gross_weight_kg = body.total_weight_kg
    ensure_manual_intake_tracking_number(db, row)
    db.add_all([row, item])
    db.flush()
    create_manual_intake_tracking_event(
        db,
        row,
        event_type="manual_cargo_received",
        description="Cargo received through warehouse intake",
        triggered_by=admin.id,
    )
    if sea_booking or air_booking:
        record_booking_warehouse_event(
            db,
            sea_booking=sea_booking,
            air_booking=air_booking,
            event_type="warehouse_cargo_received",
            description=f"Cargo received at {warehouse.name}",
            logistics_stage="cargo_received",
            actor_id=admin.id,
            location=warehouse.name or warehouse.location,
            status="received_at_warehouse",
            extra_data={
                "manual_intake_id": str(row.id),
                "tracking_number": row.tracking_number,
                "external_tracking_number": row.external_tracking_number,
            },
        )
    log_action(
        db,
        "automated_warehouse_intake_confirmed",
        admin.id,
        "manual_cargo_intake",
        row.id,
        {"intake_method": body.intake_method},
    )
    if customer.linked_user_id:
        create_notification(
            db,
            customer.linked_user_id,
            "warehouse_parcel_received",
            f"Your parcel has arrived at {warehouse.name}.",
            target_type="manual_cargo_intake",
            target_id=row.id,
        )
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=409,
            detail="Parcel conflicts with an existing tracking or intake record",
        )
    return _intake_payload(row)


@cargo_router.patch("/intakes/{intake_id}/collection-readiness")
def set_collection_readiness(
    intake_id: UUID,
    body: CollectionReadinessInput,
    db: Session = Depends(get_db),
    admin: User = Depends(get_cargo_admin),
):
    """Record payment/physical readiness before a customer can obtain a collection code."""
    _require_enabled(db, admin.id)
    intake = (
        db.query(ManualCargoIntake)
        .filter(
            ManualCargoIntake.id == intake_id,
            ManualCargoIntake.cargo_admin_id == admin.id,
        )
        .with_for_update()
        .first()
    )
    if not intake:
        raise HTTPException(status_code=404, detail="Manual cargo intake not found")
    if intake.collection_status == "collected":
        raise HTTPException(
            status_code=409, detail="A collected parcel cannot be changed"
        )
    if body.collection_status == "ready" and body.payment_status != "paid":
        raise HTTPException(
            status_code=409,
            detail="Payment must be paid before a parcel can be ready for collection",
        )
    became_ready = (
        intake.collection_status != "ready" and body.collection_status == "ready"
    )
    intake.payment_status = body.payment_status
    intake.collection_status = body.collection_status
    if became_ready:
        create_manual_intake_tracking_event(
            db,
            intake,
            event_type="manual_cargo_ready_for_pickup",
            description="Cargo is ready for pickup",
            triggered_by=admin.id,
            status="ready_for_pickup",
            payment_status=body.payment_status,
            collection_status=body.collection_status,
        )
    log_action(
        db,
        "warehouse_collection_readiness_updated",
        admin.id,
        "manual_cargo_intake",
        intake.id,
        {
            "payment_status": body.payment_status,
            "collection_status": body.collection_status,
        },
    )
    db.commit()
    return _intake_payload(intake)


@customer_router.get("/{token}")
def customer_warehouse_parcels(
    token: str, db: Session = Depends(get_db), customer: User = Depends(get_customer)
):
    warehouse = _warehouse_from_token(db, token)
    return {
        "warehouse": {"id": str(warehouse.id), "name": warehouse.name},
        "parcels": [
            _intake_payload(row)
            for row in _customer_intakes(db, customer.id, warehouse)
            .order_by(ManualCargoIntake.received_at.desc())
            .all()
        ],
    }


@customer_router.post("/{token}/collection-requests")
def create_collection_request(
    token: str,
    body: CollectionSelectionInput,
    db: Session = Depends(get_db),
    customer: User = Depends(get_customer),
):
    warehouse = _warehouse_from_token(db, token)
    _require_enabled(
        db,
        warehouse.admin_id,
        action="warehouse_collection_requested",
        created_by_id=customer.id,
    )
    rows = (
        _customer_intakes(db, customer.id, warehouse)
        .filter(ManualCargoIntake.id.in_(body.intake_ids))
        .with_for_update()
        .all()
    )
    if len(rows) != len(set(body.intake_ids)):
        raise HTTPException(
            status_code=404, detail="One or more selected parcels were not found"
        )
    if any(
        row.payment_status != "paid" or row.collection_status != "ready" for row in rows
    ):
        raise HTTPException(
            status_code=409,
            detail="Every selected parcel must be paid and ready for collection",
        )
    active_item = (
        db.query(WarehouseCollectionRequestItem)
        .join(WarehouseCollectionRequest)
        .filter(
            WarehouseCollectionRequestItem.intake_id.in_(body.intake_ids),
            WarehouseCollectionRequest.status == "requested",
            WarehouseCollectionRequest.expires_at > datetime.utcnow(),
        )
        .first()
    )
    if active_item:
        raise HTTPException(
            status_code=409,
            detail="One or more parcels already have an active collection request",
        )
    token_value = secrets.token_urlsafe(28)
    for _ in range(10):
        pin = f"{secrets.randbelow(900000) + 100000}"
        collision = (
            db.query(WarehouseCollectionRequest.id)
            .filter(
                WarehouseCollectionRequest.cargo_admin_id == warehouse.admin_id,
                WarehouseCollectionRequest.pin_hash == _digest(pin),
                WarehouseCollectionRequest.status == "requested",
                WarehouseCollectionRequest.expires_at > datetime.utcnow(),
            )
            .first()
        )
        if not collision:
            break
    else:
        raise HTTPException(
            status_code=503, detail="Could not allocate a collection PIN; please retry"
        )
    request = WarehouseCollectionRequest(
        cargo_admin_id=warehouse.admin_id,
        customer_id=customer.id,
        warehouse_id=warehouse.id,
        token_hash=_digest(token_value),
        pin_hash=_digest(pin),
        expires_at=datetime.utcnow()
        + timedelta(minutes=COLLECTION_REQUEST_TTL_MINUTES),
    )
    db.add(request)
    db.flush()
    db.add_all(
        [
            WarehouseCollectionRequestItem(
                collection_request_id=request.id, intake_id=row.id
            )
            for row in rows
        ]
    )
    log_action(
        db,
        "warehouse_collection_requested",
        customer.id,
        "warehouse_collection_request",
        request.id,
        {"parcel_count": len(rows)},
    )
    db.commit()
    return {
        "collection_request_id": str(request.id),
        "collection_code": token_value,
        "pin": pin,
        "expires_at": _utc_iso(request.expires_at),
        "parcel_count": len(rows),
    }


def _collection_for_code(
    db: Session, admin: User, body: CollectionCodeInput, lock: bool = False
) -> WarehouseCollectionRequest:
    if not body.code and not body.pin:
        raise HTTPException(status_code=422, detail="Provide a collection code or PIN")
    query = db.query(WarehouseCollectionRequest)
    query = query.filter(WarehouseCollectionRequest.cargo_admin_id == admin.id)
    query = query.filter(
        WarehouseCollectionRequest.token_hash == _digest(body.code)
        if body.code
        else WarehouseCollectionRequest.pin_hash == _digest(body.pin)
    )
    if lock:
        query = query.with_for_update()
    request = query.first()
    if not request:
        raise HTTPException(status_code=404, detail="Collection code was not found")
    if request.status != "requested":
        raise HTTPException(
            status_code=409, detail="Collection code has already been used or cancelled"
        )
    if request.expires_at <= datetime.utcnow():
        request.status = "expired"
        log_action(
            db,
            "warehouse_collection_request_expired",
            admin.id,
            "warehouse_collection_request",
            request.id,
        )
        db.commit()
        raise HTTPException(status_code=410, detail="Collection code has expired")
    if not lock:
        request = (
            db.query(WarehouseCollectionRequest)
            .options(
                joinedload(WarehouseCollectionRequest.items).joinedload(
                    WarehouseCollectionRequestItem.intake
                )
            )
            .filter(WarehouseCollectionRequest.id == request.id)
            .one()
        )
    return request


@cargo_router.post("/collection/verify")
def verify_collection_code(
    body: CollectionCodeInput,
    db: Session = Depends(get_db),
    admin: User = Depends(get_cargo_admin),
):
    _require_enabled(
        db, admin.id, action="warehouse_collection_verified", created_by_id=admin.id
    )
    request = _collection_for_code(db, admin, body)
    return {
        "collection_request_id": str(request.id),
        "expires_at": _utc_iso(request.expires_at),
        "parcel_count": len(request.items),
        "parcels": [_intake_payload(item.intake) for item in request.items],
    }


@cargo_router.post("/collection/{request_id}/confirm")
def confirm_collection(
    request_id: UUID,
    body: CollectionCodeInput,
    db: Session = Depends(get_db),
    admin: User = Depends(get_cargo_admin),
):
    _require_enabled(
        db, admin.id, action="warehouse_collection_confirmed", created_by_id=admin.id
    )
    request = _collection_for_code(db, admin, body, lock=True)
    if request.id != request_id:
        raise HTTPException(
            status_code=403, detail="Collection code does not match this request"
        )
    item_ids = [
        row[0]
        for row in db.query(WarehouseCollectionRequestItem.intake_id)
        .filter(WarehouseCollectionRequestItem.collection_request_id == request.id)
        .all()
    ]
    rows = (
        db.query(ManualCargoIntake)
        .filter(
            ManualCargoIntake.id.in_(item_ids),
            ManualCargoIntake.cargo_admin_id == admin.id,
            ManualCargoIntake.warehouse_id == request.warehouse_id,
            ManualCargoIntake.customer_id.in_(
                db.query(CargoCustomer.id).filter(
                    CargoCustomer.linked_user_id == request.customer_id
                )
            ),
        )
        .with_for_update()
        .all()
    )
    if len(rows) != len(item_ids):
        raise HTTPException(
            status_code=409,
            detail="One or more parcels no longer belong to this collection request",
        )
    if any(
        row.collection_status != "ready" or row.payment_status != "paid" for row in rows
    ):
        raise HTTPException(
            status_code=409,
            detail="One or more parcels are no longer eligible for collection",
        )
    now = datetime.utcnow()
    for row in rows:
        row.collection_status = "collected"
        row.collected_at = now
        row.collected_by = admin.id
        create_manual_intake_tracking_event(
            db,
            row,
            event_type="manual_cargo_collected",
            description="Cargo collected",
            triggered_by=admin.id,
            status="completed",
            collection_status="collected",
        )
    request.status = "used"
    request.used_at = now
    request.used_by_id = admin.id
    log_action(
        db,
        "warehouse_collection_confirmed",
        admin.id,
        "warehouse_collection_request",
        request.id,
        {"parcel_ids": [str(row.id) for row in rows]},
    )
    db.commit()
    return {
        "collection_request_id": str(request.id),
        "status": "used",
        "collected_count": len(rows),
        "collected_at": _utc_iso(now),
    }
