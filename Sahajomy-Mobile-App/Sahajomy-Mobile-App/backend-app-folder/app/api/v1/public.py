import calendar
from datetime import datetime, timedelta
from decimal import ROUND_HALF_UP, Decimal

from app.core.audit import log_action
from app.core.config import settings
from app.core.public_input import normalize_public_name, normalize_public_whatsapp
from app.database import get_db
from app.models.air_cargo import AirDepartureSchedule
from app.models.container import (  # For new endpoints
    Container,
    SeaBooking,
)
from app.models.finance import (  # FIXED: finance.py, not financial
    CommissionSettings,
    Receipt,
    ReceiptScan,
)
from app.models.sourcing import (
    BatchShareToken,
    SourcingBatch,
    SourcingOrder,
    SourcingOrderItem,
    SourcingProduct,
)
from app.models.user import Guest  # FIXED: Guest is in user.py
from app.models.user import User  # For operator stats
from app.services.booking_notifications import send_guest_batch_order_email
from app.services.document_branding import sourcing_agent_document_branding
from app.services.goods_catalog import serialize_goods_catalog
from app.services.company_service_governance import company_service_is_bookable
from app.services.tracking import TrackingService
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel, Field, field_validator
from sqlalchemy import func
from sqlalchemy.orm import Session, joinedload

router = APIRouter(prefix="/public", tags=["Public"])


# Health check endpoint
@router.get("/health")
def health_check():
    """Health check endpoint for monitoring and load balancers"""
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "service": "sahajomy-api",
    }


class PublicOrderItemRequest(BaseModel):
    product_id: str
    quantity: int = Field(..., gt=0)


class GuestInfoRequest(BaseModel):
    name: str = Field(..., min_length=2, max_length=150)
    phone_number: str = Field(..., min_length=7, max_length=30)

    @field_validator("name")
    @classmethod
    def normalize_name(cls, value: str) -> str:
        return normalize_public_name(value)

    @field_validator("phone_number")
    @classmethod
    def normalize_phone(cls, value: str) -> str:
        return normalize_public_whatsapp(value)


class PublicBatchOrderRequest(BaseModel):
    guest_info: GuestInfoRequest
    items: list[PublicOrderItemRequest] = Field(..., min_length=1)


class PublicShippingEstimateRequest(BaseModel):
    """The current product selection on a public batch link.

    The estimate is deliberately token-scoped: callers provide product IDs and
    quantities, while the server reads prices, CBM, and shipping configuration
    from the batch. This keeps customer totals authoritative without exposing
    product-level cargo data in the shared-batch payload.
    """

    items: list[PublicOrderItemRequest] = Field(default_factory=list)


class PublicSharedOrderResponse(BaseModel):
    id: str
    submitted_by: str
    items_count: int
    currency: str
    total_product_amount: float
    delivery_status: str
    message: str


MONEY_QUANTUM = Decimal("0.01")
CBM_QUANTUM = Decimal("0.0001")


def _as_decimal(value) -> Decimal:
    """Convert persisted numeric values without using binary floating point."""
    return Decimal(str(value if value is not None else 0))


def _round_money(value: Decimal) -> Decimal:
    return value.quantize(MONEY_QUANTUM, rounding=ROUND_HALF_UP)


def _round_cbm(value: Decimal) -> Decimal:
    return value.quantize(CBM_QUANTUM, rounding=ROUND_HALF_UP)


def _get_active_shared_batch(token: str, db: Session) -> SourcingBatch:
    """Resolve a valid share token to its open batch without counting a view."""
    share_token = (
        db.query(BatchShareToken).filter(BatchShareToken.token == token).first()
    )
    if not share_token:
        raise HTTPException(status_code=404, detail="Batch not found or link invalid")
    if share_token.expires_at and share_token.expires_at < datetime.utcnow():
        raise HTTPException(status_code=410, detail="Share link expired")
    if share_token.max_views and share_token.current_views >= share_token.max_views:
        raise HTTPException(status_code=410, detail="Share link view limit reached")

    batch = (
        db.query(SourcingBatch)
        .filter(
            SourcingBatch.id == share_token.batch_id, SourcingBatch.status == "open"
        )
        .first()
    )
    if not batch:
        raise HTTPException(status_code=404, detail="Batch not available")
    return batch


def _shared_batch_shipping_estimate(
    batch: SourcingBatch, items: list[PublicOrderItemRequest], db: Session
) -> dict:
    """Calculate customer-safe selected-product and shipping estimates."""
    product_ids = [item.product_id for item in items]
    unique_product_ids = set(product_ids)
    if len(unique_product_ids) != len(product_ids):
        raise HTTPException(
            status_code=400, detail="Duplicate products are not allowed"
        )

    products = []
    if unique_product_ids:
        products = (
            db.query(SourcingProduct)
            .filter(
                SourcingProduct.batch_id == batch.id,
                SourcingProduct.id.in_(unique_product_ids),
            )
            .all()
        )
    products_by_id = {str(product.id): product for product in products}
    missing_products = [pid for pid in product_ids if pid not in products_by_id]
    if missing_products:
        raise HTTPException(status_code=400, detail="One or more products are invalid")

    subtotal = Decimal("0")
    total_cbm = Decimal("0")
    missing_cbm = False
    for item in items:
        product = products_by_id[item.product_id]
        quantity = Decimal(item.quantity)
        subtotal += _as_decimal(product.price_per_unit) * quantity

        cbm_per_unit = _as_decimal(product.cbm_per_unit)
        if batch.shipping_method == "PER_CBM" and cbm_per_unit <= 0:
            missing_cbm = True
        total_cbm += cbm_per_unit * quantity

    subtotal = _round_money(subtotal)
    total_cbm = _round_cbm(total_cbm)
    shipping_method = batch.shipping_method or "PER_CBM"
    shipping_rate = _round_money(_as_decimal(batch.shipping_fee_per_cbm))

    if shipping_method == "FREE_SHIPPING":
        estimate_status = "free_shipping"
        shipping_fee = Decimal("0")
        estimated_total = subtotal
    elif missing_cbm or shipping_rate <= 0:
        # Legacy data can predate the CBM/rate validation now enforced when
        # a batch product is created. Never replace unknown shipping with zero.
        estimate_status = "pending"
        shipping_fee = None
        estimated_total = None
    else:
        estimate_status = "estimated"
        shipping_fee = _round_money(total_cbm * shipping_rate)
        estimated_total = _round_money(subtotal + shipping_fee)

    return {
        "currency": batch.currency or "TZS",
        "selected_products_total": float(subtotal),
        "total_selected_cbm": float(total_cbm),
        "shipping_method": shipping_method,
        "shipping_fee_per_cbm": float(shipping_rate),
        "estimate_status": estimate_status,
        "estimated_shipping_fee": (
            float(shipping_fee) if shipping_fee is not None else None
        ),
        "estimated_total": (
            float(estimated_total) if estimated_total is not None else None
        ),
    }


# ====== YOUR EXISTING ENDPOINTS (WITH FIXED IMPORTS) ======


@router.get("/batch/{token}")
def view_shared_batch(token: str, db: Session = Depends(get_db)):
    share_token = (
        db.query(BatchShareToken).filter(BatchShareToken.token == token).first()
    )
    if not share_token:
        raise HTTPException(status_code=404, detail="Batch not found or link invalid")
    if share_token.expires_at and share_token.expires_at < datetime.utcnow():
        raise HTTPException(status_code=410, detail="Share link expired")
    if share_token.max_views and share_token.current_views >= share_token.max_views:
        raise HTTPException(status_code=410, detail="Share link view limit reached")

    share_token.current_views += 1
    db.commit()

    batch = (
        db.query(SourcingBatch)
        .options(joinedload(SourcingBatch.agent))
        .filter(
            SourcingBatch.id == share_token.batch_id, SourcingBatch.status == "open"
        )
        .first()
    )
    if not batch:
        raise HTTPException(status_code=404, detail="Batch not available")

    products = (
        db.query(SourcingProduct).filter(SourcingProduct.batch_id == batch.id).all()
    )
    seller = sourcing_agent_document_branding(db, batch.agent)
    return {
        "title": batch.title,
        "description": batch.description,
        "seller": {
            "name": seller.get("name"),
            "phone": seller.get("phone"),
            "address": seller.get("address"),
            "profile_image_url": seller.get("profile_image_url"),
        },
        "currency": batch.currency or "TZS",
        "products": [
            {
                "id": str(p.id),
                "name": p.name,
                "description": p.description,
                # ``price_per_unit`` is the customer-facing price configured
                # for the batch. Never return CBM or batch-cost fields here.
                "customer_price": float(p.price_per_unit),
                "currency": batch.currency or "TZS",
                "minimum_order_quantity": p.minimum_order_quantity,
                "image_url": p.image_url,
            }
            for p in products
        ],
    }


@router.post("/batch/{token}/estimate")
def estimate_shared_batch_shipping(
    token: str,
    body: PublicShippingEstimateRequest,
    db: Session = Depends(get_db),
):
    """Return the server-calculated customer estimate for a shared batch."""
    batch = _get_active_shared_batch(token, db)
    return _shared_batch_shipping_estimate(batch, body.items, db)


@router.post("/batch/{token}/order", response_model=PublicSharedOrderResponse)
@router.post("/shared-batch/{token}/order", response_model=PublicSharedOrderResponse)
def place_guest_batch_order(
    token: str,
    body: PublicBatchOrderRequest,
    db: Session = Depends(get_db),
):
    share_token = (
        db.query(BatchShareToken).filter(BatchShareToken.token == token).first()
    )
    if not share_token:
        raise HTTPException(status_code=404, detail="Batch not found or link invalid")
    if share_token.expires_at and share_token.expires_at < datetime.utcnow():
        raise HTTPException(status_code=410, detail="Share link expired")
    if share_token.max_views and share_token.current_views >= share_token.max_views:
        raise HTTPException(status_code=410, detail="Share link view limit reached")

    batch = (
        db.query(SourcingBatch)
        .filter(
            SourcingBatch.id == share_token.batch_id, SourcingBatch.status == "open"
        )
        .first()
    )
    if not batch:
        raise HTTPException(status_code=404, detail="Batch not available")

    product_ids = [item.product_id for item in body.items]
    unique_product_ids = set(product_ids)
    if len(unique_product_ids) != len(product_ids):
        raise HTTPException(
            status_code=400, detail="Duplicate products are not allowed"
        )

    products = (
        db.query(SourcingProduct)
        .filter(
            SourcingProduct.batch_id == batch.id,
            SourcingProduct.id.in_(unique_product_ids),
        )
        .all()
    )
    products_by_id = {str(product.id): product for product in products}
    missing_products = [pid for pid in product_ids if pid not in products_by_id]
    if missing_products:
        raise HTTPException(status_code=400, detail="One or more products are invalid")

    below_minimum = [
        (products_by_id[item.product_id], item.quantity)
        for item in body.items
        if item.quantity < (products_by_id[item.product_id].minimum_order_quantity or 1)
    ]
    if below_minimum:
        product, quantity = below_minimum[0]
        raise HTTPException(
            status_code=400,
            detail=(
                f"{product.name} has a minimum order quantity of "
                f"{product.minimum_order_quantity}; you entered {quantity}."
            ),
        )

    guest_name = body.guest_info.name
    guest_phone = body.guest_info.phone_number

    guest = db.query(Guest).filter(Guest.phone_number == guest_phone).first()
    if not guest:
        guest = Guest(name=guest_name, phone_number=guest_phone)
        db.add(guest)
        db.flush()
    elif guest.name != guest_name:
        guest.name = guest_name

    total_product_amount = 0.0
    order_lines = []
    for item in body.items:
        product = products_by_id[item.product_id]
        line_total = float(product.price_per_unit) * item.quantity
        line_cbm = float(product.cbm_per_unit) * item.quantity
        total_product_amount += line_total
        order_lines.append(
            {
                "product": product,
                "quantity": item.quantity,
                "line_total": line_total,
                "line_cbm": line_cbm,
            }
        )

    commission_setting = (
        db.query(CommissionSettings)
        .order_by(CommissionSettings.effective_from.desc())
        .first()
    )
    commission_rate = (
        float(commission_setting.commission_percentage)
        if commission_setting
        else settings.DEFAULT_COMMISSION_PERCENTAGE
    )
    commission_amount = round(total_product_amount * (commission_rate / 100), 2)

    order = SourcingOrder(
        batch_id=batch.id,
        guest_id=guest.id,
        submitted_by="guest",
        total_product_amount=round(total_product_amount, 2),
        commission_amount=commission_amount,
        currency=batch.currency or "TZS",
        commission_status="pending",
        delivery_status="not_arrived",
    )
    db.add(order)
    db.flush()

    for line in order_lines:
        db.add(
            SourcingOrderItem(
                order_id=order.id,
                product_id=line["product"].id,
                quantity=line["quantity"],
                unit_price=round(float(line["product"].price_per_unit), 2),
                total_price=round(line["line_total"], 2),
                currency=batch.currency or "TZS",
                total_cbm=round(line["line_cbm"], 4),
            )
        )

    TrackingService.create_tracking_event(
        db=db,
        entity_type="batch",
        entity_id=str(batch.id),
        event_type="guest_order_created",
        description=f"Guest order placed for batch {batch.id}",
        triggered_by=None,
        extra_data={
            "guest_name": guest.name,
            "order_id": str(order.id),
            "items_count": len(order_lines),
            "total_product_amount": round(total_product_amount, 2),
        },
    )

    log_action(
        db=db,
        action="guest_batch_order_created",
        user_id=None,
        entity_type="sourcing_order",
        entity_id=order.id,
        metadata={
            "batch_id": str(batch.id),
            "guest_id": str(guest.id),
            "items_count": len(order_lines),
            "total_product_amount": round(total_product_amount, 2),
        },
    )

    db.commit()
    db.refresh(order)
    send_guest_batch_order_email(
        batch.agent,
        batch,
        order,
        guest,
        len(order_lines),
    )

    return {
        "id": str(order.id),
        "submitted_by": "guest",
        "items_count": len(order_lines),
        "currency": batch.currency or "TZS",
        "total_product_amount": round(total_product_amount, 2),
        "delivery_status": "not_arrived",
        "message": "Order placed successfully",
    }


@router.get("/receipt/verify/{token}")
def verify_receipt(token: str, request: Request, db: Session = Depends(get_db)):
    receipt = db.query(Receipt).filter(Receipt.receipt_token == token).first()
    if not receipt:
        raise HTTPException(status_code=404, detail="Receipt not found")

    scan = ReceiptScan(
        receipt_id=receipt.id,
        ip_address=request.client.host if request.client else None,
    )
    db.add(scan)
    db.commit()

    order = receipt.order
    return {
        "valid": True,
        "receipt_number": receipt.receipt_number,
        "generated_at": receipt.generated_at.isoformat(),
        "order_id": str(order.id) if order else None,
        "total_amount": float(order.total_product_amount or 0) if order else None,
    }


@router.get("/goods/categories")
def list_goods_categories(db: Session = Depends(get_db)):
    return serialize_goods_catalog(db)


@router.get("/products/{product_id}")
def get_public_product_detail(product_id: str, db: Session = Depends(get_db)):
    product = (
        db.query(SourcingProduct)
        .options(joinedload(SourcingProduct.batch))
        .join(SourcingBatch, SourcingProduct.batch_id == SourcingBatch.id)
        .filter(SourcingProduct.id == product_id, SourcingBatch.status == "open")
        .first()
    )
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    # This endpoint is used by an authenticated page today, but is public by
    # URL. Keep its response safe for an unauthenticated caller as well.
    return {
        "id": str(product.id),
        "name": product.name,
        "description": product.description,
        "customer_price": float(product.price_per_unit),
        "image_url": product.image_url,
        "minimum_order_quantity": product.minimum_order_quantity or 1,
    }


# ====== NEW ENDPOINTS FOR LANDING PAGE ======


@router.get("/platform-stats")
def get_platform_stats(db: Session = Depends(get_db)):
    """Get live platform statistics for landing page"""

    sea_booking_totals = (
        db.query(
            SeaBooking.container_id.label("container_id"),
            func.coalesce(func.sum(SeaBooking.cbm_booked), 0).label(
                "booked_cbm"
            ),
        )
        .group_by(SeaBooking.container_id)
        .subquery()
    )

    # Count live containers (open or nearly_full)
    live_containers = (
        db.query(Container)
        .filter(Container.status.in_(["open", "nearly_full"]))
        .count()
    )

    # Count active operators (cargo admins with containers)
    active_operators = (
        db.query(User)
        .filter(
            User.role == "cargo_admin",
            User.containers.any(Container.status.in_(["open", "nearly_full"])),
        )
        .count()
    )

    # Calculate total available CBM
    available_cbm = (
        db.query(
            func.coalesce(
                func.sum(
                    Container.max_cbm
                    - func.coalesce(sea_booking_totals.c.booked_cbm, 0)
                ),
                0,
            )
        )
        .outerjoin(
            sea_booking_totals, sea_booking_totals.c.container_id == Container.id
        )
        .filter(Container.status.in_(["open", "nearly_full"]))
        .scalar()
    )

    return {
        "containers": live_containers,
        "operators": active_operators,
        "cbm": float(available_cbm or 0),
    }


def _get_booked_cbm_map(db: Session, container_ids: list[str]) -> dict[str, float]:
    if not container_ids:
        return {}

    rows = (
        db.query(
            SeaBooking.container_id,
            func.coalesce(func.sum(SeaBooking.cbm_booked), 0).label(
                "booked_cbm"
            ),
        )
        .filter(SeaBooking.container_id.in_(container_ids))
        .group_by(SeaBooking.container_id)
        .all()
    )

    return {
        str(container_id): float(booked_cbm or 0)
        for container_id, booked_cbm in rows
    }


@router.get("/featured-containers")
def get_featured_containers(db: Session = Depends(get_db)):
    """Get 3 featured containers for landing page preview"""

    containers = (
        db.query(Container)
        .filter(Container.status.in_(["open", "nearly_full"]))
        .order_by(Container.created_at.desc())
        .limit(3)
        .all()
    )

    booked_cbm_map = _get_booked_cbm_map(
        db, [str(container.id) for container in containers]
    )

    return [
        {
            "id": str(c.id),
            "operator": c.admin.name if c.admin else "Cargo Company",
            "route": f"{c.origin_warehouse.city if c.origin_warehouse else 'China'} → {c.destination_warehouse.city if c.destination_warehouse else 'Africa'}",
            "available_cbm": max(
                float(c.max_cbm or 0)
                - booked_cbm_map.get(str(c.id), float(c.booked_cbm or 0)),
                0,
            ),
            "fill_percentage": round(
                (
                    (
                        (
                            booked_cbm_map.get(str(c.id), float(c.booked_cbm or 0))
                            / float(c.max_cbm)
                        )
                        * 100
                    )
                    if c.max_cbm and float(c.max_cbm) > 0
                    else 0
                ),
                0,
            ),
            "price_per_cbm": float(c.price_per_cbm),
            "container_size": c.container_size,
            "status": c.status,
            "origin_warehouse": (
                {
                    "name": c.origin_warehouse.name if c.origin_warehouse else None,
                    "address": (
                        c.origin_warehouse.address if c.origin_warehouse else None
                    ),
                    "city": c.origin_warehouse.city if c.origin_warehouse else None,
                    "country": (
                        c.origin_warehouse.country if c.origin_warehouse else None
                    ),
                    "latitude": (
                        float(c.origin_warehouse.latitude)
                        if c.origin_warehouse and c.origin_warehouse.latitude
                        else None
                    ),
                    "longitude": (
                        float(c.origin_warehouse.longitude)
                        if c.origin_warehouse and c.origin_warehouse.longitude
                        else None
                    ),
                }
                if c.origin_warehouse
                else None
            ),
            "destination_warehouse": (
                {
                    "name": (
                        c.destination_warehouse.name
                        if c.destination_warehouse
                        else None
                    ),
                    "address": (
                        c.destination_warehouse.address
                        if c.destination_warehouse
                        else None
                    ),
                    "city": (
                        c.destination_warehouse.city
                        if c.destination_warehouse
                        else None
                    ),
                    "country": (
                        c.destination_warehouse.country
                        if c.destination_warehouse
                        else None
                    ),
                    "latitude": (
                        float(c.destination_warehouse.latitude)
                        if c.destination_warehouse and c.destination_warehouse.latitude
                        else None
                    ),
                    "longitude": (
                        float(c.destination_warehouse.longitude)
                        if c.destination_warehouse and c.destination_warehouse.longitude
                        else None
                    ),
                }
                if c.destination_warehouse
                else None
            ),
        }
        for c in containers
    ]


@router.get("/air-departure-schedules")
def get_public_air_departure_schedules(
    limit: int = Query(5, ge=1, le=7),
    db: Session = Depends(get_db),
):
    """Return only upcoming, bookable departures safe to show on the public site."""
    schedules = (
        db.query(AirDepartureSchedule)
        .filter(
            AirDepartureSchedule.status.in_(["open", "filling_fast"]),
        )
        .order_by(AirDepartureSchedule.departure_at.asc())
        .all()
    )
    now = datetime.utcnow()
    departures = []
    for schedule in schedules:
        for departure_at in _upcoming_departures(schedule, now, limit):
            cutoff_at = None
            if schedule.booking_cutoff_at:
                cutoff_at = schedule.booking_cutoff_at + (
                    departure_at - schedule.departure_at
                )
            departures.append(
                {
                    # The occurrence key is deliberately not a booking ID: bookings
                    # remain requested separately and cannot be enumerated publicly.
                    "id": f"{schedule.id}:{departure_at.isoformat()}",
                    "route_label": schedule.route_label,
                    "service_label": schedule.service_label,
                    "departure_at": departure_at.isoformat(),
                    "booking_cutoff_at": cutoff_at.isoformat() if cutoff_at else None,
                    "capacity_kg": (
                        float(schedule.capacity_kg)
                        if schedule.capacity_kg is not None
                        else None
                    ),
                    "available_capacity_kg": (
                        float(schedule.available_capacity_kg)
                        if schedule.available_capacity_kg is not None
                        else None
                    ),
                    "status": schedule.status,
                    "recurrence_frequency": schedule.recurrence_frequency,
                }
            )

    return sorted(departures, key=lambda departure: departure["departure_at"])[:limit]


def _recurrence_weekdays(raw_weekdays: str | None) -> set[int]:
    try:
        return {int(day) for day in (raw_weekdays or "").split(",") if day.strip()}
    except ValueError:
        return set()


def _next_month(value: datetime) -> datetime:
    month_index = value.month
    year = value.year + month_index // 12
    month = month_index % 12 + 1
    day = min(value.day, calendar.monthrange(year, month)[1])
    return value.replace(year=year, month=month, day=day)


def _next_year(value: datetime) -> datetime:
    year = value.year + 1
    day = min(value.day, calendar.monthrange(year, value.month)[1])
    return value.replace(year=year, day=day)


def _upcoming_departures(
    schedule: AirDepartureSchedule, now: datetime, limit: int
) -> list[datetime]:
    """Expand one operator-owned rule without exposing any private schedule data."""
    end_at = schedule.recurrence_until
    frequency = schedule.recurrence_frequency
    if not frequency:
        return [schedule.departure_at] if schedule.departure_at >= now else []

    departures: list[datetime] = []
    if frequency == "weekly":
        weekdays = _recurrence_weekdays(schedule.recurrence_weekdays)
        if not weekdays:
            return []
        candidate_day = max(schedule.departure_at.date(), now.date())
        # A limit of seven occurrences keeps this bounded even for a long-lived rule.
        for offset in range(0, 366):
            candidate_date = candidate_day + timedelta(days=offset)
            candidate = schedule.departure_at.replace(
                year=candidate_date.year,
                month=candidate_date.month,
                day=candidate_date.day,
            )
            if candidate < schedule.departure_at or candidate < now:
                continue
            if end_at and candidate > end_at:
                break
            if candidate.weekday() in weekdays:
                departures.append(candidate)
                if len(departures) >= limit:
                    break
        return departures

    candidate = schedule.departure_at
    advance = _next_month if frequency == "monthly" else _next_year
    # Bring old recurrence templates forward. The cap guards corrupt historic data.
    for _ in range(5000):
        if candidate >= now:
            break
        candidate = advance(candidate)
    for _ in range(limit):
        if end_at and candidate > end_at:
            break
        departures.append(candidate)
        candidate = advance(candidate)
    return departures


@router.get("/containers")
def list_public_containers(db: Session = Depends(get_db)):
    """List publicly viewable open containers for unauthenticated users."""
    containers = (
        db.query(Container)
        .options(
            joinedload(Container.admin),
            joinedload(Container.route),
            joinedload(Container.origin_warehouse),
            joinedload(Container.destination_warehouse),
        )
        .filter(Container.status.in_(["open", "nearly_full"]))
        .order_by(Container.created_at.desc())
        .all()
    )

    booked_cbm_map = _get_booked_cbm_map(
        db, [str(container.id) for container in containers]
    )

    results = []
    for c in containers:
        if not company_service_is_bookable(
            db, operator_id=c.admin_id, service_type="shared_container"
        ):
            continue
        booked_cbm = booked_cbm_map.get(str(c.id), float(c.booked_cbm or 0))
        max_cbm = float(c.max_cbm or 0)
        available_cbm = max(max_cbm - booked_cbm, 0)
        fill_percentage = (
            round((booked_cbm / max_cbm * 100), 2) if max_cbm > 0 else 0.0
        )

        origin = (
            (c.route.origin if c.route else None)
            or (c.origin_warehouse.city if c.origin_warehouse else None)
            or (c.origin_warehouse.location if c.origin_warehouse else None)
            or "Origin TBD"
        )
        destination = (
            (c.route.destination if c.route else None)
            or (c.destination_warehouse.city if c.destination_warehouse else None)
            or (c.destination_warehouse.location if c.destination_warehouse else None)
            or "Destination TBD"
        )

        results.append(
            {
                "id": str(c.id),
                "operator_name": c.admin.name if c.admin else "Cargo Company",
                "origin": origin,
                "destination": destination,
                "available_cbm": available_cbm,
                "fill_percentage": fill_percentage,
                "price_per_cbm": float(c.price_per_cbm),
                "container_size": c.container_size,
                "status": c.status,
            }
        )

    return results
