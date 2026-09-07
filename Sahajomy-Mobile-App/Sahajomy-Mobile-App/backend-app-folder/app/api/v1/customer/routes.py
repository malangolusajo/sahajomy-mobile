"""Customer APIs for browsing and booking container space."""

import json
import os
import re
import tempfile
from datetime import datetime, timedelta, timezone
from typing import List, Optional
from urllib.parse import urlparse

import cloudinary.utils
import httpx
from app.api.v1.customer.analytics import router as analytics_router
from app.api.v1.customer.shipment_orders import router as shipment_orders_router
from app.core.audit import log_action
from app.core.cloudinary import (
    build_optimized_cloudinary_image_url,
    configure_cloudinary,
    upload_to_cloudinary,
)
from app.core.config import settings
from app.core.dependencies import get_customer
from app.core.upload_validation import validated_image_format
from app.database import get_db
from app.models.air_cargo import AirCargoRate, ExpressAirCargoBooking
from app.models.container import (
    Container,
    GoodsType,
    SeaBooking,
    SeaBookingGoods,
    Warehouse,
)
from app.models.customer_china_address import CustomerChinaAddress
from app.models.finance import (
    AuditLog,
    CommissionSettings,
    Receipt,
    SeaBookingInvoice,
    SeaBookingPackingList,
    SeaBookingPackingListItem,
)
from app.models.shipment_orders import ShipmentOrder
from app.models.sourcing import (
    SourcingBatch,
    SourcingOrder,
    SourcingOrderItem,
    SourcingProduct,
)
from app.models.tracking import TrackingEvent
from app.models.user import User
from app.services.air_cargo_pricing import (
    DEFAULT_AIR_CARGO_ROUTE,
    calculate_rate_total,
    get_air_cargo_goods_policy,
    get_matching_rate,
    serialize_rate,
)
from app.services.booking_notifications import (
    notify_air_cargo_booking_created,
    notify_container_booking_created,
    notify_urgent_sourcing_request,
)
from app.services.china_warehouse_address import is_china_warehouse
from app.services.company_service_governance import (
    company_service_is_bookable,
    require_company_service_bookable,
)
from app.services.customer_china_addresses import (
    copy_ready_address,
    ensure_customer_china_address,
    prepare_user_air_china_address,
)
from app.services.document_branding import operator_document_branding
from app.services.document_download import stream_safe_document
from app.services.shipment_orders_service import (
    ensure_shipment_order_for_air_booking,
    ensure_shipment_order_for_sea_booking,
)
from app.services.shipping_mark import build_printable_label, create_shipping_mark
from app.services.tracking import TrackingService
from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy import func
from sqlalchemy.orm import Session, joinedload

api_router = APIRouter()
customer_ops_router = APIRouter(prefix="/customer", tags=["customer-core"])

# Include all customer routers
# api_router.include_router(auth_router, prefix="/auth", tags=["customer-auth"])
# analytics_router already defines prefix="/customer/analytics"
api_router.include_router(analytics_router)
# Keep shipment orders under /customer/*
api_router.include_router(
    shipment_orders_router,
    prefix="/customer/shipment-orders",
    tags=["customer-shipment-orders"],
)


class EnsureChinaAddressRequest(BaseModel):
    cargo_mode: str
    destination_country: str = Field(..., min_length=2, max_length=100)
    destination_city: str = Field(..., min_length=2, max_length=120)
    # A warehouse id alone is intentionally not accepted: forwarding warehouse
    # access must be derived from the selected cargo service.
    container_id: Optional[str] = None
    air_booking_id: Optional[str] = None


class CustomerForwardingProfileRequest(BaseModel):
    full_name: Optional[str] = Field(None, min_length=2, max_length=150)
    phone: Optional[str] = Field(None, min_length=6, max_length=50)


@customer_ops_router.get("/china-addresses")
def list_my_china_addresses(
    db: Session = Depends(get_db), customer: User = Depends(get_customer)
):
    addresses = (
        db.query(CustomerChinaAddress)
        .options(
            joinedload(CustomerChinaAddress.warehouse),
            joinedload(CustomerChinaAddress.customer),
        )
        .filter(CustomerChinaAddress.customer_id == customer.id)
        .order_by(CustomerChinaAddress.created_at.desc())
        .all()
    )
    return [copy_ready_address(address) for address in addresses]


@customer_ops_router.get("/china-addresses/{address_id}")
def get_my_china_address(
    address_id: str,
    db: Session = Depends(get_db),
    customer: User = Depends(get_customer),
):
    address = (
        db.query(CustomerChinaAddress)
        .options(
            joinedload(CustomerChinaAddress.warehouse),
            joinedload(CustomerChinaAddress.customer),
        )
        .filter(
            CustomerChinaAddress.id == address_id,
            CustomerChinaAddress.customer_id == customer.id,
        )
        .first()
    )
    if not address:
        raise HTTPException(status_code=404, detail="China delivery address not found.")
    return copy_ready_address(address)


@customer_ops_router.patch("/china-addresses/forwarding-profile")
def update_forwarding_profile(
    body: CustomerForwardingProfileRequest,
    db: Session = Depends(get_db),
    customer: User = Depends(get_customer),
):
    """Complete only missing customer data while retaining the central User record."""
    if body.full_name and not (customer.name or "").strip():
        customer.name = body.full_name.strip()
    if body.phone and not (customer.secure_phone or customer.phone_number):
        phone = body.phone.strip()
        duplicate = (
            db.query(User.id)
            .filter(User.phone_number == phone, User.id != customer.id)
            .first()
        )
        if duplicate:
            raise HTTPException(
                status_code=409,
                detail="That phone / WhatsApp number is already linked to another customer.",
            )
        customer.phone_number = phone
    db.commit()
    return {
        "name": customer.name,
        "phone": customer.secure_phone or customer.phone_number,
    }


@customer_ops_router.post("/china-addresses/ensure")
def ensure_my_china_address(
    body: EnsureChinaAddressRequest,
    db: Session = Depends(get_db),
    customer: User = Depends(get_customer),
):
    mode = body.cargo_mode.lower().strip()
    if bool(body.container_id) == bool(body.air_booking_id):
        raise HTTPException(
            status_code=422, detail="Choose one valid cargo booking service."
        )
    if mode == "sea" and body.container_id:
        container = (
            db.query(Container)
            .options(joinedload(Container.origin_warehouse))
            .filter(
                Container.id == body.container_id,
                Container.status.in_(["open", "nearly_full"]),
            )
            .first()
        )
        warehouse = container.origin_warehouse if container else None
        if not warehouse or warehouse.warehouse_type not in {"sea", "both"}:
            raise HTTPException(
                status_code=404,
                detail="The selected sea cargo service has no available China warehouse.",
            )
    elif mode == "air" and body.air_booking_id:
        booking = (
            db.query(ExpressAirCargoBooking)
            .options(joinedload(ExpressAirCargoBooking.warehouse))
            .filter(
                ExpressAirCargoBooking.id == body.air_booking_id,
                ExpressAirCargoBooking.customer_id == customer.id,
            )
            .first()
        )
        warehouse = booking.warehouse if booking else None
        if not warehouse or warehouse.warehouse_type not in {"air", "both"}:
            raise HTTPException(
                status_code=404,
                detail="The selected air cargo booking has no available China warehouse.",
            )
    else:
        raise HTTPException(
            status_code=422, detail="Cargo mode does not match the selected service."
        )
    if not is_china_warehouse(warehouse):
        raise HTTPException(
            status_code=409,
            detail="This cargo service does not use a China forwarding warehouse.",
        )
    address = ensure_customer_china_address(
        db,
        customer=customer,
        warehouse=warehouse,
        cargo_mode=mode,
        destination_country=body.destination_country,
        destination_city=body.destination_city,
    )
    db.commit()
    db.refresh(address)
    return copy_ready_address(address)


async def _read_upload_with_limit(file: UploadFile, max_bytes: int) -> bytes:
    chunks = []
    total = 0
    while True:
        chunk = await file.read(1024 * 1024)
        if not chunk:
            break
        total += len(chunk)
        if total > max_bytes:
            raise HTTPException(
                status_code=400,
                detail=f"File too large. Maximum file size is {settings.MAX_IMAGE_SIZE_MB}MB.",
            )
        chunks.append(chunk)
    return b"".join(chunks)


def _build_document_fetch_candidates(document_url: str) -> List[str]:
    """Return candidate URLs, including a repair path for legacy bad public IDs."""
    raw_url = (document_url or "").strip()
    if not raw_url:
        return []

    candidates = [raw_url]
    parsed = urlparse(raw_url)
    path_parts = [part for part in (parsed.path or "").split("/") if part]

    if len(path_parts) >= 4:
        first, second, repeated, filename = path_parts[-4:]
        has_legacy_duplication = repeated == first and filename.startswith(f"{second}_")
        if has_legacy_duplication:
            repaired_parts = path_parts[:-2] + [filename]
            repaired_path = "/" + "/".join(repaired_parts)
            repaired_url = parsed._replace(path=repaired_path).geturl()
            if repaired_url not in candidates:
                candidates.append(repaired_url)

    cloudinary_signed_url = _build_cloudinary_private_download_url(raw_url)
    if cloudinary_signed_url and cloudinary_signed_url not in candidates:
        candidates.append(cloudinary_signed_url)

    return candidates


def _build_cloudinary_private_download_url(document_url: str) -> Optional[str]:
    parsed = urlparse((document_url or "").strip())
    host = (parsed.hostname or "").lower()
    if not (host == "cloudinary.com" or host.endswith(".cloudinary.com")):
        return None

    path_parts = [part for part in (parsed.path or "").split("/") if part]
    resource_index = next(
        (
            idx
            for idx, part in enumerate(path_parts)
            if part in {"image", "video", "raw"}
        ),
        None,
    )
    if resource_index is None or len(path_parts) <= resource_index + 3:
        return None

    delivery_type = path_parts[resource_index + 1]
    version_index = next(
        (
            idx
            for idx in range(resource_index + 2, len(path_parts))
            if re.fullmatch(r"v\d+", path_parts[idx])
        ),
        None,
    )
    if version_index is None or version_index >= len(path_parts) - 1:
        return None

    public_id_with_ext = "/".join(path_parts[version_index + 1 :])
    if "." not in public_id_with_ext:
        return None
    _, file_format = public_id_with_ext.rsplit(".", 1)

    configure_cloudinary()
    try:
        return cloudinary.utils.private_download_url(
            public_id_with_ext,
            file_format,
            resource_type=path_parts[resource_index],
            type=delivery_type,
            attachment=False,
            expires_at=int(datetime.utcnow().timestamp()) + 600,
        )
    except Exception:
        return None


class CreateSeaBookingRequest(BaseModel):
    container_id: str
    booked_cbm: float = Field(..., gt=0)
    goods_types: List[str] = Field(default_factory=list)
    destination_region: Optional[str] = None
    destination_country: Optional[str] = None
    carton_count: Optional[int] = None
    pickup_location_lat: Optional[float] = None
    pickup_location_lon: Optional[float] = None


class CustomerShippingLabelUpdateRequest(BaseModel):
    destination_region: Optional[str] = None
    carton_count: Optional[int] = None
    packing_list_summary: Optional[str] = None


class CustomerOrderItemRequest(BaseModel):
    product_id: str
    quantity: int = Field(..., gt=0)


class CustomerBatchOrderRequest(BaseModel):
    items: List[CustomerOrderItemRequest] = Field(..., min_length=1)
    is_urgent: bool = False


def _customer_express_booking_detail(booking: ExpressAirCargoBooking):
    photos = []
    if booking.photo_urls:
        try:
            photos = json.loads(booking.photo_urls)
            if not isinstance(photos, list):
                photos = []
        except Exception:
            photos = []
    return {
        "booking_id": str(booking.id),
        "tracking_number": booking.tracking_number,
        "service_name": booking.service_label,
        "route": booking.route_label,
        "status": booking.status,
        "weight_kg": float(booking.weight_kg),
        "shipment_date": booking.shipment_date,
        "cargo_type": booking.cargo_type.name if booking.cargo_type else "Unknown",
        "cargo_description": booking.cargo_description,
        "item_photos": photos,
        "created_at": booking.created_at,
        "shipping_mark_code": (
            booking.shipping_mark.shipping_mark_code if booking.shipping_mark else None
        ),
        "destination_region": (
            booking.shipping_mark.destination_region if booking.shipping_mark else None
        ),
        "carton_count": (
            booking.shipping_mark.carton_count if booking.shipping_mark else None
        ),
        "cargo_admin_id": (
            str(booking.cargo_admin_id) if booking.cargo_admin_id else None
        ),
        "china_address": (
            copy_ready_address(booking.customer_china_address)
            if booking.customer_china_address
            else None
        ),
        "pricing": (
            {
                "rate_id": str(booking.air_cargo_rate_id),
                "pricing_type": booking.pricing_type,
                "rate": float(booking.rate_amount),
                "currency": booking.rate_currency,
                "quantity": float(booking.quantity or 1),
                "quoted_total": float(booking.quoted_total),
            }
            if booking.quoted_total is not None
            else None
        ),
        "quotation_required": booking.air_cargo_rate_id is None,
    }


def _customer_shipment_order_summary(order: ShipmentOrder):
    status_value = (
        order.status.value if hasattr(order.status, "value") else str(order.status)
    )
    return {
        "id": str(order.id),
        "status": status_value,
        "supplier_name": order.supplier_name,
        "supplier_email": getattr(order, "supplier_email", None),
        "tracking_number": order.tracking_number,
        "order_description": order.order_description,
        "order_value": (
            float(order.order_value) if order.order_value is not None else None
        ),
        "currency": order.currency,
        "created_at": order.created_at.isoformat() if order.created_at else None,
        "updated_at": order.updated_at.isoformat() if order.updated_at else None,
    }


def _customer_sea_booking_detail(
    r: SeaBooking,
    shipment_orders=None,
    invoices=None,
    receipts=None,
    packing_lists=None,
    latest_update=None,
    latest_update_at=None,
):
    container = r.container
    route = container.route if container else None
    admin = container.admin if container else None
    shipping_mark = r.shipping_mark
    origin = (
        (route.origin if route else None)
        or (
            container.origin_warehouse.city
            if container and container.origin_warehouse
            else None
        )
        or (
            container.origin_warehouse.location
            if container and container.origin_warehouse
            else None
        )
    )
    destination = (
        (route.destination if route else None)
        or (
            container.destination_warehouse.city
            if container and container.destination_warehouse
            else None
        )
        or (
            container.destination_warehouse.location
            if container and container.destination_warehouse
            else None
        )
    )

    return {
        "sea_booking_id": str(r.id),
        "created_at": r.created_at.isoformat() if r.created_at else None,
        "source_type": r.source_type,
        "source_id": str(r.source_id) if r.source_id else None,
        "cbm_booked": float(r.cbm_booked),
        "logistics_charge": float(r.logistics_charge or 0),
        "currency": r.currency,
        "payment_status": r.payment_status,
        "payment_due_date": (
            r.payment_due_date.isoformat() if r.payment_due_date else None
        ),
        "goods_status": r.goods_status,
        "hold_reason": r.hold_reason,
        "goods_types": [
            {
                "id": str(g.goods_type.id) if g.goods_type else None,
                "name": g.goods_type.name if g.goods_type else "Unknown",
                "is_hazardous": (
                    bool(g.goods_type.is_hazardous) if g.goods_type else False
                ),
            }
            for g in r.goods_types
        ],
        "container": {
            "id": str(container.id) if container else None,
            "status": container.status if container else None,
            "container_size": container.container_size if container else None,
            "max_cbm": (
                float(container.max_cbm)
                if container and container.max_cbm is not None
                else None
            ),
            "booked_cbm": (
                float(container.booked_cbm)
                if container and container.booked_cbm is not None
                else None
            ),
            "available_cbm": float(container.available_cbm) if container else None,
            "price_per_cbm": (
                float(container.price_per_cbm)
                if container and container.price_per_cbm is not None
                else None
            ),
            "currency": (
                container.currency if container and container.currency else "TZS"
            ),
            "origin": origin,
            "destination": destination,
            "departure_date": (
                container.departure_date.isoformat()
                if container and container.departure_date
                else None
            ),
            "estimated_arrival_date": (
                container.estimated_arrival_date.isoformat()
                if container and container.estimated_arrival_date
                else None
            ),
            "arrival_date": (
                container.arrival_date.isoformat()
                if container and container.arrival_date
                else None
            ),
            "operator": {
                "id": str(admin.id) if admin else None,
                "name": admin.name if admin else None,
            },
        },
        "shipping_label": {
            "shipping_mark_code": (
                shipping_mark.shipping_mark_code if shipping_mark else None
            ),
            "destination_region": (
                shipping_mark.destination_region if shipping_mark else None
            ),
            "carton_count": shipping_mark.carton_count if shipping_mark else None,
            "packing_list_summary": (
                shipping_mark.packing_list_summary if shipping_mark else None
            ),
        },
        "tracking_number": next(
            (
                order.tracking_number
                for order in (shipment_orders or [])
                if order.tracking_number
            ),
            None,
        ),
        "shipping_label_available": shipping_mark is not None,
        "shipping_label_path": f"/label/sea/{r.id}",
        "latest_update": latest_update,
        "latest_update_at": latest_update_at,
        "shipment_orders": [
            _customer_shipment_order_summary(order) for order in (shipment_orders or [])
        ],
        "invoices": [
            {
                "id": str(invoice.id),
                "invoice_number": invoice.invoice_number,
                "amount": float(invoice.amount or 0),
                "currency": invoice.currency,
                "status": invoice.status,
                "pdf_url": invoice.pdf_url,
                "excel_url": invoice.excel_url,
                "sent_at": invoice.sent_at.isoformat() if invoice.sent_at else None,
                "paid_at": invoice.paid_at.isoformat() if invoice.paid_at else None,
                "created_at": (
                    invoice.created_at.isoformat() if invoice.created_at else None
                ),
            }
            for invoice in (invoices or [])
        ],
        "receipts": [
            {
                "id": str(receipt.id),
                "receipt_number": receipt.receipt_number,
                "amount": float(receipt.amount or 0),
                "currency": receipt.currency,
                "status": receipt.status or "issued",
                "pdf_url": receipt.pdf_url,
                "generated_at": (
                    receipt.generated_at.isoformat() if receipt.generated_at else None
                ),
                "voided_at": (
                    receipt.voided_at.isoformat() if receipt.voided_at else None
                ),
            }
            for receipt in (receipts or [])
        ],
        "packing_lists": [
            {
                "id": str(row.id),
                "status": row.status,
                "shipment_stage": row.shipment_stage,
                "notes": row.notes,
                "total_cartons": row.total_cartons,
                "total_cbm": float(row.total_cbm or 0),
                "total_weight_kg": float(row.total_weight_kg or 0),
                "received_cbm": float(row.received_cbm or 0),
                "loaded_cbm": float(row.loaded_cbm or 0),
                "updated_at": row.updated_at.isoformat() if row.updated_at else None,
            }
            for row in (packing_lists or [])
        ],
    }


def _customer_batch_summary(batch: SourcingBatch) -> dict:
    """Serialize public customer batch data without booking-only shipping mark fields."""
    goods_types = []
    seen_goods_type_ids = set()
    for product in batch.products or []:
        goods_type = product.goods_type
        if not goods_type or goods_type.id in seen_goods_type_ids:
            continue
        seen_goods_type_ids.add(goods_type.id)
        goods_types.append(
            {
                "id": str(goods_type.id),
                "name": goods_type.name,
                "is_hazardous": bool(goods_type.is_hazardous),
            }
        )
    return {
        "id": str(batch.id),
        "title": batch.title,
        "description": batch.description,
        "currency": batch.currency or "TZS",
        "shipping_fee_per_cbm": float(batch.shipping_fee_per_cbm or 0),
        "shipping_method": batch.shipping_method or "PER_CBM",
        "status": batch.status,
        "created_at": batch.created_at.isoformat() if batch.created_at else None,
        "goods_types": goods_types,
        "products_count": len(batch.products or []),
        "agent": {
            "name": batch.agent.name if batch.agent else "Unknown Agent",
            "profile_image_url": (
                batch.agent.profile_image_url
                if batch.agent and batch.agent.profile_image_url
                else None
            ),
        },
    }


def _get_booked_cbm_map(db: Session, container_ids: list[str]) -> dict[str, float]:
    if not container_ids:
        return {}

    rows = (
        db.query(
            SeaBooking.container_id,
            func.coalesce(func.sum(SeaBooking.cbm_booked), 0).label("booked_cbm"),
        )
        .filter(SeaBooking.container_id.in_(container_ids))
        .group_by(SeaBooking.container_id)
        .all()
    )
    return {
        str(container_id): float(booked_cbm or 0) for container_id, booked_cbm in rows
    }


@customer_ops_router.get("/containers")
def list_available_containers(
    db: Session = Depends(get_db),
    customer: User = Depends(get_customer),
):
    del customer  # auth gate only

    containers = (
        db.query(Container)
        .options(
            joinedload(Container.admin),
            joinedload(Container.route),
            joinedload(Container.origin_warehouse),
            joinedload(Container.destination_warehouse),
        )
        .filter(Container.status.in_(["open", "nearly_full", "full"]))
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
        fill_percentage = round((booked_cbm / max_cbm) * 100, 2) if max_cbm > 0 else 0.0

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
                "operator": c.admin.name if c.admin else "Cargo Company",
                "container_size": c.container_size,
                "status": c.status,
                "max_cbm": float(c.max_cbm),
                "booked_cbm": booked_cbm,
                "available_cbm": available_cbm,
                "fill_percentage": fill_percentage,
                "price_per_cbm": float(c.price_per_cbm),
                "currency": c.currency or "TZS",
                "origin": origin,
                "destination": destination,
                "destination_country": (
                    c.destination_warehouse.country
                    if c.destination_warehouse and c.destination_warehouse.country
                    else None
                ),
                "port_origin": origin,
                "destination_port": destination,
                "latitude": (
                    float(c.origin_warehouse.latitude)
                    if c.origin_warehouse and c.origin_warehouse.latitude is not None
                    else None
                ),
                "longitude": (
                    float(c.origin_warehouse.longitude)
                    if c.origin_warehouse and c.origin_warehouse.longitude is not None
                    else None
                ),
                "departure_date": (
                    c.departure_date.isoformat() if c.departure_date else None
                ),
                "estimated_arrival_date": (
                    c.estimated_arrival_date.isoformat()
                    if c.estimated_arrival_date
                    else None
                ),
            }
        )
    return results


@customer_ops_router.post("/sea-bookings")
def create_customer_sea_booking(
    body: CreateSeaBookingRequest,
    db: Session = Depends(get_db),
    customer: User = Depends(get_customer),
):
    container = (
        db.query(Container)
        .filter(
            Container.id == body.container_id,
            Container.status.in_(["open", "nearly_full"]),
        )
        .with_for_update()
        .first()
    )
    if not container:
        raise HTTPException(status_code=404, detail="Container not available")
    require_company_service_bookable(
        db,
        operator_id=container.admin_id,
        service_type="shared_container",
    )

    current_booked_cbm = (
        db.query(func.coalesce(func.sum(SeaBooking.cbm_booked), 0))
        .filter(SeaBooking.container_id == container.id)
        .scalar()
        or 0
    )
    current_booked_cbm = float(current_booked_cbm)
    current_available_cbm = max(float(container.max_cbm) - current_booked_cbm, 0)

    if current_available_cbm < body.booked_cbm:
        raise HTTPException(
            status_code=400,
            detail=f"Insufficient space. Available: {current_available_cbm:.2f} CBM",
        )

    destination_region = (
        body.destination_region.strip()
        if body.destination_region and body.destination_region.strip()
        else "Unknown"
    )
    logistics_charge = float(container.price_per_cbm) * body.booked_cbm
    sea_booking = SeaBooking(
        container_id=container.id,
        user_id=customer.id,
        source_type="direct",
        source_id=None,
        cbm_booked=body.booked_cbm,
        logistics_charge=logistics_charge,
        currency=container.currency,
        payment_status="pending",
        payment_due_date=datetime.utcnow() + timedelta(days=14),
        goods_status="ready",
    )
    forwarding_warehouse = container.origin_warehouse
    if forwarding_warehouse and is_china_warehouse(forwarding_warehouse):
        destination_country = (
            (
                container.destination_warehouse.country
                if container.destination_warehouse
                else None
            )
            or body.destination_country
            or "Destination country"
        )
        customer_address = ensure_customer_china_address(
            db,
            customer=customer,
            warehouse=forwarding_warehouse,
            cargo_mode="sea",
            destination_country=destination_country,
            destination_city=destination_region,
        )
        sea_booking.customer_china_address_id = customer_address.id
    db.add(sea_booking)
    db.flush()

    create_shipping_mark(
        db,
        booking_id=sea_booking.id,
        cargo_type="SEA",
        customer_name=customer.name,
        customer_phone=customer.phone_number,
        destination_region=destination_region,
        packing_list_summary=(
            f"Booked {float(body.booked_cbm):.2f} CBM"
            + (f" to {destination_region}" if destination_region != "Unknown" else "")
        ),
        carton_count=body.carton_count,
        sea_booking_id=sea_booking.id,
    )

    auto_shipment_order = ensure_shipment_order_for_sea_booking(
        db, sea_booking, destination_region=destination_region
    )

    if body.goods_types:
        goods = (
            db.query(GoodsType)
            .filter(GoodsType.id.in_(body.goods_types), GoodsType.is_active.is_(True))
            .all()
        )
        for g in goods:
            db.add(
                SeaBookingGoods(
                    sea_booking_id=sea_booking.id,
                    goods_type_id=g.id,
                )
            )

    container.booked_cbm = current_booked_cbm + body.booked_cbm
    fill_pct = (float(container.booked_cbm) / float(container.max_cbm)) * 100
    if float(container.booked_cbm) >= float(container.max_cbm):
        container.status = "full"
    elif fill_pct >= 80:
        container.status = "nearly_full"

    db.commit()
    db.refresh(sea_booking)

    # Create tracking event for sea booking creation
    TrackingService.create_tracking_event(
        db=db,
        entity_type="sea_booking",
        entity_id=str(sea_booking.id),
        event_type="sea_booking_created",
        description=f"Sea cargo sea booking created for {body.booked_cbm} CBM",
        triggered_by=str(customer.id),
        extra_data={
            "container_id": str(container.id),
            "cbm_booked": float(sea_booking.cbm_booked),
            "logistics_charge": float(sea_booking.logistics_charge),
            "goods_types_count": len(body.goods_types or []),
            "destination_region": destination_region,
            "carton_count": body.carton_count,
            "payment_status": sea_booking.payment_status,
        },
    )

    log_action(
        db=db,
        action="customer_booked_cbm",
        user_id=customer.id,
        entity_type="sea_booking",
        entity_id=sea_booking.id,
        metadata={
            "container_id": str(container.id),
            "cbm_amount": body.booked_cbm,
            "goods_count": len(body.goods_types or []),
            "destination_region": destination_region,
            "carton_count": body.carton_count,
        },
    )

    notify_container_booking_created(db, container, sea_booking, customer)

    db.commit()
    db.refresh(sea_booking)

    return {
        "id": str(sea_booking.id),
        "sea_booking_id": str(sea_booking.id),
        "container_id": str(container.id),
        "cbm_booked": float(sea_booking.cbm_booked),
        "logistics_charge": float(sea_booking.logistics_charge),
        "currency": sea_booking.currency,
        "tracking_number": auto_shipment_order.tracking_number,
        "payment_status": sea_booking.payment_status,
        "goods_status": sea_booking.goods_status,
        "china_address": (
            copy_ready_address(
                db.query(CustomerChinaAddress)
                .options(
                    joinedload(CustomerChinaAddress.warehouse),
                    joinedload(CustomerChinaAddress.customer),
                )
                .filter(
                    CustomerChinaAddress.id == sea_booking.customer_china_address_id
                )
                .first()
            )
            if sea_booking.customer_china_address_id
            else None
        ),
        "message": "Sea booking created successfully",
    }


@customer_ops_router.get("/sea-bookings")
def list_customer_sea_bookings(
    db: Session = Depends(get_db),
    customer: User = Depends(get_customer),
):
    sea_bookings = (
        db.query(SeaBooking)
        .options(
            joinedload(SeaBooking.container).joinedload(Container.admin),
            joinedload(SeaBooking.container).joinedload(Container.route),
            joinedload(SeaBooking.container).joinedload(Container.origin_warehouse),
            joinedload(SeaBooking.container).joinedload(
                Container.destination_warehouse
            ),
            joinedload(SeaBooking.goods_types).joinedload(SeaBookingGoods.goods_type),
            joinedload(SeaBooking.shipping_mark),
        )
        .filter(SeaBooking.user_id == customer.id)
        .order_by(SeaBooking.created_at.desc())
        .all()
    )

    sea_booking_ids = [sea_booking.id for sea_booking in sea_bookings]
    shipment_orders_by_sea_booking: dict = {}
    latest_update_map: dict = {}

    if sea_booking_ids:
        shipment_orders = (
            db.query(ShipmentOrder)
            .filter(
                ShipmentOrder.created_by_user_id == customer.id,
                ShipmentOrder.sea_booking_id.in_(sea_booking_ids),
            )
            .order_by(ShipmentOrder.created_at.desc())
            .all()
        )
        for order in shipment_orders:
            key = order.sea_booking_id
            shipment_orders_by_sea_booking.setdefault(key, []).append(order)

        tracking_events = (
            db.query(TrackingEvent)
            .filter(
                TrackingEvent.entity_type == "sea_booking",
                TrackingEvent.entity_id.in_(sea_booking_ids),
            )
            .order_by(TrackingEvent.timestamp.desc())
            .all()
        )
        for event in tracking_events:
            if event.entity_id not in latest_update_map:
                latest_update_map[event.entity_id] = {
                    "latest_update": event.description,
                    "latest_update_at": (
                        event.timestamp.isoformat() if event.timestamp else None
                    ),
                }

    return [
        _customer_sea_booking_detail(
            r,
            shipment_orders=shipment_orders_by_sea_booking.get(r.id, []),
            latest_update=latest_update_map.get(r.id, {}).get("latest_update"),
            latest_update_at=latest_update_map.get(r.id, {}).get("latest_update_at"),
        )
        for r in sea_bookings
    ]


@customer_ops_router.get("/sea-bookings/{sea_booking_id}")
def get_customer_sea_booking_detail(
    sea_booking_id: str,
    db: Session = Depends(get_db),
    customer: User = Depends(get_customer),
):
    sea_booking = (
        db.query(SeaBooking)
        .options(
            joinedload(SeaBooking.container).joinedload(Container.admin),
            joinedload(SeaBooking.container).joinedload(Container.route),
            joinedload(SeaBooking.container).joinedload(Container.origin_warehouse),
            joinedload(SeaBooking.container).joinedload(
                Container.destination_warehouse
            ),
            joinedload(SeaBooking.goods_types).joinedload(SeaBookingGoods.goods_type),
            joinedload(SeaBooking.shipping_mark),
        )
        .filter(
            SeaBooking.id == sea_booking_id,
            SeaBooking.user_id == customer.id,
        )
        .first()
    )
    if not sea_booking:
        raise HTTPException(status_code=404, detail="Sea booking not found")

    shipment_orders = (
        db.query(ShipmentOrder)
        .filter(
            ShipmentOrder.sea_booking_id == sea_booking.id,
            ShipmentOrder.created_by_user_id == customer.id,
        )
        .order_by(ShipmentOrder.created_at.desc())
        .all()
    )
    invoices = (
        db.query(SeaBookingInvoice)
        .filter(
            SeaBookingInvoice.sea_booking_id == sea_booking.id,
            SeaBookingInvoice.customer_id == customer.id,
        )
        .order_by(SeaBookingInvoice.created_at.desc())
        .all()
    )
    receipts = (
        db.query(Receipt)
        .filter(Receipt.sea_booking_id == sea_booking.id)
        .order_by(Receipt.generated_at.desc())
        .all()
    )
    packing_lists = (
        db.query(SeaBookingPackingList)
        .filter(
            SeaBookingPackingList.sea_booking_id == sea_booking.id,
            SeaBookingPackingList.customer_id == customer.id,
        )
        .order_by(SeaBookingPackingList.created_at.desc())
        .all()
    )
    latest_event = (
        db.query(TrackingEvent)
        .filter(
            TrackingEvent.entity_type == "sea_booking",
            TrackingEvent.entity_id == sea_booking.id,
        )
        .order_by(TrackingEvent.timestamp.desc())
        .first()
    )

    return _customer_sea_booking_detail(
        sea_booking,
        shipment_orders=shipment_orders,
        invoices=invoices,
        receipts=receipts,
        packing_lists=packing_lists,
        latest_update=latest_event.description if latest_event else None,
        latest_update_at=(
            latest_event.timestamp.isoformat()
            if latest_event and latest_event.timestamp
            else None
        ),
    )


@customer_ops_router.get("/sea-bookings/{sea_booking_id}/invoices/{invoice_id}/pdf")
def stream_customer_invoice_pdf(
    sea_booking_id: str,
    invoice_id: str,
    db: Session = Depends(get_db),
    customer: User = Depends(get_customer),
):
    sea_booking = (
        db.query(SeaBooking)
        .filter(
            SeaBooking.id == sea_booking_id,
            SeaBooking.user_id == customer.id,
        )
        .first()
    )
    if not sea_booking:
        raise HTTPException(status_code=404, detail="Sea booking not found")

    invoice = (
        db.query(SeaBookingInvoice)
        .filter(
            SeaBookingInvoice.id == invoice_id,
            SeaBookingInvoice.sea_booking_id == sea_booking.id,
            SeaBookingInvoice.customer_id == customer.id,
        )
        .first()
    )
    if not invoice or not invoice.pdf_url:
        raise HTTPException(status_code=404, detail="Invoice PDF not found")

    filename = f"{invoice.invoice_number or 'invoice'}.pdf"
    return _stream_cloudinary_document(invoice.pdf_url, filename=filename)


@customer_ops_router.get("/sea-bookings/{sea_booking_id}/receipts/{receipt_id}/pdf")
def stream_customer_receipt_pdf(
    sea_booking_id: str,
    receipt_id: str,
    db: Session = Depends(get_db),
    customer: User = Depends(get_customer),
):
    sea_booking = (
        db.query(SeaBooking)
        .filter(
            SeaBooking.id == sea_booking_id,
            SeaBooking.user_id == customer.id,
        )
        .first()
    )
    if not sea_booking:
        raise HTTPException(status_code=404, detail="Sea booking not found")

    receipt = (
        db.query(Receipt)
        .filter(
            Receipt.id == receipt_id,
            Receipt.sea_booking_id == sea_booking.id,
        )
        .first()
    )
    if not receipt or not receipt.pdf_url:
        raise HTTPException(status_code=404, detail="Receipt PDF not found")

    filename = f"{receipt.receipt_number or 'receipt'}.pdf"
    return _stream_cloudinary_document(receipt.pdf_url, filename=filename)


@customer_ops_router.get("/sea-bookings/{sea_booking_id}/packing-lists")
def get_customer_sea_booking_packing_lists(
    sea_booking_id: str,
    db: Session = Depends(get_db),
    customer: User = Depends(get_customer),
):
    sea_booking = (
        db.query(SeaBooking)
        .filter(
            SeaBooking.id == sea_booking_id,
            SeaBooking.user_id == customer.id,
        )
        .first()
    )
    if not sea_booking:
        raise HTTPException(status_code=404, detail="Sea booking not found")

    packing_lists = (
        db.query(SeaBookingPackingList)
        .filter(
            SeaBookingPackingList.sea_booking_id == sea_booking.id,
            SeaBookingPackingList.customer_id == customer.id,
        )
        .order_by(SeaBookingPackingList.created_at.desc())
        .all()
    )
    payload = []
    for packing_list in packing_lists:
        items = (
            db.query(SeaBookingPackingListItem)
            .filter(SeaBookingPackingListItem.packing_list_id == packing_list.id)
            .order_by(SeaBookingPackingListItem.created_at.asc())
            .all()
        )
        payload.append(
            {
                "id": str(packing_list.id),
                "status": packing_list.status,
                "shipment_stage": packing_list.shipment_stage,
                "notes": packing_list.notes,
                "total_cartons": packing_list.total_cartons,
                "total_cbm": float(packing_list.total_cbm or 0),
                "total_weight_kg": float(packing_list.total_weight_kg or 0),
                "received_cbm": float(packing_list.received_cbm or 0),
                "loaded_cbm": float(packing_list.loaded_cbm or 0),
                "updated_at": (
                    packing_list.updated_at.isoformat()
                    if packing_list.updated_at
                    else None
                ),
                "items": [
                    {
                        "id": str(item.id),
                        "item_name": item.item_name,
                        "supplier_details": item.supplier_details,
                        "cartons": item.cartons,
                        "cbm": float(item.cbm or 0),
                        "weight_kg": float(item.weight_kg or 0),
                        "status": item.status,
                        "notes": item.notes,
                        "updated_at": (
                            item.updated_at.isoformat() if item.updated_at else None
                        ),
                    }
                    for item in items
                ],
            }
        )

    return {"sea_booking_id": str(sea_booking.id), "packing_lists": payload}


@customer_ops_router.get("/batches/available")
def list_available_batches(
    db: Session = Depends(get_db),
    customer: User = Depends(get_customer),
):
    del customer  # auth gate only

    batches = (
        db.query(SourcingBatch)
        .options(
            joinedload(SourcingBatch.products).joinedload(SourcingProduct.goods_type),
            joinedload(SourcingBatch.agent),  # Load the agent relationship
        )
        .filter(SourcingBatch.status == "open")
        .order_by(SourcingBatch.created_at.desc())
        .all()
    )

    return [_customer_batch_summary(batch) for batch in batches]


@customer_ops_router.get("/batches/{batch_id}")
def get_customer_batch_detail(
    batch_id: str,
    db: Session = Depends(get_db),
    customer: User = Depends(get_customer),
):
    del customer  # auth gate only

    batch = (
        db.query(SourcingBatch)
        .options(
            joinedload(SourcingBatch.products).joinedload(SourcingProduct.goods_type),
            joinedload(SourcingBatch.agent),  # Load the agent relationship
        )
        .filter(SourcingBatch.id == batch_id, SourcingBatch.status == "open")
        .first()
    )
    if not batch:
        raise HTTPException(status_code=404, detail="Batch not available")

    return _customer_batch_summary(batch)


@customer_ops_router.get("/batches/{batch_id}/products")
def get_customer_batch_products(
    batch_id: str,
    db: Session = Depends(get_db),
    customer: User = Depends(get_customer),
):
    del customer  # auth gate only

    batch = (
        db.query(SourcingBatch)
        .filter(SourcingBatch.id == batch_id, SourcingBatch.status == "open")
        .first()
    )
    if not batch:
        raise HTTPException(status_code=404, detail="Batch not available")

    products = (
        db.query(SourcingProduct)
        .filter(SourcingProduct.batch_id == batch.id)
        .order_by(SourcingProduct.created_at.desc())
        .all()
    )

    return [
        {
            "id": str(product.id),
            "name": product.name,
            "description": product.description,
            "cbm_per_unit": float(product.cbm_per_unit),
            "price_per_unit": float(product.price_per_unit),
            "image_url": build_optimized_cloudinary_image_url(product.image_url),
            "created_at": (
                product.created_at.isoformat() if product.created_at else None
            ),
        }
        for product in products
    ]


@customer_ops_router.post("/batches/{batch_id}/order")
def create_customer_batch_order(
    batch_id: str,
    body: CustomerBatchOrderRequest,
    db: Session = Depends(get_db),
    customer: User = Depends(get_customer),
):
    batch = (
        db.query(SourcingBatch)
        .filter(SourcingBatch.id == batch_id, SourcingBatch.status == "open")
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
        customer_id=customer.id,
        submitted_by="user",
        total_product_amount=round(total_product_amount, 2),
        commission_amount=commission_amount,
        currency=batch.currency or "TZS",
        commission_status="pending",
        delivery_status="not_arrived",
        is_urgent=body.is_urgent,
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

    log_action(
        db=db,
        action="customer_batch_order_created",
        user_id=customer.id,
        entity_type="sourcing_order",
        entity_id=order.id,
        metadata={
            "batch_id": str(batch.id),
            "items_count": len(order_lines),
            "total_product_amount": round(total_product_amount, 2),
        },
    )

    if body.is_urgent:
        notify_urgent_sourcing_request(db, batch, order, customer)

    db.commit()

    return {
        "id": str(order.id),
        "batch_id": str(batch.id),
        "items_count": len(order_lines),
        "total_product_amount": round(total_product_amount, 2),
        "currency": batch.currency or "TZS",
        "delivery_status": "not_arrived",
        "is_urgent": bool(body.is_urgent),
        "message": "Order placed successfully",
    }


@customer_ops_router.get("/express-air-cargo/options")
def customer_express_air_cargo_options(
    cargo_admin_id: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    customer: User = Depends(get_customer),
):
    del customer  # auth gate only
    cargo_types = (
        db.query(GoodsType)
        .filter(GoodsType.is_active == True)
        .order_by(GoodsType.name.asc())
        .all()
    )
    active_rates = (
        db.query(AirCargoRate)
        .options(joinedload(AirCargoRate.goods_type))
        .filter(
            AirCargoRate.is_active.is_(True),
            *(
                [AirCargoRate.cargo_admin_id == cargo_admin_id]
                if cargo_admin_id
                else []
            ),
        )
        .order_by(AirCargoRate.shipping_method, AirCargoRate.price)
        .all()
    )
    rates_by_goods_type = {}
    for rate in active_rates:
        rates_by_goods_type.setdefault(str(rate.goods_type_id), []).append(
            serialize_rate(rate)
        )
    unique_routes = sorted({rate.route for rate in active_rates if rate.route})
    return {
        "service_name": "China → Africa Air Cargo",
        "route": unique_routes[0] if len(unique_routes) == 1 else "China → Africa",
        "delivery_window": "Varies by selected service",
        "allowed_weight_unit": "KG",
        "cargo_types": [
            {
                "id": str(gt.id),
                "name": gt.name,
                "is_hazardous": gt.is_hazardous,
                "requires_special_handling": gt.requires_special_handling,
                "shipping_policy": get_air_cargo_goods_policy(gt.name),
                "rates": rates_by_goods_type.get(str(gt.id), []),
            }
            for gt in cargo_types
        ],
    }


@customer_ops_router.post("/express-air-cargo/upload-photo")
async def customer_upload_express_air_cargo_photo(
    file: UploadFile = File(...),
    customer: User = Depends(get_customer),
):
    allowed_types = set(settings.ALLOWED_IMAGE_TYPES) | {"image/gif"}
    if file.content_type not in allowed_types:
        raise HTTPException(
            status_code=400,
            detail="Invalid file type. Only JPEG, PNG, GIF, and WebP images are allowed.",
        )

    max_bytes = settings.MAX_IMAGE_SIZE_MB * 1024 * 1024
    content = await _read_upload_with_limit(file, max_bytes)
    _, file_extension = validated_image_format(
        content, file.content_type, allow_gif=True
    )

    with tempfile.NamedTemporaryFile(delete=False, suffix=f".{file_extension}") as tmp:
        tmp.write(content)
        tmp_path = tmp.name

    try:
        result = upload_to_cloudinary(tmp_path, str(customer.id), "express_air_cargo")
        return {
            "success": True,
            "image_url": result["secure_url"],
            "public_id": result["public_id"],
        }
    finally:
        os.unlink(tmp_path)


@customer_ops_router.post("/express-air-cargo/book")
def customer_create_express_air_booking(
    cargo_type_id: str = Form(...),
    weight_kg: float = Form(...),
    shipment_date: datetime = Form(...),
    cargo_description: Optional[str] = Form(None),
    destination_region: str = Form(...),
    destination_country: str = Form("Tanzania"),
    carton_count: int = Form(1),
    item_photos: Optional[str] = Form("[]"),
    air_cargo_rate_id: Optional[str] = Form(None),
    quantity: float = Form(1),
    certification_acknowledged: bool = Form(False),
    customer_china_address_id: Optional[str] = Form(None),
    cargo_admin_id: Optional[str] = Form(None),
    warehouse_id: Optional[str] = Form(None),
    db: Session = Depends(get_db),
    customer: User = Depends(get_customer),
):
    if weight_kg <= 0:
        raise HTTPException(status_code=400, detail="Weight must be greater than 0 KG")

    if shipment_date.tzinfo is not None:
        shipment_date = shipment_date.astimezone(timezone.utc).replace(tzinfo=None)
    if shipment_date < datetime.utcnow() + timedelta(hours=6):
        raise HTTPException(
            status_code=400, detail="Shipment date must be at least 6 hours from now"
        )
    if not destination_region.strip():
        raise HTTPException(status_code=400, detail="Destination region is required")
    if not destination_country.strip():
        raise HTTPException(status_code=400, detail="Destination country is required")
    if carton_count <= 0:
        raise HTTPException(status_code=400, detail="Carton count must be at least 1")
    if quantity <= 0:
        raise HTTPException(
            status_code=400, detail="Quantity must be greater than zero"
        )

    cargo_type = (
        db.query(GoodsType)
        .filter(GoodsType.id == cargo_type_id, GoodsType.is_active == True)
        .first()
    )
    if not cargo_type:
        raise HTTPException(status_code=400, detail="Invalid cargo type selected")
    goods_policy = get_air_cargo_goods_policy(cargo_type.name)
    if goods_policy["requires_certification"] and not certification_acknowledged:
        raise HTTPException(
            status_code=422,
            detail=(
                "Import certification acknowledgement is required for this Goods Type. "
                "Food, medicines, cosmetics, fruits, perfumes, and supplements cannot "
                "use 1–3 day Express until the required permit has been obtained."
            ),
        )

    selected_rate = None
    quoted_total = None
    if air_cargo_rate_id:
        selected_rate = get_matching_rate(
            db,
            rate_id=air_cargo_rate_id,
            goods_type_id=str(cargo_type.id),
            weight_kg=weight_kg,
            cargo_admin_id=cargo_admin_id,
        )
        quoted_total = calculate_rate_total(
            selected_rate, weight_kg=weight_kg, quantity=quantity
        )

    try:
        photos = json.loads(item_photos or "[]")
        if not isinstance(photos, list):
            raise ValueError
    except Exception:
        raise HTTPException(
            status_code=400, detail="item_photos must be a JSON array of URLs"
        )

    booking = ExpressAirCargoBooking(
        customer_id=customer.id,
        cargo_type_id=cargo_type.id,
        cargo_description=cargo_description,
        weight_kg=round(weight_kg, 2),
        air_cargo_rate_id=selected_rate.id if selected_rate else None,
        pricing_type=selected_rate.pricing_type if selected_rate else None,
        rate_amount=selected_rate.price if selected_rate else None,
        rate_currency=selected_rate.currency if selected_rate else None,
        quantity=round(quantity, 2) if selected_rate else None,
        quoted_total=quoted_total,
        route_label=selected_rate.route if selected_rate else DEFAULT_AIR_CARGO_ROUTE,
        service_label=(
            f"{selected_rate.shipping_method} — {selected_rate.transit_time}"
            if selected_rate
            else "Quotation required"
        ),
        shipment_date=shipment_date,
        photo_urls=json.dumps(photos),
        status="pending",
    )
    customer_address, forwarding_warehouse = prepare_user_air_china_address(
        db,
        user=customer,
        destination_country=destination_country.strip(),
        destination_city=destination_region.strip(),
        preferred_address_id=customer_china_address_id,
        cargo_admin_id=cargo_admin_id,
        warehouse_id=warehouse_id,
    )
    booking.cargo_admin_id = forwarding_warehouse.admin_id
    booking.warehouse_id = forwarding_warehouse.id
    booking.customer_china_address_id = customer_address.id
    db.add(booking)
    db.flush()
    ensure_shipment_order_for_air_booking(
        db, booking, destination_region=destination_region
    )

    create_shipping_mark(
        db,
        booking_id=booking.id,
        cargo_type="AIR",
        customer_name=customer.name,
        customer_phone=customer.phone_number,
        destination_region=destination_region,
        packing_list_summary=cargo_description,
        carton_count=carton_count,
        air_booking_id=booking.id,
    )

    db.commit()
    db.refresh(booking)

    # Create tracking event for the new booking
    TrackingService.create_tracking_event(
        db=db,
        entity_type="booking",
        entity_id=str(booking.id),
        event_type="booking_created",
        description=f"Express air cargo booking created for {weight_kg}kg shipment",
        triggered_by=str(customer.id),
        extra_data={
            "cargo_type": (
                cargo_type.name if hasattr(cargo_type, "name") else str(cargo_type.id)
            ),
            "weight_kg": float(booking.weight_kg),
            "destination_region": destination_region,
            "carton_count": carton_count,
            "status": booking.status,
            "quoted_total": float(quoted_total) if quoted_total is not None else None,
            "quotation_required": selected_rate is None,
        },
    )

    log_action(
        db=db,
        action="CUSTOMER_EXPRESS_AIR_BOOKING_CREATED",
        user_id=customer.id,
        entity_type="express_air_booking",
        entity_id=booking.id,
        metadata={
            "cargo_type_id": str(cargo_type.id),
            "weight_kg": float(booking.weight_kg),
            "destination_region": destination_region,
            "carton_count": carton_count,
            "air_cargo_rate_id": str(selected_rate.id) if selected_rate else None,
            "quoted_total": float(quoted_total) if quoted_total is not None else None,
        },
    )
    notify_air_cargo_booking_created(db, booking, customer)
    db.commit()
    db.refresh(booking)
    return _customer_express_booking_detail(booking)


@customer_ops_router.get("/express-air-cargo/bookings")
def customer_list_express_air_bookings(
    db: Session = Depends(get_db),
    customer: User = Depends(get_customer),
):
    bookings = (
        db.query(ExpressAirCargoBooking)
        .options(
            joinedload(ExpressAirCargoBooking.cargo_type),
            joinedload(ExpressAirCargoBooking.shipping_mark),
        )
        .filter(ExpressAirCargoBooking.customer_id == customer.id)
        .order_by(ExpressAirCargoBooking.created_at.desc())
        .all()
    )
    return [_customer_express_booking_detail(b) for b in bookings]


@customer_ops_router.get("/express-air-cargo/{booking_id}")
def customer_get_express_air_booking_detail(
    booking_id: str,
    db: Session = Depends(get_db),
    customer: User = Depends(get_customer),
):
    booking = (
        db.query(ExpressAirCargoBooking)
        .options(
            joinedload(ExpressAirCargoBooking.cargo_type),
            joinedload(ExpressAirCargoBooking.shipping_mark),
        )
        .filter(
            ExpressAirCargoBooking.id == booking_id,
            ExpressAirCargoBooking.customer_id == customer.id,
        )
        .first()
    )
    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found")
    return _customer_express_booking_detail(booking)


@customer_ops_router.get("/express-air-cargo/{booking_id}/shipping-label")
def customer_get_express_air_cargo_label(
    booking_id: str,
    db: Session = Depends(get_db),
    customer: User = Depends(get_customer),
):
    booking = (
        db.query(ExpressAirCargoBooking)
        .options(
            joinedload(ExpressAirCargoBooking.cargo_type),
            joinedload(ExpressAirCargoBooking.shipping_mark),
        )
        .filter(
            ExpressAirCargoBooking.id == booking_id,
            ExpressAirCargoBooking.customer_id == customer.id,
        )
        .first()
    )
    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found")

    mark = booking.shipping_mark
    if not mark:
        mark = create_shipping_mark(
            db,
            booking_id=booking.id,
            cargo_type="AIR",
            customer_name=customer.name,
            customer_phone=customer.phone_number,
            destination_region="Unknown",
            packing_list_summary=booking.cargo_description,
            carton_count=1,
            air_booking_id=booking.id,
        )
        db.commit()
        db.refresh(booking)
        mark = booking.shipping_mark

    photos = []
    if booking.photo_urls:
        try:
            photos = json.loads(booking.photo_urls)
            if not isinstance(photos, list):
                photos = []
        except Exception:
            photos = []

    # Get cargo admin warehouse information if available
    warehouse_info = None
    if booking.cargo_admin_id:
        # Get the air cargo warehouse for the cargo admin (prefer air or both type)
        warehouse = (
            db.query(Warehouse)
            .filter(
                Warehouse.admin_id == booking.cargo_admin_id,
                Warehouse.warehouse_type.in_(["air", "both"]),
            )
            .order_by(Warehouse.created_at)
            .first()
        )

        if warehouse:
            warehouse_info = {
                "name": warehouse.name,
                "address": warehouse.address or warehouse.location,
                "city": warehouse.city,
                "state": warehouse.state,
                "country": warehouse.country,
                "postal_code": warehouse.postal_code,
                "contact_name": warehouse.contact_name_1,
                "contact_phone": warehouse.contact_phone_1,
                "full_address": f"{warehouse.address or warehouse.location}, {warehouse.city or ''}, {warehouse.state or ''}, {warehouse.country or ''}".strip(
                    ", "
                ),
                "warehouse_type": warehouse.warehouse_type,
            }

    return {
        "company": operator_document_branding(db, booking.cargo_admin_id),
        "booking": {
            "booking_id": str(booking.id),
            "tracking_number": booking.tracking_number,
            "status": booking.status,
            "shipment_date": booking.shipment_date,
            "weight_kg": float(booking.weight_kg),
            "cargo_type": (
                {"id": str(booking.cargo_type.id), "name": booking.cargo_type.name}
                if booking.cargo_type
                else None
            ),
            "route_label": booking.route_label,
            "service_label": booking.service_label,
            "created_at": booking.created_at,
        },
        "customer": {
            "id": str(customer.id),
            "name": customer.name,
            "phone_number": customer.phone_number,
        },
        "label": build_printable_label(mark),
        "item_photos": photos,
        "warehouse": warehouse_info,
    }


@customer_ops_router.patch("/express-air-cargo/{booking_id}/shipping-label")
def customer_update_express_air_label(
    booking_id: str,
    body: CustomerShippingLabelUpdateRequest,
    db: Session = Depends(get_db),
    customer: User = Depends(get_customer),
):
    booking = (
        db.query(ExpressAirCargoBooking)
        .options(joinedload(ExpressAirCargoBooking.shipping_mark))
        .filter(
            ExpressAirCargoBooking.id == booking_id,
            ExpressAirCargoBooking.customer_id == customer.id,
        )
        .first()
    )
    if not booking or not booking.shipping_mark:
        raise HTTPException(status_code=404, detail="Shipping label not found")

    mark = booking.shipping_mark
    if body.destination_region is not None:
        mark.destination_region = (
            body.destination_region.strip() or mark.destination_region
        )
    if body.carton_count is not None:
        if body.carton_count <= 0:
            raise HTTPException(
                status_code=400, detail="Carton count must be at least 1"
            )
        mark.carton_count = body.carton_count
    if body.packing_list_summary is not None:
        mark.packing_list_summary = body.packing_list_summary.strip() or None

    db.commit()
    db.refresh(mark)
    return {"message": "Shipping label updated", "label": build_printable_label(mark)}


@customer_ops_router.get("/orders")
def list_customer_orders(
    db: Session = Depends(get_db),
    customer: User = Depends(get_customer),
):
    orders = (
        db.query(SourcingOrder)
        .options(
            joinedload(SourcingOrder.batch),
            joinedload(SourcingOrder.items),
        )
        .filter(SourcingOrder.customer_id == customer.id)
        .order_by(SourcingOrder.created_at.desc())
        .all()
    )

    return [
        {
            "id": str(o.id),
            "batch_id": str(o.batch_id) if o.batch_id else None,
            "batch_title": o.batch.title if o.batch else None,
            "total_product_amount": float(o.total_product_amount or 0),
            "delivery_status": o.delivery_status,
            "items_count": len(o.items or []),
            "created_at": o.created_at.isoformat() if o.created_at else None,
            "currency": o.currency or "TZS",
        }
        for o in orders
    ]


@customer_ops_router.get("/orders/{order_id}")
def get_customer_order_detail(
    order_id: str,
    db: Session = Depends(get_db),
    customer: User = Depends(get_customer),
):
    from uuid import UUID

    try:
        order_uuid = UUID(order_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid order ID format")

    order = (
        db.query(SourcingOrder)
        .options(
            joinedload(SourcingOrder.batch),
            joinedload(SourcingOrder.items).joinedload(SourcingOrderItem.product),
        )
        .filter(
            SourcingOrder.id == order_uuid, SourcingOrder.customer_id == customer.id
        )
        .first()
    )

    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    receipt = (
        db.query(Receipt)
        .filter(Receipt.order_id == order.id)
        .order_by(Receipt.generated_at.desc())
        .first()
    )
    invoice_log = (
        db.query(AuditLog)
        .filter(
            AuditLog.entity_type == "sourcing_order",
            AuditLog.entity_id == order.id,
            AuditLog.action == "ORDER_INVOICE_GENERATED",
        )
        .order_by(AuditLog.created_at.desc())
        .first()
    )
    invoice_meta = (
        invoice_log.extra_data
        if invoice_log and isinstance(invoice_log.extra_data, dict)
        else {}
    )

    order_total_cbm = sum(float(item.total_cbm or 0) for item in (order.items or []))
    estimated_shipping_fee = 0.0
    shipping_fee_is_estimated = False
    shipping_method = order.batch.shipping_method if order.batch else "PER_CBM"
    shipping_fee_per_cbm = (
        float(order.batch.shipping_fee_per_cbm or 0)
        if order.batch and shipping_method == "PER_CBM"
        else 0.0
    )

    if shipping_method == "FREE_SHIPPING":
        estimated_shipping_fee = 0.0
    elif shipping_fee_per_cbm > 0 and order_total_cbm > 0:
        estimated_shipping_fee = shipping_fee_per_cbm * order_total_cbm
    elif order.batch_id and order_total_cbm > 0:
        # Fallback for legacy batches created before shipping_fee_per_cbm was required.
        batch_total_logistics_charge = (
            db.query(func.coalesce(func.sum(SeaBooking.logistics_charge), 0))
            .filter(
                SeaBooking.source_type == "batch",
                SeaBooking.source_id == order.batch_id,
            )
            .scalar()
            or 0
        )
        batch_total_cbm = (
            db.query(func.coalesce(func.sum(SourcingOrderItem.total_cbm), 0))
            .join(SourcingOrder, SourcingOrderItem.order_id == SourcingOrder.id)
            .filter(SourcingOrder.batch_id == order.batch_id)
            .scalar()
            or 0
        )

        batch_total_cbm = float(batch_total_cbm or 0)
        batch_total_logistics_charge = float(batch_total_logistics_charge or 0)

        if batch_total_cbm > 0 and batch_total_logistics_charge > 0:
            estimated_shipping_fee = batch_total_logistics_charge * (
                order_total_cbm / batch_total_cbm
            )
            shipping_fee_is_estimated = True

    total_amount_needed = (
        float(order.total_product_amount or 0) + estimated_shipping_fee
    )

    return {
        "id": str(order.id),
        "batch_id": str(order.batch_id) if order.batch_id else None,
        "batch_title": order.batch.title if order.batch else None,
        "batch_description": order.batch.description if order.batch else None,
        "total_product_amount": float(order.total_product_amount or 0),
        "currency": order.currency or "TZS",
        "shipping_method": shipping_method,
        "shipping_fee_per_cbm": round(shipping_fee_per_cbm, 2),
        "total_cbm": round(order_total_cbm, 4),
        "total_shipping_fee": round(estimated_shipping_fee, 2),
        "shipping_fee_is_estimated": shipping_fee_is_estimated,
        "total_amount_needed": round(total_amount_needed, 2),
        "delivery_status": order.delivery_status,
        "receipt_number": (receipt.receipt_number if receipt else order.receipt_number),
        "receipt_pdf_available": bool(receipt and receipt.pdf_url),
        "invoice_number": invoice_meta.get("invoice_number"),
        "invoice_pdf_available": bool(invoice_meta.get("pdf_url")),
        "collected_at": order.collected_at.isoformat() if order.collected_at else None,
        "created_at": order.created_at.isoformat() if order.created_at else None,
        # Explicitly excluding commission_amount and commission_status
        "items": [
            {
                "id": str(item.id),
                "product_id": str(item.product.id) if item.product else None,
                "product_name": (
                    item.product.name if item.product else "Unknown Product"
                ),
                "product_description": (
                    item.product.description if item.product else None
                ),
                "quantity": item.quantity,
                "unit_price": float(item.unit_price or 0),
                "total_price": float(item.total_price or 0),
                "currency": item.currency or order.currency or "TZS",
                "total_cbm": float(item.total_cbm or 0),
            }
            for item in order.items or []
        ],
    }


@customer_ops_router.get("/orders/{order_id}/receipt/pdf")
def stream_customer_order_receipt_pdf(
    order_id: str,
    db: Session = Depends(get_db),
    customer: User = Depends(get_customer),
):
    from uuid import UUID

    try:
        order_uuid = UUID(order_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid order ID format")

    order = (
        db.query(SourcingOrder)
        .filter(
            SourcingOrder.id == order_uuid, SourcingOrder.customer_id == customer.id
        )
        .first()
    )
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    receipt = (
        db.query(Receipt)
        .filter(Receipt.order_id == order.id)
        .order_by(Receipt.generated_at.desc())
        .first()
    )
    if not receipt or not receipt.pdf_url:
        raise HTTPException(status_code=404, detail="Receipt PDF not found")

    filename = f"{receipt.receipt_number or 'receipt'}.pdf"
    return _stream_cloudinary_document(receipt.pdf_url, filename=filename)


@customer_ops_router.get("/orders/{order_id}/invoice/pdf")
def stream_customer_order_invoice_pdf(
    order_id: str,
    db: Session = Depends(get_db),
    customer: User = Depends(get_customer),
):
    from uuid import UUID

    try:
        order_uuid = UUID(order_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid order ID format")

    order = (
        db.query(SourcingOrder)
        .filter(
            SourcingOrder.id == order_uuid, SourcingOrder.customer_id == customer.id
        )
        .first()
    )
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    invoice_log = (
        db.query(AuditLog)
        .filter(
            AuditLog.entity_type == "sourcing_order",
            AuditLog.entity_id == order.id,
            AuditLog.action == "ORDER_INVOICE_GENERATED",
        )
        .order_by(AuditLog.created_at.desc())
        .first()
    )
    invoice_meta = (
        invoice_log.extra_data
        if invoice_log and isinstance(invoice_log.extra_data, dict)
        else {}
    )
    pdf_url = invoice_meta.get("pdf_url")
    if not pdf_url:
        raise HTTPException(status_code=404, detail="Invoice PDF not found")

    filename = f"{invoice_meta.get('invoice_number') or 'invoice'}.pdf"
    return _stream_cloudinary_document(pdf_url, filename=filename)


@customer_ops_router.get("/sea-bookings/{sea_booking_id}/shipping-label")
def customer_get_sea_booking_label(
    sea_booking_id: str,
    db: Session = Depends(get_db),
    customer: User = Depends(get_customer),
):
    sea_booking = (
        db.query(SeaBooking)
        .options(
            joinedload(SeaBooking.container),
            joinedload(SeaBooking.shipping_mark),
        )
        .filter(
            SeaBooking.id == sea_booking_id,
            SeaBooking.user_id == customer.id,
        )
        .first()
    )
    if not sea_booking:
        raise HTTPException(status_code=404, detail="Container sea_booking not found")

    linked_order = (
        db.query(ShipmentOrder)
        .filter(
            ShipmentOrder.sea_booking_id == sea_booking.id,
            ShipmentOrder.created_by_user_id == customer.id,
            ShipmentOrder.tracking_number.isnot(None),
        )
        .order_by(ShipmentOrder.created_at.desc())
        .first()
    )

    mark = sea_booking.shipping_mark
    if not mark:
        # Create shipping mark if it doesn't exist
        mark = create_shipping_mark(
            db,
            booking_id=str(sea_booking.id),
            cargo_type="SEA",
            customer_name=customer.name,
            customer_phone=customer.phone_number,
            destination_region="Unknown",
            packing_list_summary="Container sea_booking",
            carton_count=1,
            sea_booking_id=sea_booking.id,
        )

    # Parse photos if any (though sea bookings don't currently have photo support)
    photos = []
    if hasattr(sea_booking, "photo_urls") and sea_booking.photo_urls:
        try:
            photos = json.loads(sea_booking.photo_urls)
        except (json.JSONDecodeError, TypeError):
            photos = []

    # Return data in the same structure as cargo admin endpoint
    return {
        "company": operator_document_branding(
            db, sea_booking.container.admin_id if sea_booking.container else None
        ),
        "sea_booking": {
            "sea_booking_id": str(sea_booking.id),
            "tracking_number": linked_order.tracking_number if linked_order else None,
            "cbm_booked": float(sea_booking.cbm_booked),
            "logistics_charge": float(sea_booking.logistics_charge or 0),
            "goods_status": sea_booking.goods_status,
            "payment_status": sea_booking.payment_status,
            "container": {
                "id": str(sea_booking.container.id) if sea_booking.container else None,
                "status": (
                    sea_booking.container.status if sea_booking.container else None
                ),
                "departure_date": (
                    sea_booking.container.departure_date
                    if sea_booking.container
                    else None
                ),
                "arrival_date": (
                    sea_booking.container.estimated_arrival_date
                    if sea_booking.container
                    else None
                ),
            },
            "customer": {
                "name": customer.name,
                "phone_number": customer.phone_number,
            },
        },
        "label": build_printable_label(mark),
        "item_photos": photos,
    }


@customer_ops_router.patch("/sea-bookings/{sea_booking_id}/shipping-label")
def customer_update_sea_booking_label(
    sea_booking_id: str,
    body: CustomerShippingLabelUpdateRequest,
    db: Session = Depends(get_db),
    customer: User = Depends(get_customer),
):
    sea_booking = (
        db.query(SeaBooking)
        .options(joinedload(SeaBooking.shipping_mark))
        .filter(
            SeaBooking.id == sea_booking_id,
            SeaBooking.user_id == customer.id,
        )
        .first()
    )
    if not sea_booking or not sea_booking.shipping_mark:
        raise HTTPException(status_code=404, detail="Shipping label not found")

    mark = sea_booking.shipping_mark
    if body.destination_region is not None:
        mark.destination_region = (
            body.destination_region.strip() or mark.destination_region
        )
    if body.carton_count is not None:
        if body.carton_count <= 0:
            raise HTTPException(
                status_code=400, detail="Carton count must be at least 1"
            )
        mark.carton_count = body.carton_count
    if body.packing_list_summary is not None:
        mark.packing_list_summary = body.packing_list_summary.strip() or None

    db.commit()
    db.refresh(mark)

    # Return consistent structure with GET endpoint
    return {"message": "Shipping label updated", "label": build_printable_label(mark)}


def _stream_cloudinary_document(document_url: str, filename: str) -> StreamingResponse:
    return stream_safe_document(document_url, filename)


api_router.include_router(customer_ops_router)


# Export the router with the expected name
router = api_router
