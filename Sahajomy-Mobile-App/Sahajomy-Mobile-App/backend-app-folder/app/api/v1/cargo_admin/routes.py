"""
Cargo Admin (Logistics Operator) API.
Can: create warehouses/containers, manage sea_bookings, hold/release/collect
goods, confirm lifecycle.
Cannot: change commission, modify sourcing batches, access other operators' data.
Security: all queries scoped to admin_id = current_user.id
"""

import csv
import hashlib
import io
import json
import re
from datetime import datetime, timedelta, timezone
from typing import List, Optional
from urllib.parse import urlparse
from uuid import UUID

import cloudinary.utils
import httpx
from app.api.v1.cargo_admin.customs import router as customs_router
from app.api.v1.cargo_admin.shipment_orders import router as shipment_orders_router
from app.core.audit import log_action
from app.core.cloudinary import configure_cloudinary
from app.core.config import settings
from app.core.dependencies import get_cargo_admin
from app.core.redis import redis_client  # You'll need to create this
from app.core.reference_ids import build_display_reference
from app.core.utils import generate_invoice_number
from app.database import get_db
from app.models.air_cargo import AirDepartureSchedule, ExpressAirCargoBooking
from app.models.container import Container, SeaBooking, SeaBookingGoods, Warehouse
from app.models.customer_china_address import CustomerChinaAddress
from app.models.finance import (
    ContainerConsolidatedPackingList,
    Notification,
    Payment,
    Receipt,
    SeaBookingInvoice,
    SeaBookingPackingList,
    SeaBookingPackingListItem,
)
from app.models.interaction import Interaction
from app.models.shipment_orders import ShipmentOrder, ShipmentOrderStatus
from app.models.shipping_mark import ShippingMark
from app.models.tracking import TrackingEvent
from app.models.user import User
from app.services.cargo_dashboard import (
    DEFAULT_CARGO_DASHBOARD_PERMISSIONS,
    build_cargo_dashboard,
)
from app.services.china_warehouse_address import (
    china_address_ready,
    is_china_warehouse,
    normalize_warehouse_china_address,
)
from app.services.document_branding import operator_document_branding
from app.services.document_download import stream_safe_document
from app.services.document_generation_service import DocumentGenerationService
from app.services.realtime_notifications import create_notification
from app.services.sea_booking_currency import snapshot_sea_booking_currency
from app.services.shipping_mark import (
    build_printable_label,
    create_shipping_mark,
    generate_shipping_mark_code,
)
from app.services.tracking import TrackingService  # NEW: Import tracking service
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, ConfigDict, Field, field_validator
from sqlalchemy import and_, func, or_
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, joinedload

router = APIRouter(prefix="/cargo_admin")

# Include sub-routers
router.include_router(shipment_orders_router, prefix="/shipment-orders")
router.include_router(customs_router)


def parse_photos(raw: Optional[str]) -> List[str]:
    if not raw:
        return []
    try:
        parsed = json.loads(raw)
        return parsed if isinstance(parsed, list) else []
    except Exception:
        return []


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


def warehouse_full_address(warehouse: Warehouse) -> str:
    return (
        f"{warehouse.address or warehouse.location}, "
        f"{warehouse.city or ''}, "
        f"{warehouse.state or ''}, "
        f"{warehouse.country or ''}"
    ).strip(", ")


_CHINA_CONFIG_FIELDS = {
    "name_zh",
    "china_receiver_name",
    "china_mobile",
    "china_province",
    "china_city",
    "china_district",
    "china_street",
    "china_detailed_address",
    "china_original_address",
    "china_address_status",
}


def _finalize_china_configuration(
    warehouse: Warehouse, submitted_fields: set[str]
) -> bool:
    """Normalize legacy records, but make admin-entered structured values authoritative."""
    if not is_china_warehouse(warehouse):
        return False
    if submitted_fields & _CHINA_CONFIG_FIELDS:
        if not warehouse.china_original_address:
            warehouse.china_original_address = warehouse.address or warehouse.location
        warehouse.china_address_source = "manual"
        warehouse.china_address_status = (
            "structured" if china_address_ready(warehouse) else "needs_review"
        )
        return True
    else:
        return normalize_warehouse_china_address(warehouse)


def _public_warehouse_payload(warehouse: Warehouse, **extra) -> dict:
    """Public discovery intentionally omits China receiver/copy-address data."""
    payload = WarehouseResponse.from_orm(warehouse).model_dump()
    for field in (
        "name_zh",
        "china_receiver_name",
        "china_mobile",
        "china_province",
        "china_city",
        "china_district",
        "china_street",
        "china_detailed_address",
        "china_original_address",
        "china_address_status",
        "china_address_source",
        "china_address_ready",
        "contact_name_1",
        "contact_phone_1",
        "contact_name_2",
        "contact_phone_2",
    ):
        payload.pop(field, None)
    payload.update(extra)
    return payload


# ─── Schemas ─────────────────────────────────────────────


class WarehouseCreate(BaseModel):
    name: str
    location: str = None  # Legacy field, keep for backward compatibility
    country: Optional[str] = None

    # Location fields
    country_code: Optional[str] = None
    state: Optional[str] = None
    state_code: Optional[str] = None
    city: Optional[str] = None
    address: Optional[str] = None
    postal_code: Optional[str] = None

    # Contact information
    contact_name_1: Optional[str] = None
    contact_phone_1: Optional[str] = None
    contact_name_2: Optional[str] = None
    contact_phone_2: Optional[str] = None

    # Operating hours
    operating_hours: Optional[str] = None
    weekend_hours: Optional[str] = None

    # Coordinates
    latitude: Optional[float] = None
    longitude: Optional[float] = None

    # Warehouse type: "sea", "air", or "both"
    warehouse_type: str = "both"

    # China forwarding-address fields. The legacy address remains untouched.
    name_zh: Optional[str] = None
    china_receiver_name: Optional[str] = None
    china_mobile: Optional[str] = None
    china_province: Optional[str] = None
    china_city: Optional[str] = None
    china_district: Optional[str] = None
    china_street: Optional[str] = None
    china_detailed_address: Optional[str] = None
    china_original_address: Optional[str] = None
    china_address_status: Optional[str] = None


class ShippingLabelUpdateRequest(BaseModel):
    customer_name: Optional[str] = None
    customer_phone: Optional[str] = None
    destination_region: Optional[str] = None
    carton_count: Optional[int] = None
    packing_list_summary: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None


class WarehouseResponse(BaseModel):
    id: str
    name: str
    location: str
    country: Optional[str] = None
    country_code: Optional[str] = None
    state: Optional[str] = None
    state_code: Optional[str] = None
    city: Optional[str] = None
    address: Optional[str] = None
    postal_code: Optional[str] = None
    contact_name_1: Optional[str] = None
    contact_phone_1: Optional[str] = None
    contact_name_2: Optional[str] = None
    contact_phone_2: Optional[str] = None
    operating_hours: Optional[str] = None
    weekend_hours: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    distance_km: Optional[float] = None
    created_at: Optional[str] = None
    warehouse_type: str = "both"
    name_zh: Optional[str] = None
    china_receiver_name: Optional[str] = None
    china_mobile: Optional[str] = None
    china_province: Optional[str] = None
    china_city: Optional[str] = None
    china_district: Optional[str] = None
    china_street: Optional[str] = None
    china_detailed_address: Optional[str] = None
    china_original_address: Optional[str] = None
    china_address_status: Optional[str] = None
    china_address_source: Optional[str] = None
    china_address_ready: bool = False

    # Use model_config instead of Config class for Pydantic v2
    model_config = ConfigDict(from_attributes=True, arbitrary_types_allowed=True)

    @field_validator("id", mode="before")
    @classmethod
    def validate_id(cls, v):
        """Convert UUID to string"""
        if isinstance(v, UUID):
            return str(v)
        return v

    @field_validator("created_at", mode="before")
    @classmethod
    def validate_created_at(cls, v):
        """Convert datetime to ISO format string"""
        if isinstance(v, datetime):
            return v.isoformat()
        return v

    @classmethod
    def from_orm(cls, obj):
        data = super().from_orm(obj)
        data.china_address_ready = china_address_ready(obj)
        return data


class ContainerCreate(BaseModel):
    route_id: Optional[str] = None
    warehouse_origin_id: str
    warehouse_destination_id: Optional[str] = None
    container_size: str  # 20ft | 40ft
    max_cbm: float

    price_per_cbm: float
    currency: str = "TZS"
    departure_date: Optional[datetime] = None
    estimated_arrival_date: Optional[datetime] = None
    status: Optional[str] = "draft"

    @field_validator("currency")
    @classmethod
    def validate_currency(cls, v):
        supported_currencies = {"TZS", "RMB", "USD"}
        if v.upper() not in supported_currencies:
            raise ValueError(f"Currency must be one of {supported_currencies}")
        return v.upper()


class ContainerStatusUpdate(BaseModel):
    status: str
    reason: Optional[str] = None


class ContainerScheduleUpdate(BaseModel):
    departure_date: Optional[datetime] = None
    estimated_arrival_date: Optional[datetime] = None


class ContainerArchiveRequest(BaseModel):
    archived: bool = True
    reason: Optional[str] = None


class HoldGoodsRequest(BaseModel):
    hold_reason: str


class ReleaseGoodsRequest(BaseModel):
    reason: Optional[str] = None


class MarkCollectedRequest(BaseModel):
    reason: Optional[str] = None


class SeaBookingStatusUpdateRequest(BaseModel):
    goods_status: str
    reason: Optional[str] = None


class AirCargoBookingStatusUpdate(BaseModel):
    status: str
    reason: Optional[str] = None


AIR_DEPARTURE_SCHEDULE_STATUSES = {
    "open",
    "filling_fast",
    "closed",
    "cancelled",
    "departed",
}
AIR_DEPARTURE_RECURRENCE_FREQUENCIES = {"weekly", "monthly", "yearly"}


class AirDepartureScheduleCreate(BaseModel):
    route_label: str = Field("China → Africa", min_length=2, max_length=120)
    service_label: str = Field("Express Air Cargo", min_length=2, max_length=150)
    departure_at: datetime
    booking_cutoff_at: Optional[datetime] = None
    recurrence_frequency: Optional[str] = None
    recurrence_weekdays: List[int] = Field(default_factory=list)
    recurrence_until: Optional[datetime] = None
    capacity_kg: Optional[float] = Field(None, gt=0)
    available_capacity_kg: Optional[float] = Field(None, ge=0)
    status: str = "open"
    notes: Optional[str] = Field(None, max_length=2000)

    @field_validator("route_label", "service_label")
    @classmethod
    def normalize_label(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("This field cannot be empty")
        return value

    @field_validator("status")
    @classmethod
    def validate_status(cls, value: str) -> str:
        normalized = value.strip().lower()
        if normalized not in AIR_DEPARTURE_SCHEDULE_STATUSES:
            raise ValueError("Invalid departure schedule status")
        return normalized

    @field_validator("recurrence_frequency")
    @classmethod
    def validate_recurrence_frequency(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return None
        normalized = value.strip().lower()
        if normalized not in AIR_DEPARTURE_RECURRENCE_FREQUENCIES:
            raise ValueError("Invalid recurrence frequency")
        return normalized

    @field_validator("recurrence_weekdays")
    @classmethod
    def validate_recurrence_weekdays(cls, value: List[int]) -> List[int]:
        normalized = sorted(set(value))
        if any(day < 0 or day > 6 for day in normalized):
            raise ValueError("Weekdays must use Monday (0) through Sunday (6)")
        return normalized


class AirDepartureScheduleUpdate(BaseModel):
    route_label: Optional[str] = Field(None, min_length=2, max_length=120)
    service_label: Optional[str] = Field(None, min_length=2, max_length=150)
    departure_at: Optional[datetime] = None
    booking_cutoff_at: Optional[datetime] = None
    recurrence_frequency: Optional[str] = None
    recurrence_weekdays: Optional[List[int]] = None
    recurrence_until: Optional[datetime] = None
    capacity_kg: Optional[float] = Field(None, gt=0)
    available_capacity_kg: Optional[float] = Field(None, ge=0)
    status: Optional[str] = None
    notes: Optional[str] = Field(None, max_length=2000)

    @field_validator("route_label", "service_label")
    @classmethod
    def normalize_optional_label(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return value
        value = value.strip()
        if not value:
            raise ValueError("This field cannot be empty")
        return value

    @field_validator("status")
    @classmethod
    def validate_optional_status(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return value
        normalized = value.strip().lower()
        if normalized not in AIR_DEPARTURE_SCHEDULE_STATUSES:
            raise ValueError("Invalid departure schedule status")
        return normalized

    @field_validator("recurrence_frequency")
    @classmethod
    def validate_optional_recurrence_frequency(
        cls, value: Optional[str]
    ) -> Optional[str]:
        if value is None:
            return None
        normalized = value.strip().lower()
        if normalized not in AIR_DEPARTURE_RECURRENCE_FREQUENCIES:
            raise ValueError("Invalid recurrence frequency")
        return normalized

    @field_validator("recurrence_weekdays")
    @classmethod
    def validate_optional_recurrence_weekdays(
        cls, value: Optional[List[int]]
    ) -> Optional[List[int]]:
        if value is None:
            return None
        normalized = sorted(set(value))
        if any(day < 0 or day > 6 for day in normalized):
            raise ValueError("Weekdays must use Monday (0) through Sunday (6)")
        return normalized


class SeaBookingInvoiceCreateRequest(BaseModel):
    notes: Optional[str] = None
    due_date: Optional[datetime] = None
    format: str = "both"
    send_to_customer: bool = True


class SeaBookingInvoiceStatusUpdateRequest(BaseModel):
    status: str
    note: Optional[str] = None


class SeaBookingPackingListCreateRequest(BaseModel):
    notes: Optional[str] = None
    shipment_stage: str = "booking_received"


class SeaBookingPackingListItemCreateRequest(BaseModel):
    item_name: str
    supplier_details: Optional[str] = None
    cartons: int = 0
    cbm: float = 0
    weight_kg: float = 0
    status: str = "pending"
    notes: Optional[str] = None


class SeaBookingPackingListItemUpdateRequest(BaseModel):
    item_name: Optional[str] = None
    supplier_details: Optional[str] = None
    cartons: Optional[int] = None
    cbm: Optional[float] = None
    weight_kg: Optional[float] = None
    status: Optional[str] = None
    notes: Optional[str] = None


class SeaBookingPackingStageUpdateRequest(BaseModel):
    shipment_stage: str
    status: Optional[str] = None
    notes: Optional[str] = None


INVOICE_STATUSES = {"draft", "sent", "paid", "cancelled"}
RECEIPT_STATUSES = {"issued", "voided"}
PACKING_LIST_STATUSES = {"draft", "in_progress", "finalized"}
PACKING_ITEM_STATUSES = {
    "pending",
    "received",
    "inspected",
    "packed",
    "loaded",
    "completed",
}
PACKING_WORKFLOW_STAGES = {
    "booking_received",
    "products_pending",
    "products_received_at_warehouse",
    "products_inspected",
    "packing_list_created",
    "products_packed",
    "products_loaded_into_container",
    "container_partially_full",
    "container_full",
    "ready_for_shipment",
    "shipped",
}


# ─── Geocoding Helper ────────────────────────────────────


async def geocode_address_cached(address: str, city: str, country: str):
    """Convert address to coordinates with Redis caching"""
    try:
        # Create cache key
        address_str = f"{address}, {city}, {country}".strip(", ")
        cache_key = f"geocode:{hashlib.md5(address_str.encode()).hexdigest()}"

        # Check Redis cache
        if redis_client:
            cached = await redis_client.get(cache_key)
            if cached:
                return json.loads(cached)

        # Call Nominatim
        async with httpx.AsyncClient() as client:
            response = await client.get(
                "https://nominatim.openstreetmap.org/search",
                params={"q": address_str, "format": "json", "limit": 1},
                headers={"User-Agent": "SahajomyApp/1.0"},
            )

            if response.status_code == 200:
                data = response.json()
                if data:
                    result = {
                        "lat": float(data[0]["lat"]),
                        "lon": float(data[0]["lon"]),
                    }
                    # Cache for 30 days
                    if redis_client:
                        await redis_client.setex(cache_key, 2592000, json.dumps(result))
                    return result
    except Exception as e:
        print(f"Geocoding failed: {str(e)}")

    return None


def calculate_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Calculate distance between two points using Haversine formula"""
    from math import atan2, cos, radians, sin, sqrt

    R = 6371  # Earth's radius in kilometers

    lat1, lon1, lat2, lon2 = map(radians, [lat1, lon1, lat2, lon2])

    dlat = lat2 - lat1
    dlon = lon2 - lon1

    a = sin(dlat / 2) ** 2 + cos(lat1) * cos(lat2) * sin(dlon / 2) ** 2
    c = 2 * atan2(sqrt(a), sqrt(1 - a))

    return R * c


# ─── Warehouse Management ────────────────────────────────


@router.get("/warehouses", response_model=List[WarehouseResponse])
def list_my_warehouses(
    db: Session = Depends(get_db),
    admin: User = Depends(get_cargo_admin),
):
    """List warehouses owned by this cargo admin"""
    warehouses = db.query(Warehouse).filter(Warehouse.admin_id == admin.id).all()
    changed = False
    for warehouse in warehouses:
        changed = _finalize_china_configuration(warehouse, set()) or changed
    if changed:
        db.commit()

    return [WarehouseResponse.from_orm(w) for w in warehouses]


@router.post("/warehouses", response_model=WarehouseResponse)
async def create_warehouse(
    body: WarehouseCreate,
    db: Session = Depends(get_db),
    admin: User = Depends(get_cargo_admin),
):
    """Create a new warehouse with full address and auto-geocoding"""

    # Auto-geocode if coordinates not provided
    latitude = body.latitude
    longitude = body.longitude

    if not latitude or not longitude:
        if body.address and body.city and body.country:
            coords = await geocode_address_cached(body.address, body.city, body.country)
            if coords:
                latitude = coords["lat"]
                longitude = coords["lon"]

    # Combine location field for backward compatibility
    location_parts = []
    if body.address:
        location_parts.append(body.address)
    if body.city:
        location_parts.append(body.city)
    if body.state:
        location_parts.append(body.state)
    if body.country:
        location_parts.append(body.country)

    location = ", ".join(location_parts) if location_parts else (body.location or "")

    warehouse = Warehouse(
        admin_id=admin.id,
        name=body.name,
        location=location,
        country=body.country,
        country_code=body.country_code,
        state=body.state,
        state_code=body.state_code,
        city=body.city,
        address=body.address,
        postal_code=body.postal_code,
        contact_name_1=body.contact_name_1,
        contact_phone_1=body.contact_phone_1,
        contact_name_2=body.contact_name_2,
        contact_phone_2=body.contact_phone_2,
        operating_hours=body.operating_hours,
        weekend_hours=body.weekend_hours,
        latitude=latitude,
        longitude=longitude,
        warehouse_type=body.warehouse_type,
        name_zh=body.name_zh,
        china_receiver_name=body.china_receiver_name,
        china_mobile=body.china_mobile,
        china_province=body.china_province,
        china_city=body.china_city,
        china_district=body.china_district,
        china_street=body.china_street,
        china_detailed_address=body.china_detailed_address,
        china_original_address=body.china_original_address,
        china_address_status=body.china_address_status,
    )
    _finalize_china_configuration(warehouse, set(body.model_fields_set))

    db.add(warehouse)
    db.commit()
    db.refresh(warehouse)

    return WarehouseResponse.from_orm(warehouse)


@router.post("/warehouses/backfill-china-addresses")
def backfill_my_china_warehouse_addresses(
    db: Session = Depends(get_db), admin: User = Depends(get_cargo_admin)
):
    """Safe, idempotent per-operator backfill; confirmed values are preserved."""
    warehouses = db.query(Warehouse).filter(Warehouse.admin_id == admin.id).all()
    report = {
        "checked": len(warehouses),
        "already_structured": 0,
        "auto_structured": 0,
        "needs_review": [],
    }
    for warehouse in warehouses:
        was_status = warehouse.china_address_status
        changed = _finalize_china_configuration(warehouse, set())
        if (
            warehouse.china_address_status in {"structured", "confirmed"}
            and not changed
        ):
            report["already_structured"] += 1
        elif warehouse.china_address_status == "auto_structured":
            report["auto_structured"] += 1
        elif is_china_warehouse(warehouse) and not china_address_ready(warehouse):
            report["needs_review"].append(
                {
                    "id": str(warehouse.id),
                    "name": warehouse.name,
                    "status": warehouse.china_address_status
                    or was_status
                    or "needs_review",
                }
            )
    db.commit()
    return report


@router.patch("/warehouses/{warehouse_id}", response_model=WarehouseResponse)
async def update_warehouse(
    warehouse_id: str,
    body: WarehouseCreate,
    db: Session = Depends(get_db),
    admin: User = Depends(get_cargo_admin),
):
    """Update warehouse details"""
    warehouse = (
        db.query(Warehouse)
        .filter(Warehouse.id == warehouse_id, Warehouse.admin_id == admin.id)
        .first()
    )

    if not warehouse:
        raise HTTPException(status_code=404, detail="Warehouse not found")

    # Update fields
    for field, value in body.model_dump(exclude_unset=True).items():
        if value is not None:
            setattr(warehouse, field, value)

    _finalize_china_configuration(warehouse, set(body.model_fields_set))
    log_action(
        db=db,
        action="WAREHOUSE_CHINA_ADDRESS_CONFIGURED",
        user_id=admin.id,
        entity_type="warehouse",
        entity_id=warehouse.id,
        metadata={"ready": china_address_ready(warehouse)},
    )

    db.commit()
    db.refresh(warehouse)

    return WarehouseResponse.from_orm(warehouse)


@router.delete("/warehouses/{warehouse_id}")
def delete_warehouse(
    warehouse_id: str,
    db: Session = Depends(get_db),
    admin: User = Depends(get_cargo_admin),
):
    """Delete a warehouse"""
    warehouse = (
        db.query(Warehouse)
        .filter(Warehouse.id == warehouse_id, Warehouse.admin_id == admin.id)
        .first()
    )

    if not warehouse:
        raise HTTPException(status_code=404, detail="Warehouse not found")

    db.delete(warehouse)
    db.commit()

    return {"message": "Warehouse deleted successfully"}


@router.get("/china-addresses/search")
def search_customer_china_addresses(
    q: str = Query(..., min_length=2, max_length=120),
    db: Session = Depends(get_db),
    admin: User = Depends(get_cargo_admin),
):
    """Operator-scoped intake lookup by mark, customer, or forwarding phone."""
    term = f"%{q.strip()}%"
    rows = (
        db.query(CustomerChinaAddress)
        .options(
            joinedload(CustomerChinaAddress.customer),
            joinedload(CustomerChinaAddress.warehouse),
        )
        .join(User, CustomerChinaAddress.customer_id == User.id)
        .filter(
            CustomerChinaAddress.cargo_admin_id == admin.id,
            or_(
                CustomerChinaAddress.shipping_mark.ilike(term),
                User.name.ilike(term),
                User.phone_number.ilike(term),
            ),
        )
        .order_by(CustomerChinaAddress.created_at.desc())
        .limit(50)
        .all()
    )
    return [
        {
            "id": str(row.id),
            "shipping_mark": row.shipping_mark,
            "customer": {
                "name": row.customer.name if row.customer else None,
                "phone": row.customer.secure_phone if row.customer else None,
            },
            "destination": {
                "country": row.destination_country,
                "city": row.destination_city,
            },
            "cargo_mode": row.cargo_mode,
            "warehouse": {
                "id": str(row.warehouse_id),
                "name": row.warehouse.name if row.warehouse else None,
            },
        }
        for row in rows
    ]


# ─── Customer-facing Warehouse Search ───────────────────


@router.get("/public/warehouses/nearby")
def find_nearby_warehouses(
    lat: float = Query(..., description="Customer latitude"),
    lng: float = Query(..., description="Customer longitude"),
    radius_km: float = Query(50.0, description="Search radius in kilometers"),
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
):
    """
    Find warehouses near a customer's location
    Returns warehouses sorted by distance
    """
    # Get all warehouses with coordinates
    warehouses = (
        db.query(Warehouse)
        .filter(Warehouse.latitude.isnot(None), Warehouse.longitude.isnot(None))
        .all()
    )

    # Calculate distances and filter by radius
    nearby = []
    for w in warehouses:
        distance = calculate_distance(lat, lng, float(w.latitude), float(w.longitude))

        if distance <= radius_km:
            warehouse_dict = _public_warehouse_payload(
                w, distance_km=round(distance, 2)
            )
            nearby.append(warehouse_dict)

    # Sort by distance and return
    nearby.sort(key=lambda x: x["distance_km"])
    return nearby[:limit]


@router.get("/public/warehouses/search")
def search_warehouses(
    q: str = Query(..., description="Search query (city, country, or name)"),
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
):
    """
    Search warehouses by name, city, or country
    """
    search_term = f"%{q}%"

    warehouses = (
        db.query(Warehouse)
        .filter(
            or_(
                Warehouse.name.ilike(search_term),
                Warehouse.city.ilike(search_term),
                Warehouse.country.ilike(search_term),
                Warehouse.state.ilike(search_term),
                Warehouse.address.ilike(search_term),
            )
        )
        .limit(limit)
        .all()
    )

    return [_public_warehouse_payload(w) for w in warehouses]


# ─── Container Management ────────────────────────────────


@router.get("/containers")
def list_my_containers(
    status: Optional[str] = None,
    warehouse_id: Optional[str] = None,
    include_archived: bool = Query(False),
    db: Session = Depends(get_db),
    admin: User = Depends(get_cargo_admin),
):
    """List containers owned by this cargo admin only."""
    q = (
        db.query(Container)
        .options(
            joinedload(Container.origin_warehouse),
            joinedload(Container.destination_warehouse),
        )
        .filter(Container.admin_id == admin.id)
    )

    if not include_archived:
        q = q.filter(Container.is_archived.is_(False))

    if status:
        q = q.filter(Container.status == status)

    if warehouse_id:
        q = q.filter(
            or_(
                Container.warehouse_origin_id == warehouse_id,
                Container.warehouse_destination_id == warehouse_id,
            )
        )

    containers = q.order_by(Container.created_at.desc()).all()
    container_ids = [str(container.id) for container in containers]

    booked_cbm_rows = (
        db.query(
            SeaBooking.container_id,
            func.coalesce(func.sum(SeaBooking.cbm_booked), 0).label("booked_cbm"),
        )
        .filter(SeaBooking.container_id.in_(container_ids))
        .group_by(SeaBooking.container_id)
        .all()
        if container_ids
        else []
    )
    booked_cbm_map = {
        str(container_id): float(booked_cbm or 0)
        for container_id, booked_cbm in booked_cbm_rows
    }

    return [
        {
            "id": str(c.id),
            "container_size": c.container_size,
            "max_cbm": float(c.max_cbm),
            "booked_cbm": booked_cbm_map.get(str(c.id), float(c.booked_cbm or 0)),
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
                2,
            ),
            "price_per_cbm": float(c.price_per_cbm),
            "status": c.status,
            "reference": build_display_reference("container", c.id, c.created_at),
            "is_archived": bool(c.is_archived),
            "archived_at": c.archived_at.isoformat() if c.archived_at else None,
            "departure_date": (
                c.departure_date.isoformat() if c.departure_date else None
            ),
            "estimated_arrival_date": (
                c.estimated_arrival_date.isoformat()
                if c.estimated_arrival_date
                else None
            ),
            "arrival_date": c.arrival_date.isoformat() if c.arrival_date else None,
            "warehouse_origin_id": (
                str(c.warehouse_origin_id) if c.warehouse_origin_id else None
            ),
            "warehouse_destination_id": (
                str(c.warehouse_destination_id) if c.warehouse_destination_id else None
            ),
            "warehouse_origin_name": (
                c.origin_warehouse.name if c.origin_warehouse else None
            ),
            "warehouse_destination_name": (
                c.destination_warehouse.name if c.destination_warehouse else None
            ),
        }
        for c in containers
    ]


@router.post("/containers")
def create_container(
    body: ContainerCreate,
    db: Session = Depends(get_db),
    admin: User = Depends(get_cargo_admin),
):
    origin = (
        db.query(Warehouse)
        .filter(
            Warehouse.id == body.warehouse_origin_id,
            Warehouse.admin_id == admin.id,
        )
        .first()
    )
    if not origin:
        raise HTTPException(
            status_code=400, detail="Valid origin warehouse is required"
        )

    if body.warehouse_destination_id:
        destination = (
            db.query(Warehouse)
            .filter(
                Warehouse.id == body.warehouse_destination_id,
                Warehouse.admin_id == admin.id,
            )
            .first()
        )
        if not destination:
            raise HTTPException(status_code=400, detail="Invalid destination warehouse")

    if body.status not in {"draft", "open"}:
        raise HTTPException(status_code=400, detail="Invalid container status")

    container = Container(
        admin_id=admin.id,
        route_id=body.route_id,
        warehouse_origin_id=origin.id,
        warehouse_destination_id=body.warehouse_destination_id,
        container_size=body.container_size,
        max_cbm=body.max_cbm,
        booked_cbm=0,
        price_per_cbm=body.price_per_cbm,
        currency=body.currency,
        departure_date=body.departure_date,
        estimated_arrival_date=body.estimated_arrival_date,
        status=body.status or "draft",
    )
    db.add(container)
    db.flush()  # Generate the container ID before creating tracking event
    TrackingService.create_tracking_event(
        db=db,
        entity_type="container",
        entity_id=str(container.id),
        event_type="container_created",
        description="Container created by cargo admin",
        triggered_by=str(admin.id),
        extra_data={"status": container.status},
    )
    db.commit()
    db.refresh(container)
    return {
        "id": str(container.id),
        "status": container.status,
        "max_cbm": float(container.max_cbm),
    }


@router.patch("/containers/{container_id}/status")
def update_container_status(
    container_id: str,
    body: ContainerStatusUpdate,
    db: Session = Depends(get_db),
    admin: User = Depends(get_cargo_admin),
):
    container = (
        db.query(Container)
        .filter(
            Container.id == container_id,
            Container.admin_id == admin.id,
        )
        .first()
    )

    if not container:
        raise HTTPException(status_code=404, detail="Container not found")

    valid_transitions = {
        "draft": ["open"],
        "open": ["in_transit"],
        "nearly_full": ["in_transit"],
        "full": ["in_transit"],
        "in_transit": ["arrived"],
        "arrived": ["completed"],
    }

    if body.status not in valid_transitions.get(container.status, []):
        raise HTTPException(
            status_code=400,
            detail=f"Invalid transition: {container.status} → {body.status}",
        )

    old_status = container.status
    container.status = body.status
    transition_payload = {
        "old_status": old_status,
        "new_status": body.status,
        "reason": body.reason,
    }
    TrackingService.create_tracking_event(
        db=db,
        entity_type="container",
        entity_id=str(container.id),
        event_type="container_status_updated",
        description=f"Container status changed from {old_status} to {body.status}",
        triggered_by=str(admin.id),
        extra_data=transition_payload,
    )

    if body.status == "arrived":
        container.arrival_date = datetime.utcnow()
        db.query(SeaBooking).filter(SeaBooking.container_id == container.id).update(
            {"payment_status": "due"}
        )

    log_action(
        db=db,
        action=f"CONTAINER_STATUS_{old_status.upper()}_TO_{body.status.upper()}",
        user_id=admin.id,
        entity_type="container",
        entity_id=container.id,
        reason=body.reason,
    )

    db.commit()
    return {"message": f"Container status updated to {body.status}"}


@router.patch("/containers/{container_id}/schedule")
def update_container_schedule(
    container_id: str,
    body: ContainerScheduleUpdate,
    db: Session = Depends(get_db),
    admin: User = Depends(get_cargo_admin),
):
    container = _get_container_for_admin(db, container_id, admin.id)

    if body.departure_date is None and body.estimated_arrival_date is None:
        raise HTTPException(
            status_code=400,
            detail="Provide departure_date and/or estimated_arrival_date.",
        )

    next_departure_date = (
        body.departure_date
        if body.departure_date is not None
        else container.departure_date
    )
    next_estimated_arrival_date = (
        body.estimated_arrival_date
        if body.estimated_arrival_date is not None
        else container.estimated_arrival_date
    )

    if (
        next_departure_date
        and next_estimated_arrival_date
        and next_estimated_arrival_date < next_departure_date
    ):
        raise HTTPException(
            status_code=400,
            detail="Estimated arrival date must be later than departure date.",
        )

    old_departure_date = container.departure_date
    old_estimated_arrival_date = container.estimated_arrival_date
    container.departure_date = next_departure_date
    container.estimated_arrival_date = next_estimated_arrival_date

    TrackingService.create_tracking_event(
        db=db,
        entity_type="container",
        entity_id=str(container.id),
        event_type="container_schedule_updated",
        description="Container departure/arrival estimate updated",
        triggered_by=str(admin.id),
        extra_data={
            "old_departure_date": (
                old_departure_date.isoformat() if old_departure_date else None
            ),
            "new_departure_date": (
                next_departure_date.isoformat() if next_departure_date else None
            ),
            "old_estimated_arrival_date": (
                old_estimated_arrival_date.isoformat()
                if old_estimated_arrival_date
                else None
            ),
            "new_estimated_arrival_date": (
                next_estimated_arrival_date.isoformat()
                if next_estimated_arrival_date
                else None
            ),
        },
    )

    sea_bookings = (
        db.query(SeaBooking).filter(SeaBooking.container_id == container.id).all()
    )
    actor = admin.name or "Cargo Admin"
    actor_role = _actor_label(admin)
    departure_label = (
        next_departure_date.strftime("%Y-%m-%d %H:%M") if next_departure_date else "TBD"
    )
    eta_label = (
        next_estimated_arrival_date.strftime("%Y-%m-%d %H:%M")
        if next_estimated_arrival_date
        else "TBD"
    )

    for sea_booking in sea_bookings:
        TrackingService.create_tracking_event(
            db=db,
            entity_type="sea_booking",
            entity_id=str(sea_booking.id),
            event_type="container_schedule_updated",
            description="Container schedule was updated by cargo admin",
            triggered_by=str(admin.id),
            extra_data={
                "container_id": str(container.id),
                "departure_date": (
                    next_departure_date.isoformat() if next_departure_date else None
                ),
                "estimated_arrival_date": (
                    next_estimated_arrival_date.isoformat()
                    if next_estimated_arrival_date
                    else None
                ),
            },
        )
        _notify_sea_booking_user(
            db=db,
            sea_booking=sea_booking,
            notification_type="container_schedule_updated",
            message=(
                f"{actor} ({actor_role}) updated your container schedule. "
                f"Departure: {departure_label}. Estimated arrival: {eta_label}."
            ),
            target_type="container",
            target_id=container.id,
        )

    log_action(
        db=db,
        action="CONTAINER_SCHEDULE_UPDATED",
        user_id=admin.id,
        entity_type="container",
        entity_id=container.id,
    )

    db.commit()
    db.refresh(container)
    return {
        "message": "Container schedule updated",
        "container": _container_detail(container),
        "notified_sea_bookings": len(sea_bookings),
    }


@router.patch("/containers/{container_id}/archive")
def archive_container(
    container_id: str,
    body: ContainerArchiveRequest,
    db: Session = Depends(get_db),
    admin: User = Depends(get_cargo_admin),
):
    container = _get_container_for_admin(db, container_id, admin.id)

    if body.archived:
        if container.is_archived:
            return {
                "message": "Container already archived",
                "container": _container_detail(container),
            }
        if container.status in {"in_transit"}:
            raise HTTPException(
                status_code=400,
                detail="Cannot archive a container that is currently in transit.",
            )
        if container.status not in {"arrived", "completed"}:
            raise HTTPException(
                status_code=400,
                detail=(
                    "Only arrived or completed containers can be archived. "
                    "Finish active logistics operations first."
                ),
            )
        if not (body.reason or "").strip():
            raise HTTPException(
                status_code=400,
                detail="Archive reason is required for audit compliance.",
            )

        active_sea_bookings = (
            db.query(SeaBooking)
            .filter(SeaBooking.container_id == container.id)
            .filter(
                or_(
                    SeaBooking.goods_status != "collected",
                    SeaBooking.payment_status != "confirmed",
                )
            )
            .count()
        )
        if active_sea_bookings > 0:
            raise HTTPException(
                status_code=400,
                detail=(
                    "Container has active sea bookings (uncollected goods or "
                    "unsettled payments). Resolve them before archiving."
                ),
            )

        active_packing_lists = (
            db.query(SeaBookingPackingList)
            .filter(SeaBookingPackingList.container_id == container.id)
            .filter(SeaBookingPackingList.status.in_(["draft", "in_progress"]))
            .count()
        )
        if active_packing_lists > 0:
            raise HTTPException(
                status_code=400,
                detail=(
                    "Container has packing lists still in progress. Finalize "
                    "packing workflows before archiving."
                ),
            )

        old_status = container.status
        container.is_archived = True
        container.archived_at = datetime.utcnow()
        container.archived_by = admin.id
        action = "CONTAINER_ARCHIVED"
        event_type = "container_archived"
        description = "Container archived by cargo admin"
        message = "Container archived"
    else:
        if not container.is_archived:
            return {
                "message": "Container is already active",
                "container": _container_detail(container),
            }
        old_status = container.status
        container.is_archived = False
        container.archived_at = None
        container.archived_by = None
        action = "CONTAINER_UNARCHIVED"
        event_type = "container_unarchived"
        description = "Container restored by cargo admin"
        message = "Container restored"

    TrackingService.create_tracking_event(
        db=db,
        entity_type="container",
        entity_id=str(container.id),
        event_type=event_type,
        description=description,
        triggered_by=str(admin.id),
        extra_data={
            "reason": body.reason,
            "archived": bool(body.archived),
            "old_status": old_status,
            "new_status": container.status,
        },
    )
    log_action(
        db=db,
        action=action,
        user_id=admin.id,
        entity_type="container",
        entity_id=container.id,
        reason=body.reason,
    )

    db.commit()
    db.refresh(container)
    return {"message": message, "container": _container_detail(container)}


@router.get("/containers/{container_id}/sea-bookings")
def list_sea_bookings(
    container_id: str,
    db: Session = Depends(get_db),
    admin: User = Depends(get_cargo_admin),
):
    container = (
        db.query(Container)
        .filter(Container.id == container_id, Container.admin_id == admin.id)
        .first()
    )

    if not container:
        raise HTTPException(status_code=404, detail="Container not found")

    sea_bookings = (
        db.query(SeaBooking)
        .options(
            joinedload(SeaBooking.shipping_mark),
            joinedload(SeaBooking.goods_types).joinedload(SeaBookingGoods.goods_type),
        )
        .filter(SeaBooking.container_id == container_id)
        .all()
    )

    response = []
    for r in sea_bookings:
        shipping_mark = r.shipping_mark
        response.append(
            {
                "id": str(r.id),
                "user_id": str(r.user_id) if r.user_id else None,
                "cbm_booked": float(r.cbm_booked),
                "logistics_charge": float(r.logistics_charge),
                "currency": r.currency or container.currency,
                "payment_status": r.payment_status,
                "goods_status": r.goods_status,
                "payment_due_date": r.payment_due_date,
                "hold_reason": r.hold_reason,
                "collected_at": r.collected_at,
                "shipping_mark": (
                    shipping_mark.shipping_mark_code if shipping_mark else None
                ),
                "goods_types": [
                    {
                        "id": str(rg.goods_type.id),
                        "name": rg.goods_type.name,
                        "is_hazardous": rg.goods_type.is_hazardous,
                    }
                    for rg in r.goods_types
                    if rg.goods_type
                ],
            }
        )

    return response


# ─── Goods Control ───────────────────────────────────────


@router.post("/sea-bookings/{sea_booking_id}/hold")
def hold_goods(
    sea_booking_id: str,
    body: HoldGoodsRequest,
    db: Session = Depends(get_db),
    admin: User = Depends(get_cargo_admin),
):
    sea_booking = _get_sea_booking_for_admin(db, sea_booking_id, admin.id)

    if sea_booking.payment_status == "confirmed":
        raise HTTPException(
            status_code=400, detail="Cannot hold goods - payment already confirmed"
        )

    sea_booking.goods_status = "held"
    sea_booking.hold_reason = body.hold_reason
    sea_booking.hold_marked_at = datetime.utcnow()
    sea_booking.hold_marked_by = admin.id

    TrackingService.create_tracking_event(
        db=db,
        entity_type="sea_booking",
        entity_id=str(sea_booking.id),
        event_type="goods_held",
        description="Goods placed on hold by cargo admin",
        triggered_by=str(admin.id),
        extra_data={"hold_reason": body.hold_reason},
    )

    log_action(
        db=db,
        action="GOODS_HELD",
        user_id=admin.id,
        entity_type="sea_booking",
        entity_id=sea_booking.id,
        metadata={
            "hold_reason": body.hold_reason,
            "payment_status": sea_booking.payment_status,
        },
        reason=body.hold_reason,
    )

    db.commit()
    return {"message": "Goods marked as held", "hold_reason": body.hold_reason}


@router.post("/sea-bookings/{sea_booking_id}/release")
def release_goods(
    sea_booking_id: str,
    body: ReleaseGoodsRequest,
    db: Session = Depends(get_db),
    admin: User = Depends(get_cargo_admin),
):
    sea_booking = _get_sea_booking_for_admin(db, sea_booking_id, admin.id)

    if sea_booking.payment_status != "confirmed":
        raise HTTPException(
            status_code=400, detail="Cannot release goods - payment not confirmed"
        )

    sea_booking.goods_status = "released"
    sea_booking.hold_reason = None

    TrackingService.create_tracking_event(
        db=db,
        entity_type="sea_booking",
        entity_id=str(sea_booking.id),
        event_type="goods_released",
        description="Goods released by cargo admin",
        triggered_by=str(admin.id),
        extra_data={"reason": body.reason},
    )

    log_action(
        db=db,
        action="GOODS_RELEASED",
        user_id=admin.id,
        entity_type="sea_booking",
        entity_id=sea_booking.id,
        reason=body.reason,
    )

    db.commit()
    return {"message": "Goods released"}


# ─── All SeaBookings Listing ───────────────────────────


@router.get("/sea-bookings")
def list_all_sea_bookings(
    container_id: Optional[str] = None,
    status: Optional[str] = None,
    payment_status: Optional[str] = None,
    search: Optional[str] = None,
    from_date: Optional[str] = None,
    to_date: Optional[str] = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=500),
    db: Session = Depends(get_db),
    admin: User = Depends(get_cargo_admin),
):
    query = (
        db.query(SeaBooking, Container, User)
        .join(Container, SeaBooking.container_id == Container.id)
        .join(User, SeaBooking.user_id == User.id, isouter=True)
        .filter(Container.admin_id == admin.id)
    )

    if container_id:
        query = query.filter(Container.id == container_id)
    if status:
        query = query.filter(SeaBooking.goods_status == status)
    if payment_status:
        query = query.filter(SeaBooking.payment_status == payment_status)
    if search:
        query = query.filter(
            or_(
                SeaBooking.id.ilike(f"%{search}%"),
                User.name.ilike(f"%{search}%"),
                User.phone_number.ilike(f"%{search}%"),
            )
        )
    if from_date:
        from_datetime = datetime.fromisoformat(from_date.replace("Z", "+00:00"))
        query = query.filter(SeaBooking.created_at >= from_datetime)
    if to_date:
        to_datetime = datetime.fromisoformat(to_date.replace("Z", "+00:00"))
        query = query.filter(SeaBooking.created_at <= to_datetime)

    query = query.order_by(SeaBooking.created_at.desc())

    total = query.count()
    results = query.offset(skip).limit(limit).all()

    sea_booking_ids = [sea_booking.id for sea_booking, _, _ in results]

    shipping_mark_map = {}
    if sea_booking_ids:
        shipping_marks = (
            db.query(ShippingMark)
            .filter(ShippingMark.sea_booking_id.in_(sea_booking_ids))
            .all()
        )
        shipping_mark_map = {
            mark.sea_booking_id: mark for mark in shipping_marks if mark.sea_booking_id
        }

    tracking_number_map = {}
    if sea_booking_ids:
        linked_orders = (
            db.query(ShipmentOrder)
            .filter(
                ShipmentOrder.sea_booking_id.in_(sea_booking_ids),
                ShipmentOrder.tracking_number.isnot(None),
            )
            .order_by(ShipmentOrder.created_at.desc())
            .all()
        )
        for order in linked_orders:
            sea_booking_id = order.sea_booking_id
            if sea_booking_id not in tracking_number_map and order.tracking_number:
                tracking_number_map[sea_booking_id] = order.tracking_number

    latest_event_map = {}
    if sea_booking_ids:
        sea_booking_events = (
            db.query(TrackingEvent)
            .filter(
                TrackingEvent.entity_type == "sea_booking",
                TrackingEvent.entity_id.in_(sea_booking_ids),
            )
            .order_by(TrackingEvent.timestamp.desc())
            .all()
        )
        for event in sea_booking_events:
            if event.entity_id not in latest_event_map:
                latest_event_map[event.entity_id] = event

    sea_bookings = []
    for sea_booking, container, user in results:
        goods_types = (
            db.query(SeaBookingGoods)
            .filter(SeaBookingGoods.sea_booking_id == sea_booking.id)
            .all()
        )

        shipping_mark = shipping_mark_map.get(sea_booking.id)
        latest_event = latest_event_map.get(sea_booking.id)
        destination = None
        if shipping_mark and shipping_mark.destination_region:
            destination = shipping_mark.destination_region
        elif container and container.route and container.route.destination:
            destination = container.route.destination
        elif container and container.destination_warehouse:
            destination = (
                container.destination_warehouse.city
                or container.destination_warehouse.location
            )

        sea_bookings.append(
            {
                "id": str(sea_booking.id),
                "container_id": str(container.id),
                "container_name": f"{container.container_size} - {container.status}",
                "container_size": container.container_size,
                "user_id": str(user.id) if user else None,
                "user_name": user.name if user else "Guest",
                "user_phone": user.phone_number if user else None,
                "source_type": sea_booking.source_type,
                "source_id": (
                    str(sea_booking.source_id) if sea_booking.source_id else None
                ),
                "cbm_booked": float(sea_booking.cbm_booked),
                "logistics_charge": float(sea_booking.logistics_charge),
                "currency": sea_booking.currency
                or (container.currency if container else None),
                "payment_status": sea_booking.payment_status,
                "goods_status": sea_booking.goods_status,
                "hold_reason": sea_booking.hold_reason,
                "hold_marked_at": (
                    sea_booking.hold_marked_at.isoformat()
                    if sea_booking.hold_marked_at
                    else None
                ),
                "collected_at": (
                    sea_booking.collected_at.isoformat()
                    if sea_booking.collected_at
                    else None
                ),
                "created_at": (
                    sea_booking.created_at.isoformat()
                    if sea_booking.created_at
                    else None
                ),
                "shipping_mark": (
                    shipping_mark.shipping_mark_code if shipping_mark else None
                ),
                "tracking_number": tracking_number_map.get(sea_booking.id),
                "shipping_label_available": shipping_mark is not None,
                "shipping_label_path": f"/label/sea/{sea_booking.id}",
                "customer_display_name": (
                    user.name.strip()
                    if user and user.name and user.name.strip()
                    else "Customer name not available"
                ),
                "destination": destination,
                "cargo_type": "Sea Cargo",
                "carton_count": shipping_mark.carton_count if shipping_mark else None,
                "latest_update": latest_event.description if latest_event else None,
                "latest_update_at": (
                    latest_event.timestamp.isoformat() if latest_event else None
                ),
                "estimated_arrival": (
                    container.estimated_arrival_date.isoformat()
                    if container and container.estimated_arrival_date
                    else None
                ),
                "goods_types": [
                    {
                        "id": str(gt.goods_type.id),
                        "name": gt.goods_type.name,
                        "is_hazardous": gt.goods_type.is_hazardous,
                    }
                    for gt in goods_types
                    if gt.goods_type
                ],
            }
        )

    return {"total": total, "skip": skip, "limit": limit, "sea_bookings": sea_bookings}


@router.patch("/sea-bookings/{sea_booking_id}/status")
def update_sea_booking_status(
    sea_booking_id: str,
    body: SeaBookingStatusUpdateRequest,
    db: Session = Depends(get_db),
    admin: User = Depends(get_cargo_admin),
):
    sea_booking = _get_sea_booking_for_admin(db, sea_booking_id, admin.id)

    valid_statuses = {"ready", "held", "released", "collected"}
    new_status = (body.goods_status or "").strip().lower()
    if new_status not in valid_statuses:
        raise HTTPException(
            status_code=400,
            detail="Invalid goods_status. Use ready, held, released, or collected.",
        )

    if sea_booking.goods_status == new_status:
        return {
            "message": "Sea booking already in requested status",
            "sea_booking": _sea_booking_detail(sea_booking),
        }

    allowed_transitions = {
        "ready": {"held", "released"},
        "held": {"released"},
        "released": {"collected"},
        "collected": set(),
    }
    if new_status not in allowed_transitions.get(sea_booking.goods_status, set()):
        raise HTTPException(
            status_code=400,
            detail=(
                f"Invalid transition from {sea_booking.goods_status} to {new_status}."
            ),
        )

    if new_status == "collected" and sea_booking.payment_status != "confirmed":
        raise HTTPException(
            status_code=400,
            detail="Goods cannot be collected until payment is confirmed.",
        )

    old_status = sea_booking.goods_status
    sea_booking.goods_status = new_status
    if new_status == "held":
        sea_booking.hold_reason = (body.reason or "Held by cargo admin").strip()
        sea_booking.hold_marked_at = datetime.utcnow()
        sea_booking.hold_marked_by = admin.id
    elif new_status == "released":
        sea_booking.hold_reason = None
    elif new_status == "collected":
        sea_booking.collected_at = datetime.utcnow()
        _generate_receipt(db, sea_booking_id=sea_booking.id)

    TrackingService.create_tracking_event(
        db=db,
        entity_type="sea_booking",
        entity_id=str(sea_booking.id),
        event_type="booking_status_updated",
        description=f"Sea booking status changed from {old_status} to {new_status}",
        triggered_by=str(admin.id),
        extra_data={
            "old_status": old_status,
            "new_status": new_status,
            "reason": body.reason,
        },
    )

    actor = admin.name or "Cargo Admin"
    actor_role = _actor_label(admin)
    _notify_sea_booking_user(
        db,
        sea_booking,
        notification_type="sea_booking_status_update",
        message=(
            f"{actor} ({actor_role}) updated your sea booking goods status "
            f"from {old_status} to {new_status}."
        ),
        target_type="sea_booking",
        target_id=sea_booking.id,
    )

    log_action(
        db=db,
        action="SEA_BOOKING_STATUS_UPDATED",
        user_id=admin.id,
        entity_type="sea_booking",
        entity_id=sea_booking.id,
        reason=body.reason,
    )

    db.commit()
    db.refresh(sea_booking)

    return {
        "message": "Sea booking status updated",
        "sea_booking": _sea_booking_detail(sea_booking),
    }


@router.get("/sea-bookings/{sea_booking_id}/shipping-label")
def get_sea_booking_shipping_label(
    sea_booking_id: str,
    db: Session = Depends(get_db),
    admin: User = Depends(get_cargo_admin),
):
    sea_booking = _get_sea_booking_for_admin(db, sea_booking_id, admin.id)
    shipping_mark, created = _get_or_create_sea_booking_shipping_mark(db, sea_booking)
    if created:
        db.commit()
        db.refresh(shipping_mark)

    company = operator_document_branding(db, admin.id)
    return build_printable_label(shipping_mark, company["name"])


@router.get("/sea-bookings/{sea_booking_id}/shipping-label/details")
def get_sea_booking_shipping_label_details(
    sea_booking_id: str,
    db: Session = Depends(get_db),
    admin: User = Depends(get_cargo_admin),
):
    """Cargo admin: view shipping label data for a sea_booking."""
    sea_booking = _get_sea_booking_for_admin(db, sea_booking_id, admin.id)
    shipping_mark, created = _get_or_create_sea_booking_shipping_mark(db, sea_booking)
    if created:
        db.commit()
        db.refresh(shipping_mark)

    linked_order = (
        db.query(ShipmentOrder)
        .filter(
            ShipmentOrder.sea_booking_id == sea_booking.id,
            ShipmentOrder.tracking_number.isnot(None),
        )
        .order_by(ShipmentOrder.created_at.desc())
        .first()
    )

    company = operator_document_branding(db, admin.id)
    label = build_printable_label(shipping_mark, company["name"])
    return {
        "company": company,
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
                    sea_booking.container.arrival_date
                    if sea_booking.container
                    else None
                ),
            },
            "customer": {
                "name": sea_booking.user.name if sea_booking.user else None,
                "phone_number": (
                    sea_booking.user.phone_number if sea_booking.user else None
                ),
            },
        },
        "label": label,
    }


@router.patch("/sea-bookings/{sea_booking_id}/shipping-label")
def update_sea_booking_shipping_label(
    sea_booking_id: str,
    body: ShippingLabelUpdateRequest,
    db: Session = Depends(get_db),
    admin: User = Depends(get_cargo_admin),
):
    """Cargo admin: update sea_booking shipping label fields."""
    sea_booking = _get_sea_booking_for_admin(db, sea_booking_id, admin.id)
    shipping_mark, _ = _get_or_create_sea_booking_shipping_mark(db, sea_booking)

    if body.destination_region is not None:
        dest = body.destination_region.strip()
        if not dest:
            raise HTTPException(
                status_code=400, detail="Destination region is required"
            )
        shipping_mark.destination_region = dest
        shipping_mark.shipping_mark_code = generate_shipping_mark_code(
            "SEA", dest, str(sea_booking.id)
        )

    if body.carton_count is not None:
        if body.carton_count < 1 or body.carton_count > 999:
            raise HTTPException(
                status_code=400, detail="Carton count must be between 1 and 999"
            )
        shipping_mark.carton_count = body.carton_count

    if body.packing_list_summary is not None:
        shipping_mark.packing_list_summary = body.packing_list_summary.strip() or None

    db.commit()
    db.refresh(shipping_mark)
    return {
        "message": "Shipping label updated",
        "label": build_printable_label(shipping_mark),
    }


def _build_container_consolidated_packing_list(
    db: Session, container: Container
) -> dict:
    """Build the source data for a full container packing-list export."""
    sea_bookings = (
        db.query(SeaBooking)
        .options(
            joinedload(SeaBooking.user),
            joinedload(SeaBooking.shipping_mark),
            joinedload(SeaBooking.goods_types).joinedload(SeaBookingGoods.goods_type),
        )
        .filter(SeaBooking.container_id == container.id)
        .order_by(SeaBooking.created_at.asc())
        .all()
    )
    if not sea_bookings:
        raise HTTPException(
            status_code=400,
            detail="No sea bookings found for this container.",
        )

    sea_booking_ids = [row.id for row in sea_bookings]
    linked_orders = (
        db.query(ShipmentOrder)
        .filter(
            ShipmentOrder.sea_booking_id.in_(sea_booking_ids),
            ShipmentOrder.tracking_number.isnot(None),
        )
        .order_by(ShipmentOrder.created_at.desc())
        .all()
    )
    tracking_number_map = {}
    for order in linked_orders:
        if order.sea_booking_id not in tracking_number_map:
            tracking_number_map[order.sea_booking_id] = order.tracking_number

    missing_tracking_numbers = [
        {
            "sea_booking_id": str(sea_booking.id),
            "sea_booking_reference": build_display_reference(
                "sea_booking", sea_booking.id, sea_booking.created_at
            ),
        }
        for sea_booking in sea_bookings
        if not tracking_number_map.get(sea_booking.id)
    ]
    if missing_tracking_numbers:
        missing_references = ", ".join(
            row["sea_booking_reference"] for row in missing_tracking_numbers
        )
        raise HTTPException(
            status_code=422,
            detail=(
                "Generate tracking numbers before creating a consolidated packing "
                f"list. Affected sea bookings: {missing_references}."
            ),
        )

    packing_lists = (
        db.query(SeaBookingPackingList)
        .filter(
            SeaBookingPackingList.container_id == container.id,
            SeaBookingPackingList.sea_booking_id.in_(sea_booking_ids),
        )
        .order_by(SeaBookingPackingList.created_at.asc())
        .all()
    )
    packing_list_ids = [row.id for row in packing_lists]
    packing_items = []
    if packing_list_ids:
        packing_items = (
            db.query(SeaBookingPackingListItem)
            .filter(SeaBookingPackingListItem.packing_list_id.in_(packing_list_ids))
            .order_by(SeaBookingPackingListItem.created_at.asc())
            .all()
        )

    booked_cbm_total = float(
        db.query(func.coalesce(func.sum(SeaBooking.cbm_booked), 0))
        .filter(SeaBooking.id.in_(sea_booking_ids))
        .scalar()
        or 0
    )
    loaded_cbm_total = float(
        sum(
            float(item.cbm or 0)
            for item in packing_items
            if item.status in {"loaded", "completed"}
        )
    )
    max_cbm = float(container.max_cbm or 0)
    fill_from_booked = (booked_cbm_total / max_cbm * 100) if max_cbm > 0 else 0
    fill_from_loaded = (loaded_cbm_total / max_cbm * 100) if max_cbm > 0 else 0
    is_full = (
        container.status == "full" or fill_from_booked >= 100 or fill_from_loaded >= 100
    )
    if not is_full:
        raise HTTPException(
            status_code=400,
            detail=(
                "Container is not full yet. Consolidated packing list is available "
                "only when full."
            ),
        )

    list_to_sea_booking = {row.id: row.sea_booking_id for row in packing_lists}
    items_by_sea_booking = {sea_booking.id: [] for sea_booking in sea_bookings}
    for item in packing_items:
        sea_booking_id = list_to_sea_booking.get(item.packing_list_id)
        if sea_booking_id in items_by_sea_booking:
            items_by_sea_booking[sea_booking_id].append(item)

    consolidated_rows = []
    for sea_booking in sea_bookings:
        customer_name = (
            sea_booking.user.name
            if sea_booking.user and sea_booking.user.name
            else "Customer"
        )
        common = {
            "sea_booking_id": str(sea_booking.id),
            "sea_booking_reference": build_display_reference(
                "sea_booking", sea_booking.id, sea_booking.created_at
            ),
            "customer_name": customer_name,
            "tracking_number": tracking_number_map[sea_booking.id],
            "shipping_mark": (
                sea_booking.shipping_mark.shipping_mark_code
                if sea_booking.shipping_mark
                else None
            ),
        }
        detailed_items = items_by_sea_booking[sea_booking.id]
        if detailed_items:
            for item in detailed_items:
                consolidated_rows.append(
                    {
                        **common,
                        "item_id": str(item.id),
                        "item_name": item.item_name,
                        "supplier_details": item.supplier_details,
                        "cartons": int(item.cartons or 0),
                        "cbm": float(item.cbm or 0),
                        "weight_kg": float(item.weight_kg or 0),
                        "status": item.status,
                        "notes": item.notes,
                        "source": "packing_item",
                    }
                )
            continue

        goods_names = [
            goods.goods_type.name
            for goods in sea_booking.goods_types
            if goods.goods_type and goods.goods_type.name
        ]
        consolidated_rows.append(
            {
                **common,
                "item_id": None,
                "item_name": (
                    ", ".join(goods_names)
                    if goods_names
                    else "Booked cargo space (baseline booking snapshot)"
                ),
                "supplier_details": (
                    sea_booking.shipping_mark.packing_list_summary
                    if sea_booking.shipping_mark
                    and sea_booking.shipping_mark.packing_list_summary
                    else None
                ),
                "cartons": int(
                    sea_booking.shipping_mark.carton_count
                    if sea_booking.shipping_mark
                    and sea_booking.shipping_mark.carton_count is not None
                    else 0
                ),
                "cbm": float(sea_booking.cbm_booked or 0),
                "weight_kg": None,
                "status": "booked",
                "notes": (
                    "Baseline booking data; detailed warehouse packing items are "
                    "not recorded yet."
                ),
                "source": "booking_baseline",
            }
        )

    return {
        "issuer": operator_document_branding(db, container.admin_id),
        "container": {
            "id": str(container.id),
            "reference": build_display_reference(
                "container", container.id, container.created_at
            ),
            "container_size": container.container_size,
            "status": container.status,
            "max_cbm": max_cbm,
            "booked_cbm_total": booked_cbm_total,
            "loaded_cbm_total": loaded_cbm_total,
            "fill_from_booked_percentage": round(fill_from_booked, 2),
            "fill_from_loaded_percentage": round(fill_from_loaded, 2),
        },
        "summary": {
            "sea_booking_count": len(sea_bookings),
            "customer_count": len(
                {
                    sea_booking.user_id
                    for sea_booking in sea_bookings
                    if sea_booking.user_id
                }
            ),
            "packing_list_count": len(packing_lists),
            "item_count": len(consolidated_rows),
            "total_cartons": int(sum(row["cartons"] for row in consolidated_rows)),
            "total_cbm": round(sum(row["cbm"] for row in consolidated_rows), 4),
            "total_weight_kg": round(
                sum(
                    row["weight_kg"]
                    for row in consolidated_rows
                    if row["weight_kg"] is not None
                ),
                4,
            ),
            "missing_weight_item_count": sum(
                1 for row in consolidated_rows if row["weight_kg"] is None
            ),
        },
        "generated_at": datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC"),
        "items": consolidated_rows,
    }


@router.get("/containers/{container_id}/consolidated-packing-list")
def get_container_consolidated_packing_list(
    container_id: str,
    db: Session = Depends(get_db),
    admin: User = Depends(get_cargo_admin),
):
    """Return the validated data used by the container packing-list export."""
    container = _get_container_for_admin(db, container_id, admin.id)
    return _build_container_consolidated_packing_list(db, container)


def _serialize_consolidated_packing_list(
    packing_list: ContainerConsolidatedPackingList,
    container: Container,
    generated_by: Optional[User],
) -> dict:
    """Return the safe, cargo-admin-facing document metadata."""
    packing_list_reference = build_display_reference(
        "packing_list", packing_list.id, packing_list.created_at
    )
    return {
        "id": str(packing_list.id),
        "packing_list_id": str(packing_list.id),
        "packing_list_reference": packing_list_reference,
        "container_id": str(container.id),
        "container_reference": packing_list.container_reference,
        "container_size": container.container_size,
        "status": packing_list.status,
        "document_url": packing_list.document_url,
        "generated_by": (
            str(packing_list.generated_by) if packing_list.generated_by else None
        ),
        "generated_by_name": (
            generated_by.name if generated_by and generated_by.name else "Cargo Admin"
        ),
        "created_at": (
            packing_list.created_at.isoformat() if packing_list.created_at else None
        ),
        "updated_at": (
            packing_list.updated_at.isoformat() if packing_list.updated_at else None
        ),
        "view_endpoint": (
            f"/cargo_admin/financial/consolidated-packing-lists/{packing_list.id}/pdf"
        ),
    }


@router.post("/containers/{container_id}/consolidated-packing-list/generate")
def generate_container_consolidated_packing_list(
    container_id: str,
    db: Session = Depends(get_db),
    admin: User = Depends(get_cargo_admin),
):
    """Generate, store, and register a consolidated container packing-list PDF."""
    container = _get_container_for_admin(db, container_id, admin.id)
    payload = _build_container_consolidated_packing_list(db, container)
    content = (
        DocumentGenerationService.generate_consolidated_container_packing_list_pdf(
            payload
        )
    )
    document_url = DocumentGenerationService.upload_document_to_cloudinary(
        content,
        "consolidated_packing_lists/pdf",
        str(container.id),
        "pdf",
        db=db,
        operator_id=admin.id,
    )
    if not document_url:
        raise HTTPException(
            status_code=500,
            detail="Packing list generated but failed to save its document.",
        )

    packing_list = ContainerConsolidatedPackingList(
        container_id=container.id,
        container_reference=payload["container"]["reference"],
        generated_by=admin.id,
        document_url=document_url,
        status="generated",
    )
    db.add(packing_list)
    db.commit()
    db.refresh(packing_list)
    return _serialize_consolidated_packing_list(packing_list, container, admin)


@router.get("/containers/{container_id}/consolidated-packing-list/export/pdf")
def export_container_consolidated_packing_list_pdf(
    container_id: str,
    db: Session = Depends(get_db),
    admin: User = Depends(get_cargo_admin),
):
    """Stream a consolidated packing-list PDF for a cargo-admin container."""
    container = _get_container_for_admin(db, container_id, admin.id)
    payload = _build_container_consolidated_packing_list(db, container)
    content = (
        DocumentGenerationService.generate_consolidated_container_packing_list_pdf(
            payload
        )
    )
    reference = payload["container"]["reference"].replace("/", "-")
    return StreamingResponse(
        iter([content]),
        media_type="application/pdf",
        headers={
            "Content-Disposition": (
                f'inline; filename="consolidated-packing-list-{reference}.pdf"'
            )
        },
    )


@router.get("/financial/consolidated-packing-lists")
def list_cargo_admin_consolidated_packing_lists(
    container_id: Optional[str] = None,
    include_archived: bool = Query(False),
    db: Session = Depends(get_db),
    admin: User = Depends(get_cargo_admin),
):
    """List generated consolidated PDFs for containers managed by this admin."""
    query = (
        db.query(ContainerConsolidatedPackingList, Container, User)
        .join(
            Container,
            ContainerConsolidatedPackingList.container_id == Container.id,
        )
        .outerjoin(User, ContainerConsolidatedPackingList.generated_by == User.id)
        .filter(Container.admin_id == admin.id)
    )
    if not include_archived:
        query = query.filter(Container.is_archived.is_(False))
    if container_id:
        query = query.filter(
            ContainerConsolidatedPackingList.container_id == container_id
        )

    rows = query.order_by(ContainerConsolidatedPackingList.created_at.desc()).all()
    return {
        "packing_lists": [
            _serialize_consolidated_packing_list(packing_list, container, generated_by)
            for packing_list, container, generated_by in rows
        ]
    }


@router.get("/financial/consolidated-packing-lists/{packing_list_id}/pdf")
def stream_cargo_admin_consolidated_packing_list_pdf(
    packing_list_id: str,
    db: Session = Depends(get_db),
    admin: User = Depends(get_cargo_admin),
):
    """Securely view or download one generated consolidated packing-list PDF."""
    row = (
        db.query(ContainerConsolidatedPackingList, Container)
        .join(
            Container,
            ContainerConsolidatedPackingList.container_id == Container.id,
        )
        .filter(
            ContainerConsolidatedPackingList.id == packing_list_id,
            Container.admin_id == admin.id,
        )
        .first()
    )
    if not row:
        raise HTTPException(status_code=404, detail="Packing list document not found")

    packing_list, container = row
    filename = (
        "consolidated-packing-list-"
        f"{packing_list.container_reference or str(container.id)}.pdf"
    )
    return stream_safe_document(packing_list.document_url, filename, inline=True)


@router.post("/sea-bookings/{sea_booking_id}/collect")
def mark_goods_collected(
    sea_booking_id: str,
    body: MarkCollectedRequest,
    db: Session = Depends(get_db),
    admin: User = Depends(get_cargo_admin),
):
    sea_booking = _get_sea_booking_for_admin(db, sea_booking_id, admin.id)

    if sea_booking.goods_status == "collected":
        existing_receipt = (
            db.query(Receipt)
            .filter(Receipt.sea_booking_id == sea_booking.id)
            .order_by(Receipt.generated_at.desc())
            .first()
        )
        return {
            "message": "Goods already collected",
            "receipt_number": (
                existing_receipt.receipt_number if existing_receipt else None
            ),
            "receipt_token": (
                existing_receipt.receipt_token if existing_receipt else None
            ),
        }

    if sea_booking.payment_status != "confirmed":
        raise HTTPException(
            status_code=400,
            detail="Goods cannot be collected until payment is confirmed",
        )

    sea_booking.goods_status = "collected"
    sea_booking.collected_at = datetime.utcnow()

    # NEW: Create tracking event for goods collection
    TrackingService.create_tracking_event(
        db,
        entity_type="sea_booking",
        entity_id=str(sea_booking.id),
        event_type="goods_collected",
        description="Goods for sea booking collected by customer",
        triggered_by=str(admin.id),
        extra_data={
            "reason": body.reason,
            "collected_at": sea_booking.collected_at.isoformat(),
        },
    )

    log_action(
        db=db,
        action="GOODS_COLLECTED",
        user_id=admin.id,
        entity_type="sea_booking",
        entity_id=sea_booking.id,
        reason=body.reason,
    )

    db.commit()

    receipt = _generate_receipt(db, sea_booking_id=sea_booking.id)
    db.commit()
    db.refresh(receipt)

    return {
        "message": "Goods marked as collected",
        "receipt_number": receipt.receipt_number,
        "receipt_token": receipt.receipt_token,
    }


@router.post("/sea-bookings/{sea_booking_id}/confirm-payment")
def confirm_sea_booking_payment(
    sea_booking_id: str,
    db: Session = Depends(get_db),
    admin: User = Depends(get_cargo_admin),
):
    sea_booking = _get_sea_booking_for_admin(db, sea_booking_id, admin.id)

    if sea_booking.payment_status == "confirmed":
        return {"message": "Payment already confirmed"}

    if sea_booking.payment_status != "due" and sea_booking.payment_status != "pending":
        raise HTTPException(
            status_code=400,
            detail=(
                "Cannot confirm payment for sea booking with status "
                f"'{sea_booking.payment_status}'"
            ),
        )

    # Find the latest payment record
    latest_payment = (
        db.query(Payment)
        .filter(Payment.sea_booking_id == sea_booking.id)
        .order_by(Payment.created_at.desc())
        .first()
    )

    if not latest_payment or latest_payment.status != "confirmed":
        # Create a manual confirmation record if no confirmed payment exists
        try:
            currency = snapshot_sea_booking_currency(db, sea_booking)
        except ValueError as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc
        payment = Payment(
            sea_booking_id=sea_booking.id,
            amount=sea_booking.logistics_charge,
            currency=currency,
            method="manual_confirmation",
            transaction_reference=f"MANUAL_CONFIRM_{sea_booking.id}",
            status="confirmed",
            paid_at=datetime.utcnow(),
        )
        db.add(payment)

    previous_payment_status = sea_booking.payment_status
    sea_booking.payment_status = "confirmed"
    sea_booking.goods_status = "released"  # Automatically release goods after payment

    # NEW: Create tracking event for payment confirmation
    TrackingService.create_tracking_event(
        db,
        entity_type="sea_booking",
        entity_id=str(sea_booking.id),
        event_type="payment_confirmed",
        description="Payment confirmed for sea booking by admin",
        triggered_by=str(admin.id),
        extra_data={
            "amount": float(sea_booking.logistics_charge),
            "previous_status": previous_payment_status,
        },
    )

    # NEW: Create tracking event for goods release
    TrackingService.create_tracking_event(
        db,
        entity_type="sea_booking",
        entity_id=str(sea_booking.id),
        event_type="goods_released",
        description="Goods released for collection after payment confirmation",
        triggered_by=str(admin.id),
        extra_data={"reason": "payment_confirmed"},
    )

    log_action(
        db=db,
        action="PAYMENT_CONFIRMED_MANUAL",
        user_id=admin.id,
        entity_type="sea_booking",
        entity_id=sea_booking.id,
    )

    db.commit()

    return {
        "message": "Payment confirmed and goods released",
        "sea_booking": _sea_booking_detail(sea_booking),
    }


# ─── Financial Documents ────────────────────────────────


@router.post("/sea-bookings/{sea_booking_id}/generate-invoice")
def generate_sea_booking_invoice(
    sea_booking_id: str,
    format: str = Query("both", pattern="^(excel|pdf|both)$"),
    db: Session = Depends(get_db),
    admin: User = Depends(get_cargo_admin),
):
    """Generate invoice document(s) for sea booking logistics charges."""
    sea_booking = _get_sea_booking_for_admin(db, sea_booking_id, admin.id)

    if sea_booking.payment_status == "confirmed":
        raise HTTPException(
            status_code=400,
            detail="Invoice can only be generated for unpaid sea bookings",
        )

    invoice_number = generate_invoice_number()
    generated_at = datetime.utcnow().isoformat()
    due_date = (
        sea_booking.payment_due_date.isoformat()
        if sea_booking.payment_due_date
        else (datetime.utcnow() + timedelta(days=30)).isoformat()
    )

    customer_name = sea_booking.user.name if sea_booking.user else "Unknown Customer"
    try:
        currency = snapshot_sea_booking_currency(db, sea_booking)
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc

    invoice_data = {
        "invoice_number": invoice_number,
        "sea_booking_id": str(sea_booking.id),
        "customer_name": customer_name,
        "total_amount": float(sea_booking.logistics_charge or 0),
        "currency": currency,
        "status": "draft",
        "generated_at": generated_at,
        "due_date": due_date,
        "items": [
            {
                "description": "Container Logistics Charge",
                "quantity": 1,
                "unit_price": float(sea_booking.logistics_charge or 0),
                "total_price": float(sea_booking.logistics_charge or 0),
                "currency": currency,
            }
        ],
    }

    metadata = {
        "issuer": operator_document_branding(db, admin.id),
        "document_number": invoice_data["invoice_number"],
        "order_id": invoice_data["sea_booking_id"],
        "customer_name": invoice_data["customer_name"],
        "currency": invoice_data["currency"],
        "status": invoice_data["status"],
        "generated_at": generated_at,
    }

    excel_url = None
    pdf_url = None

    if format in ["excel", "both"]:
        excel_bytes = DocumentGenerationService.generate_financial_document_excel(
            "Sea Booking Invoice", metadata, invoice_data["items"]
        )
        excel_url = DocumentGenerationService.upload_document_to_cloudinary(
            excel_bytes,
            "cargo_invoices/excel",
            str(sea_booking.id),
            "xlsx",
            db=db,
            operator_id=admin.id,
        )

    if format in ["pdf", "both"]:
        pdf_bytes = DocumentGenerationService.generate_financial_document_pdf(
            "Sea Booking Invoice", metadata, invoice_data["items"]
        )
        pdf_url = DocumentGenerationService.upload_document_to_cloudinary(
            pdf_bytes,
            "cargo_invoices/pdf",
            str(sea_booking.id),
            "pdf",
            db=db,
            operator_id=admin.id,
        )

    if (format in ["excel", "both"] and not excel_url) or (
        format in ["pdf", "both"] and not pdf_url
    ):
        raise HTTPException(
            status_code=500,
            detail="Invoice document generated but failed to upload",
        )

    due_date_value = (
        sea_booking.payment_due_date
        if sea_booking.payment_due_date
        else datetime.utcnow() + timedelta(days=30)
    )
    invoice_record = SeaBookingInvoice(
        sea_booking_id=sea_booking.id,
        container_id=sea_booking.container_id,
        customer_id=sea_booking.user_id,
        created_by=admin.id,
        invoice_number=invoice_number,
        amount=sea_booking.logistics_charge or 0,
        currency=currency,
        status="draft",
        notes="Generated by cargo admin",
        excel_url=excel_url,
        pdf_url=pdf_url,
        sent_at=None,
        paid_at=None,
        cancelled_at=None,
    )
    db.add(invoice_record)
    db.flush()

    actor = admin.name or "Cargo Admin"
    actor_role = _actor_label(admin)
    _notify_sea_booking_user(
        db,
        sea_booking,
        notification_type="invoice_created",
        message=(
            f"{actor} ({actor_role}) created invoice {invoice_number} "
            f"for your sea booking."
        ),
        target_type="invoice",
        target_id=invoice_record.id,
    )
    db.commit()

    return {
        "invoice_id": str(invoice_record.id),
        "invoice": invoice_data,
        "documents": {
            "requested_format": format,
            "excel_url": excel_url,
            "pdf_url": pdf_url,
        },
        "payment_due_date": due_date_value.isoformat(),
    }


@router.post("/sea-bookings/{sea_booking_id}/generate-receipt")
def generate_sea_booking_receipt(
    sea_booking_id: str,
    format: str = Query("both", pattern="^(excel|pdf|both)$"),
    db: Session = Depends(get_db),
    admin: User = Depends(get_cargo_admin),
):
    """Generate receipt document(s) for paid sea booking logistics charges."""
    sea_booking = _get_sea_booking_for_admin(db, sea_booking_id, admin.id)

    if sea_booking.payment_status != "confirmed":
        raise HTTPException(
            status_code=400,
            detail="Receipt can only be generated for payment-confirmed sea bookings",
        )

    try:
        receipt = _generate_receipt(db, sea_booking_id=sea_booking.id)
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    receipt.status = "issued"
    receipt.issued_by = admin.id
    receipt.voided_at = None
    receipt.voided_by = None
    db.commit()
    db.refresh(receipt)
    generated_at = (
        receipt.generated_at.isoformat()
        if receipt.generated_at
        else datetime.utcnow().isoformat()
    )
    customer_name = sea_booking.user.name if sea_booking.user else "Unknown Customer"
    try:
        currency = snapshot_sea_booking_currency(db, sea_booking)
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    if receipt.currency is None:
        receipt.currency = currency
    if receipt.amount is None:
        receipt.amount = sea_booking.logistics_charge or 0
    db.flush()
    currency = receipt.currency
    receipt_amount = float(receipt.amount or 0)

    receipt_data = {
        "receipt_number": receipt.receipt_number,
        "receipt_token": receipt.receipt_token,
        "sea_booking_id": str(sea_booking.id),
        "customer_name": customer_name,
        "total_amount": receipt_amount,
        "currency": currency,
        "status": "paid",
        "generated_at": generated_at,
        "items": [
            {
                "description": "Container Logistics Charge",
                "quantity": 1,
                "unit_price": receipt_amount,
                "total_price": receipt_amount,
                "currency": currency,
            }
        ],
    }

    metadata = {
        "issuer": operator_document_branding(db, admin.id),
        "document_number": receipt_data["receipt_number"],
        "order_id": receipt_data["sea_booking_id"],
        "customer_name": receipt_data["customer_name"],
        "currency": receipt_data["currency"],
        "status": receipt_data["status"],
        "generated_at": generated_at,
    }

    excel_url = None
    pdf_url = None

    if format in ["excel", "both"]:
        excel_bytes = DocumentGenerationService.generate_financial_document_excel(
            "Sea Booking Receipt", metadata, receipt_data["items"]
        )
        excel_url = DocumentGenerationService.upload_document_to_cloudinary(
            excel_bytes,
            "cargo_receipts/excel",
            str(sea_booking.id),
            "xlsx",
            db=db,
            operator_id=admin.id,
        )

    if format in ["pdf", "both"]:
        pdf_bytes = DocumentGenerationService.generate_financial_document_pdf(
            "Sea Booking Receipt", metadata, receipt_data["items"]
        )
        pdf_url = DocumentGenerationService.upload_document_to_cloudinary(
            pdf_bytes,
            "cargo_receipts/pdf",
            str(sea_booking.id),
            "pdf",
            db=db,
            operator_id=admin.id,
        )
        if pdf_url:
            receipt.pdf_url = pdf_url
            db.commit()
            db.refresh(receipt)

    if (format in ["excel", "both"] and not excel_url) or (
        format in ["pdf", "both"] and not pdf_url
    ):
        raise HTTPException(
            status_code=500,
            detail="Receipt document generated but failed to upload",
        )

    actor = admin.name or "Cargo Admin"
    actor_role = _actor_label(admin)
    _notify_sea_booking_user(
        db,
        sea_booking,
        notification_type="receipt_issued",
        message=(
            f"{actor} ({actor_role}) issued receipt "
            f"{receipt.receipt_number} for your sea booking."
        ),
        target_type="receipt",
        target_id=receipt.id,
    )
    db.commit()

    return {
        "receipt": receipt_data,
        "documents": {
            "requested_format": format,
            "excel_url": excel_url,
            "pdf_url": pdf_url,
        },
    }


@router.get("/financial/invoices")
def list_sea_booking_invoices(
    db: Session = Depends(get_db),
    admin: User = Depends(get_cargo_admin),
):
    """List invoice candidates for sea bookings not yet payment-confirmed."""
    sea_bookings = (
        db.query(SeaBooking)
        .join(Container, SeaBooking.container_id == Container.id)
        .options(
            joinedload(SeaBooking.user),
            joinedload(SeaBooking.container),
        )
        .filter(
            Container.admin_id == admin.id,
            SeaBooking.payment_status.in_(["pending", "due", "overdue"]),
        )
        .order_by(SeaBooking.created_at.desc())
        .all()
    )

    return {
        "invoices": [
            {
                "sea_booking_id": str(r.id),
                "invoice_reference": f"INV-{str(r.id).split('-')[0].upper()}",
                "customer_name": r.user.name if r.user else "Unknown Customer",
                "total_amount": float(r.logistics_charge or 0),
                "currency": r.currency
                or (r.container.currency if r.container else None),
                "status": r.payment_status,
                "due_date": (
                    r.payment_due_date.isoformat() if r.payment_due_date else None
                ),
                "created_at": r.created_at.isoformat() if r.created_at else None,
            }
            for r in sea_bookings
        ]
    }


@router.get("/financial/receipts")
def list_sea_booking_receipts(
    db: Session = Depends(get_db),
    admin: User = Depends(get_cargo_admin),
):
    """List generated receipts for this cargo admin sea_bookings."""
    receipts = (
        db.query(Receipt, SeaBooking)
        .join(
            SeaBooking,
            Receipt.sea_booking_id == SeaBooking.id,
        )
        .join(Container, SeaBooking.container_id == Container.id)
        .options(
            joinedload(SeaBooking.user),
            joinedload(SeaBooking.container),
        )
        .filter(Container.admin_id == admin.id)
        .order_by(Receipt.generated_at.desc())
        .all()
    )

    return {
        "receipts": [
            {
                "receipt_id": str(receipt.id),
                "receipt_number": receipt.receipt_number,
                "receipt_token": receipt.receipt_token,
                "pdf_url": receipt.pdf_url,
                "sea_booking_id": str(sea_booking.id),
                "customer_name": (
                    sea_booking.user.name if sea_booking.user else "Unknown Customer"
                ),
                "total_amount": float(
                    receipt.amount
                    if receipt.amount is not None
                    else sea_booking.logistics_charge or 0
                ),
                "currency": receipt.currency,
                "generated_at": (
                    receipt.generated_at.isoformat() if receipt.generated_at else None
                ),
            }
            for receipt, sea_booking in receipts
        ]
    }


@router.get("/financial/packing-lists")
def list_cargo_admin_packing_lists(
    container_id: Optional[str] = None,
    status: Optional[str] = None,
    shipment_stage: Optional[str] = None,
    search: Optional[str] = None,
    include_archived: bool = Query(False),
    db: Session = Depends(get_db),
    admin: User = Depends(get_cargo_admin),
):
    query = (
        db.query(SeaBookingPackingList, SeaBooking, Container)
        .join(
            SeaBooking,
            SeaBookingPackingList.sea_booking_id == SeaBooking.id,
        )
        .join(Container, SeaBookingPackingList.container_id == Container.id)
        .options(
            joinedload(SeaBookingPackingList.customer),
            joinedload(SeaBookingPackingList.items),
        )
        .filter(Container.admin_id == admin.id)
    )

    if not include_archived:
        query = query.filter(Container.is_archived.is_(False))

    if container_id:
        query = query.filter(SeaBookingPackingList.container_id == container_id)
    if status:
        query = query.filter(SeaBookingPackingList.status == status)
    if shipment_stage:
        query = query.filter(SeaBookingPackingList.shipment_stage == shipment_stage)

    rows = query.order_by(SeaBookingPackingList.created_at.desc()).all()
    search_token = (search or "").strip().upper()
    payload = []
    for packing_list, sea_booking, container in rows:
        container_reference = build_display_reference(
            "container", container.id, container.created_at
        )
        packing_list_reference = build_display_reference(
            "packing_list", packing_list.id, packing_list.created_at
        )
        sea_booking_reference = build_display_reference(
            "sea_booking", sea_booking.id, sea_booking.created_at
        )
        row_payload = {
            "packing_list_id": str(packing_list.id),
            "packing_list_reference": packing_list_reference,
            "sea_booking_id": str(sea_booking.id),
            "sea_booking_reference": sea_booking_reference,
            "container_id": str(container.id),
            "container_reference": container_reference,
            "container_size": container.container_size,
            "container_status": container.status,
            "customer_name": (
                packing_list.customer.name
                if packing_list.customer and packing_list.customer.name
                else "Customer"
            ),
            "status": packing_list.status,
            "shipment_stage": packing_list.shipment_stage,
            "total_items": len(packing_list.items or []),
            "total_cartons": int(packing_list.total_cartons or 0),
            "total_cbm": float(packing_list.total_cbm or 0),
            "loaded_cbm": float(packing_list.loaded_cbm or 0),
            "received_cbm": float(packing_list.received_cbm or 0),
            "notes": packing_list.notes,
            "updated_at": (
                packing_list.updated_at.isoformat() if packing_list.updated_at else None
            ),
        }
        if search_token:
            searchable = " ".join(
                [
                    container_reference,
                    packing_list_reference,
                    sea_booking_reference,
                    str(container.id),
                    str(packing_list.id),
                    str(sea_booking.id),
                    row_payload["customer_name"] or "",
                ]
            ).upper()
            if search_token not in searchable:
                continue
        payload.append(row_payload)

    return {"packing_lists": payload}


@router.get("/financial/packing-lists/{packing_list_id}")
def get_cargo_admin_packing_list_detail(
    packing_list_id: str,
    db: Session = Depends(get_db),
    admin: User = Depends(get_cargo_admin),
):
    row = (
        db.query(SeaBookingPackingList, SeaBooking, Container)
        .join(
            SeaBooking,
            SeaBookingPackingList.sea_booking_id == SeaBooking.id,
        )
        .join(Container, SeaBookingPackingList.container_id == Container.id)
        .options(
            joinedload(SeaBookingPackingList.customer),
            joinedload(SeaBookingPackingList.items),
        )
        .filter(
            SeaBookingPackingList.id == packing_list_id,
            Container.admin_id == admin.id,
        )
        .first()
    )
    if not row:
        raise HTTPException(status_code=404, detail="Packing list not found")

    packing_list, sea_booking, container = row
    return {
        "packing_list_id": str(packing_list.id),
        "packing_list_reference": build_display_reference(
            "packing_list", packing_list.id, packing_list.created_at
        ),
        "sea_booking_id": str(sea_booking.id),
        "sea_booking_reference": build_display_reference(
            "sea_booking", sea_booking.id, sea_booking.created_at
        ),
        "container_id": str(container.id),
        "container_reference": build_display_reference(
            "container", container.id, container.created_at
        ),
        "container_size": container.container_size,
        "container_status": container.status,
        "customer_name": (
            packing_list.customer.name
            if packing_list.customer and packing_list.customer.name
            else "Customer"
        ),
        "status": packing_list.status,
        "shipment_stage": packing_list.shipment_stage,
        "total_items": len(packing_list.items or []),
        "total_cartons": int(packing_list.total_cartons or 0),
        "total_cbm": float(packing_list.total_cbm or 0),
        "total_weight_kg": float(packing_list.total_weight_kg or 0),
        "loaded_cbm": float(packing_list.loaded_cbm or 0),
        "received_cbm": float(packing_list.received_cbm or 0),
        "notes": packing_list.notes,
        "created_at": (
            packing_list.created_at.isoformat() if packing_list.created_at else None
        ),
        "updated_at": (
            packing_list.updated_at.isoformat() if packing_list.updated_at else None
        ),
        "items": [
            {
                "id": str(item.id),
                "item_name": item.item_name,
                "supplier_details": item.supplier_details,
                "cartons": int(item.cartons or 0),
                "cbm": float(item.cbm or 0),
                "weight_kg": float(item.weight_kg or 0),
                "status": item.status,
                "notes": item.notes,
                "updated_at": item.updated_at.isoformat() if item.updated_at else None,
            }
            for item in (packing_list.items or [])
        ],
    }


@router.get("/financial/packing-lists/{packing_list_id}/export/csv")
def export_cargo_admin_packing_list_csv(
    packing_list_id: str,
    db: Session = Depends(get_db),
    admin: User = Depends(get_cargo_admin),
):
    payload = get_cargo_admin_packing_list_detail(packing_list_id, db, admin)

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(
        [
            "Packing List Reference",
            "Container Reference",
            "Sea Booking Reference",
            "Customer",
            "Stage",
            "Status",
            "Item Name",
            "Supplier Details",
            "Cartons",
            "CBM",
            "Weight KG",
            "Item Status",
            "Item Notes",
        ]
    )
    for item in payload["items"]:
        writer.writerow(
            [
                payload["packing_list_reference"],
                payload["container_reference"],
                payload["sea_booking_reference"],
                payload["customer_name"],
                payload["shipment_stage"],
                payload["status"],
                item.get("item_name") or "",
                item.get("supplier_details") or "",
                item.get("cartons") or 0,
                item.get("cbm") or 0,
                item.get("weight_kg") or 0,
                item.get("status") or "",
                item.get("notes") or "",
            ]
        )
    output.seek(0)

    safe_reference = str(payload["packing_list_reference"]).replace("/", "-")
    headers = {
        "Content-Disposition": (
            f'attachment; filename="packing-list-{safe_reference}.csv"'
        )
    }
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv; charset=utf-8",
        headers=headers,
    )


@router.get("/sea-bookings/{sea_booking_id}/invoices")
def list_sea_booking_invoice_history(
    sea_booking_id: str,
    db: Session = Depends(get_db),
    admin: User = Depends(get_cargo_admin),
):
    sea_booking = _get_sea_booking_for_admin(db, sea_booking_id, admin.id)
    invoices = (
        db.query(SeaBookingInvoice)
        .filter(SeaBookingInvoice.sea_booking_id == sea_booking.id)
        .order_by(SeaBookingInvoice.created_at.desc())
        .all()
    )
    return {
        "sea_booking_id": str(sea_booking.id),
        "invoices": [
            {
                "id": str(invoice.id),
                "invoice_number": invoice.invoice_number,
                "amount": float(invoice.amount or 0),
                "currency": invoice.currency,
                "status": invoice.status,
                "notes": invoice.notes,
                "excel_url": invoice.excel_url,
                "pdf_url": invoice.pdf_url,
                "sent_at": invoice.sent_at.isoformat() if invoice.sent_at else None,
                "paid_at": invoice.paid_at.isoformat() if invoice.paid_at else None,
                "cancelled_at": (
                    invoice.cancelled_at.isoformat() if invoice.cancelled_at else None
                ),
                "created_at": (
                    invoice.created_at.isoformat() if invoice.created_at else None
                ),
            }
            for invoice in invoices
        ],
    }


@router.get("/sea-bookings/{sea_booking_id}/invoices/{invoice_id}/pdf")
def stream_sea_booking_invoice_pdf(
    sea_booking_id: str,
    invoice_id: str,
    db: Session = Depends(get_db),
    admin: User = Depends(get_cargo_admin),
):
    sea_booking = _get_sea_booking_for_admin(db, sea_booking_id, admin.id)
    invoice = (
        db.query(SeaBookingInvoice)
        .filter(
            SeaBookingInvoice.id == invoice_id,
            SeaBookingInvoice.sea_booking_id == sea_booking.id,
        )
        .first()
    )
    if not invoice or not invoice.pdf_url:
        raise HTTPException(status_code=404, detail="Invoice PDF not found")

    filename = f"{invoice.invoice_number or 'invoice'}.pdf"
    return _stream_cloudinary_document(invoice.pdf_url, filename=filename)


@router.patch("/sea-bookings/{sea_booking_id}/invoices/{invoice_id}/status")
def update_sea_booking_invoice_status(
    sea_booking_id: str,
    invoice_id: str,
    body: SeaBookingInvoiceStatusUpdateRequest,
    db: Session = Depends(get_db),
    admin: User = Depends(get_cargo_admin),
):
    sea_booking = _get_sea_booking_for_admin(db, sea_booking_id, admin.id)
    invoice = (
        db.query(SeaBookingInvoice)
        .filter(
            SeaBookingInvoice.id == invoice_id,
            SeaBookingInvoice.sea_booking_id == sea_booking.id,
        )
        .first()
    )
    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")

    next_status = (body.status or "").strip().lower()
    if next_status not in INVOICE_STATUSES:
        raise HTTPException(status_code=400, detail="Invalid invoice status")

    invoice.status = next_status
    if body.note is not None:
        invoice.notes = body.note.strip() or None
    if next_status == "sent":
        invoice.sent_at = datetime.utcnow()
    if next_status == "paid":
        invoice.paid_at = datetime.utcnow()
    if next_status == "cancelled":
        invoice.cancelled_at = datetime.utcnow()

    if next_status == "paid" and sea_booking.payment_status != "confirmed":
        sea_booking.payment_status = "confirmed"
        TrackingService.create_tracking_event(
            db=db,
            entity_type="sea_booking",
            entity_id=str(sea_booking.id),
            event_type="payment_confirmed",
            description="Invoice marked paid by cargo admin",
            triggered_by=str(admin.id),
            extra_data={"amount": float(invoice.amount or 0)},
        )

    actor = admin.name or "Cargo Admin"
    actor_role = _actor_label(admin)
    _notify_sea_booking_user(
        db,
        sea_booking,
        notification_type="invoice_status_updated",
        message=(
            f"{actor} ({actor_role}) updated invoice "
            f"{invoice.invoice_number} to {next_status}."
        ),
        target_type="invoice",
        target_id=invoice.id,
    )

    db.commit()
    db.refresh(invoice)
    return {
        "message": "Invoice status updated",
        "invoice": {
            "id": str(invoice.id),
            "invoice_number": invoice.invoice_number,
            "status": invoice.status,
        },
    }


@router.post("/sea-bookings/{sea_booking_id}/invoices/{invoice_id}/share")
def share_sea_booking_invoice(
    sea_booking_id: str,
    invoice_id: str,
    db: Session = Depends(get_db),
    admin: User = Depends(get_cargo_admin),
):
    sea_booking = _get_sea_booking_for_admin(db, sea_booking_id, admin.id)
    invoice = (
        db.query(SeaBookingInvoice)
        .filter(
            SeaBookingInvoice.id == invoice_id,
            SeaBookingInvoice.sea_booking_id == sea_booking.id,
        )
        .first()
    )
    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")

    invoice.status = "sent"
    invoice.sent_at = datetime.utcnow()
    actor = admin.name or "Cargo Admin"
    actor_role = _actor_label(admin)
    _notify_sea_booking_user(
        db,
        sea_booking,
        notification_type="invoice_sent",
        message=(
            f"{actor} ({actor_role}) sent invoice "
            f"{invoice.invoice_number} to your dashboard."
        ),
        target_type="invoice",
        target_id=invoice.id,
    )
    db.commit()
    return {"message": "Invoice shared with customer"}


@router.get("/sea-bookings/{sea_booking_id}/receipts")
def list_sea_booking_receipt_history(
    sea_booking_id: str,
    db: Session = Depends(get_db),
    admin: User = Depends(get_cargo_admin),
):
    sea_booking = _get_sea_booking_for_admin(db, sea_booking_id, admin.id)
    receipts = (
        db.query(Receipt)
        .filter(Receipt.sea_booking_id == sea_booking.id)
        .order_by(Receipt.generated_at.desc())
        .all()
    )
    return {
        "sea_booking_id": str(sea_booking.id),
        "receipts": [
            {
                "id": str(receipt.id),
                "receipt_number": receipt.receipt_number,
                "amount": float(receipt.amount or 0),
                "currency": receipt.currency,
                "status": receipt.status or "issued",
                "pdf_url": receipt.pdf_url,
                "notes": receipt.notes,
                "generated_at": (
                    receipt.generated_at.isoformat() if receipt.generated_at else None
                ),
                "voided_at": (
                    receipt.voided_at.isoformat() if receipt.voided_at else None
                ),
            }
            for receipt in receipts
        ],
    }


@router.get("/sea-bookings/{sea_booking_id}/receipts/{receipt_id}/pdf")
def stream_sea_booking_receipt_pdf(
    sea_booking_id: str,
    receipt_id: str,
    db: Session = Depends(get_db),
    admin: User = Depends(get_cargo_admin),
):
    sea_booking = _get_sea_booking_for_admin(db, sea_booking_id, admin.id)
    receipt = (
        db.query(Receipt)
        .filter(Receipt.id == receipt_id, Receipt.sea_booking_id == sea_booking.id)
        .first()
    )
    if not receipt or not receipt.pdf_url:
        raise HTTPException(status_code=404, detail="Receipt PDF not found")

    filename = f"{receipt.receipt_number or 'receipt'}.pdf"
    return _stream_cloudinary_document(receipt.pdf_url, filename=filename)


@router.patch("/sea-bookings/{sea_booking_id}/receipts/{receipt_id}/void")
def void_sea_booking_receipt(
    sea_booking_id: str,
    receipt_id: str,
    db: Session = Depends(get_db),
    admin: User = Depends(get_cargo_admin),
):
    sea_booking = _get_sea_booking_for_admin(db, sea_booking_id, admin.id)
    receipt = (
        db.query(Receipt)
        .filter(Receipt.id == receipt_id, Receipt.sea_booking_id == sea_booking.id)
        .first()
    )
    if not receipt:
        raise HTTPException(status_code=404, detail="Receipt not found")
    if receipt.status == "voided":
        return {"message": "Receipt already voided"}

    receipt.status = "voided"
    receipt.voided_at = datetime.utcnow()
    receipt.voided_by = admin.id
    actor = admin.name or "Cargo Admin"
    actor_role = _actor_label(admin)
    _notify_sea_booking_user(
        db,
        sea_booking,
        notification_type="receipt_voided",
        message=(
            f"{actor} ({actor_role}) voided receipt {receipt.receipt_number}. "
            "Please contact support for clarification."
        ),
        priority="warning",
        target_type="receipt",
        target_id=receipt.id,
    )
    db.commit()
    return {"message": "Receipt voided"}


@router.get("/sea-bookings/{sea_booking_id}/workflow")
def get_sea_booking_workflow(
    sea_booking_id: str,
    db: Session = Depends(get_db),
    admin: User = Depends(get_cargo_admin),
):
    sea_booking = _get_sea_booking_for_admin(db, sea_booking_id, admin.id)
    snapshot = _get_sea_booking_packing_fill_snapshot(db, sea_booking)
    packing_lists = (
        db.query(SeaBookingPackingList)
        .filter(SeaBookingPackingList.sea_booking_id == sea_booking.id)
        .order_by(SeaBookingPackingList.created_at.desc())
        .all()
    )
    return {
        "sea_booking": _sea_booking_detail(sea_booking),
        "container": _container_detail(sea_booking.container),
        "packing_lists": [
            {
                "id": str(row.id),
                "status": row.status,
                "shipment_stage": row.shipment_stage,
                "total_cartons": row.total_cartons,
                "total_cbm": float(row.total_cbm or 0),
                "total_weight_kg": float(row.total_weight_kg or 0),
                "received_cbm": float(row.received_cbm or 0),
                "loaded_cbm": float(row.loaded_cbm or 0),
                "notes": row.notes,
                "updated_at": row.updated_at.isoformat() if row.updated_at else None,
            }
            for row in packing_lists
        ],
        "fill_summary": snapshot,
    }


@router.post("/sea-bookings/{sea_booking_id}/packing-lists")
def create_sea_booking_packing_list(
    sea_booking_id: str,
    body: SeaBookingPackingListCreateRequest,
    db: Session = Depends(get_db),
    admin: User = Depends(get_cargo_admin),
):
    sea_booking = _get_sea_booking_for_admin(db, sea_booking_id, admin.id)
    stage = (body.shipment_stage or "booking_received").strip().lower()
    if stage not in PACKING_WORKFLOW_STAGES:
        raise HTTPException(status_code=400, detail="Invalid shipment stage")

    packing_list = SeaBookingPackingList(
        sea_booking_id=sea_booking.id,
        container_id=sea_booking.container_id,
        customer_id=sea_booking.user_id,
        created_by=admin.id,
        status="draft",
        shipment_stage=stage,
        notes=body.notes.strip() if body.notes else None,
    )
    db.add(packing_list)
    db.flush()
    TrackingService.create_tracking_event(
        db=db,
        entity_type="sea_booking",
        entity_id=str(sea_booking.id),
        event_type="packing_list_created",
        description=f"Packing list created for sea booking {sea_booking.id}",
        triggered_by=str(admin.id),
        extra_data={
            "packing_list_id": str(packing_list.id),
            "logistics_stage": "packed_verified",
        },
    )
    actor = admin.name or "Cargo Admin"
    actor_role = _actor_label(admin)
    _notify_sea_booking_user(
        db,
        sea_booking,
        notification_type="packing_list_created",
        message=(
            f"{actor} ({actor_role}) created a packing list for your " "sea_booking."
        ),
        target_type="packing_list",
        target_id=packing_list.id,
    )
    db.commit()
    return {"packing_list_id": str(packing_list.id), "status": packing_list.status}


@router.get("/sea-bookings/{sea_booking_id}/packing-lists")
def list_sea_booking_packing_lists(
    sea_booking_id: str,
    db: Session = Depends(get_db),
    admin: User = Depends(get_cargo_admin),
):
    sea_booking = _get_sea_booking_for_admin(db, sea_booking_id, admin.id)
    packing_lists = (
        db.query(SeaBookingPackingList)
        .filter(SeaBookingPackingList.sea_booking_id == sea_booking.id)
        .order_by(SeaBookingPackingList.created_at.desc())
        .all()
    )
    response = []
    for row in packing_lists:
        items = (
            db.query(SeaBookingPackingListItem)
            .filter(SeaBookingPackingListItem.packing_list_id == row.id)
            .order_by(SeaBookingPackingListItem.created_at.asc())
            .all()
        )
        response.append(
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
                    }
                    for item in items
                ],
            }
        )
    return {"packing_lists": response}


def _build_sea_booking_individual_packing_snapshot(
    db: Session, sea_booking: SeaBooking
) -> dict:
    packing_lists = (
        db.query(SeaBookingPackingList)
        .filter(SeaBookingPackingList.sea_booking_id == sea_booking.id)
        .order_by(SeaBookingPackingList.created_at.desc())
        .all()
    )

    flattened_items = []
    total_cartons = 0
    total_cbm = 0.0
    total_weight_kg = 0.0

    for row in packing_lists:
        items = (
            db.query(SeaBookingPackingListItem)
            .filter(SeaBookingPackingListItem.packing_list_id == row.id)
            .order_by(SeaBookingPackingListItem.created_at.asc())
            .all()
        )
        for item in items:
            cartons = int(item.cartons or 0)
            cbm = float(item.cbm or 0)
            weight_kg = float(item.weight_kg or 0)
            total_cartons += cartons
            total_cbm += cbm
            total_weight_kg += weight_kg
            flattened_items.append(
                {
                    "packing_list_id": str(row.id),
                    "packing_list_status": row.status,
                    "shipment_stage": row.shipment_stage,
                    "item_id": str(item.id),
                    "item_name": item.item_name,
                    "supplier_details": item.supplier_details,
                    "cartons": cartons,
                    "cbm": cbm,
                    "weight_kg": weight_kg,
                    "status": item.status,
                    "notes": item.notes,
                    "updated_at": (
                        item.updated_at.isoformat() if item.updated_at else None
                    ),
                }
            )

    if not flattened_items:
        shipping_mark = (
            db.query(ShippingMark)
            .filter(ShippingMark.sea_booking_id == sea_booking.id)
            .first()
        )
        goods_types = (
            db.query(SeaBookingGoods)
            .options(joinedload(SeaBookingGoods.goods_type))
            .filter(SeaBookingGoods.sea_booking_id == sea_booking.id)
            .all()
        )
        goods_names = [
            row.goods_type.name
            for row in goods_types
            if row.goods_type and row.goods_type.name
        ]
        baseline_cartons = int(
            (shipping_mark.carton_count or 0) if shipping_mark else 0
        )
        baseline_cbm = float(sea_booking.cbm_booked or 0)
        total_cartons = baseline_cartons
        total_cbm = baseline_cbm
        total_weight_kg = 0.0
        flattened_items = [
            {
                "packing_list_id": None,
                "packing_list_status": "booking",
                "shipment_stage": "booking_received",
                "item_id": None,
                "item_name": (
                    ", ".join(goods_names)
                    if goods_names
                    else "Booked cargo space (baseline booking snapshot)"
                ),
                "supplier_details": (
                    shipping_mark.packing_list_summary
                    if shipping_mark and shipping_mark.packing_list_summary
                    else "No supplier details captured yet."
                ),
                "cartons": baseline_cartons,
                "cbm": baseline_cbm,
                "weight_kg": 0.0,
                "status": "booked",
                "notes": (
                    "This is a baseline booking snapshot before detailed "
                    "warehouse packing entries."
                ),
                "updated_at": None,
            }
        ]

    customer_name = (
        sea_booking.user.name
        if sea_booking.user and sea_booking.user.name
        else (
            sea_booking.user.phone_number
            if sea_booking.user and sea_booking.user.phone_number
            else "Customer"
        )
    )
    now = datetime.utcnow()
    return {
        "sea_booking_id": str(sea_booking.id),
        "sea_booking_reference": build_display_reference(
            "sea_booking", sea_booking.id, sea_booking.created_at
        ),
        "container_id": (
            str(sea_booking.container.id)
            if sea_booking.container and sea_booking.container.id
            else None
        ),
        "container_reference": (
            build_display_reference(
                "container",
                sea_booking.container.id,
                sea_booking.container.created_at,
            )
            if sea_booking.container and sea_booking.container.id
            else None
        ),
        "container_status": (
            sea_booking.container.status if sea_booking.container else None
        ),
        "customer_name": customer_name,
        "generated_at": now.isoformat(),
        "as_of_date": now.strftime("%Y-%m-%d"),
        "packing_lists_count": len(packing_lists),
        "items_count": len(flattened_items),
        "totals": {
            "cartons": int(total_cartons),
            "cbm": round(float(total_cbm), 3),
            "weight_kg": round(float(total_weight_kg), 3),
        },
        "items": flattened_items,
    }


@router.get("/sea-bookings/{sea_booking_id}/packing-lists/individual-report")
def get_sea_booking_individual_packing_report(
    sea_booking_id: str,
    db: Session = Depends(get_db),
    admin: User = Depends(get_cargo_admin),
):
    sea_booking = _get_sea_booking_for_admin(db, sea_booking_id, admin.id)
    return _build_sea_booking_individual_packing_snapshot(db, sea_booking)


@router.get("/sea-bookings/{sea_booking_id}/packing-lists/individual-report/export/csv")
def export_sea_booking_individual_packing_report_csv(
    sea_booking_id: str,
    db: Session = Depends(get_db),
    admin: User = Depends(get_cargo_admin),
):
    sea_booking = _get_sea_booking_for_admin(db, sea_booking_id, admin.id)
    payload = _build_sea_booking_individual_packing_snapshot(db, sea_booking)

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(
        [
            "Sea Booking Reference",
            "Container Reference",
            "Customer",
            "As Of Date",
            "Packing List Status",
            "Shipment Stage",
            "Item Name",
            "Supplier Details",
            "Cartons",
            "CBM",
            "Weight KG",
            "Item Status",
            "Item Notes",
        ]
    )
    for item in payload["items"]:
        writer.writerow(
            [
                payload["sea_booking_reference"],
                payload["container_reference"] or "",
                payload["customer_name"],
                payload["as_of_date"],
                item.get("packing_list_status") or "",
                item.get("shipment_stage") or "",
                item.get("item_name") or "",
                item.get("supplier_details") or "",
                item.get("cartons") or 0,
                item.get("cbm") or 0,
                item.get("weight_kg") or 0,
                item.get("status") or "",
                item.get("notes") or "",
            ]
        )
    output.seek(0)

    safe_ref = str(payload["sea_booking_reference"]).replace("/", "-")
    headers = {
        "Content-Disposition": (
            f'attachment; filename="individual-packing-list-{safe_ref}.csv"'
        )
    }
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv; charset=utf-8",
        headers=headers,
    )


@router.post("/sea-bookings/{sea_booking_id}/packing-lists/{packing_list_id}/items")
def add_sea_booking_packing_list_item(
    sea_booking_id: str,
    packing_list_id: str,
    body: SeaBookingPackingListItemCreateRequest,
    db: Session = Depends(get_db),
    admin: User = Depends(get_cargo_admin),
):
    sea_booking = _get_sea_booking_for_admin(db, sea_booking_id, admin.id)
    packing_list = (
        db.query(SeaBookingPackingList)
        .filter(
            SeaBookingPackingList.id == packing_list_id,
            SeaBookingPackingList.sea_booking_id == sea_booking.id,
        )
        .first()
    )
    if not packing_list:
        raise HTTPException(status_code=404, detail="Packing list not found")

    if body.status not in PACKING_ITEM_STATUSES:
        raise HTTPException(status_code=400, detail="Invalid packing item status")
    if body.cartons < 0 or body.cbm < 0 or body.weight_kg < 0:
        raise HTTPException(status_code=400, detail="Invalid negative item totals")

    if body.status in {"loaded", "completed"}:
        snapshot = _get_sea_booking_packing_fill_snapshot(db, sea_booking)
        if body.cbm > snapshot["container_remaining_cbm"]:
            raise HTTPException(
                status_code=400,
                detail="Cannot load item: container capacity would be exceeded.",
            )

    item = SeaBookingPackingListItem(
        packing_list_id=packing_list.id,
        item_name=body.item_name.strip(),
        supplier_details=(
            body.supplier_details.strip() if body.supplier_details else None
        ),
        cartons=body.cartons,
        cbm=body.cbm,
        weight_kg=body.weight_kg,
        status=body.status,
        notes=body.notes.strip() if body.notes else None,
    )
    db.add(item)
    db.flush()
    _sync_packing_list_totals(db, packing_list)

    actor = admin.name or "Cargo Admin"
    actor_role = _actor_label(admin)
    _notify_sea_booking_user(
        db,
        sea_booking,
        notification_type="packing_list_updated",
        message=(
            f"{actor} ({actor_role}) added item '{item.item_name}' "
            "to your packing list."
        ),
        target_type="packing_list",
        target_id=packing_list.id,
    )
    db.commit()
    return {
        "message": "Packing list item added",
        "item_id": str(item.id),
        "packing_list_id": str(packing_list.id),
    }


@router.patch(
    "/sea-bookings/{sea_booking_id}/packing-lists/{packing_list_id}/items/{item_id}"
)
def update_sea_booking_packing_list_item(
    sea_booking_id: str,
    packing_list_id: str,
    item_id: str,
    body: SeaBookingPackingListItemUpdateRequest,
    db: Session = Depends(get_db),
    admin: User = Depends(get_cargo_admin),
):
    sea_booking = _get_sea_booking_for_admin(db, sea_booking_id, admin.id)
    packing_list = (
        db.query(SeaBookingPackingList)
        .filter(
            SeaBookingPackingList.id == packing_list_id,
            SeaBookingPackingList.sea_booking_id == sea_booking.id,
        )
        .first()
    )
    if not packing_list:
        raise HTTPException(status_code=404, detail="Packing list not found")
    item = (
        db.query(SeaBookingPackingListItem)
        .filter(
            SeaBookingPackingListItem.id == item_id,
            SeaBookingPackingListItem.packing_list_id == packing_list.id,
        )
        .first()
    )
    if not item:
        raise HTTPException(status_code=404, detail="Packing list item not found")

    if body.status is not None and body.status not in PACKING_ITEM_STATUSES:
        raise HTTPException(status_code=400, detail="Invalid packing item status")
    if body.cartons is not None and body.cartons < 0:
        raise HTTPException(status_code=400, detail="Cartons cannot be negative")
    if body.cbm is not None and body.cbm < 0:
        raise HTTPException(status_code=400, detail="CBM cannot be negative")
    if body.weight_kg is not None and body.weight_kg < 0:
        raise HTTPException(status_code=400, detail="Weight cannot be negative")

    updated_status = body.status if body.status is not None else item.status
    updated_cbm = body.cbm if body.cbm is not None else float(item.cbm or 0)
    previous_loaded = (
        float(item.cbm or 0) if item.status in {"loaded", "completed"} else 0
    )
    new_loaded = updated_cbm if updated_status in {"loaded", "completed"} else 0
    delta_loaded = new_loaded - previous_loaded
    if delta_loaded > 0:
        snapshot = _get_sea_booking_packing_fill_snapshot(db, sea_booking)
        if delta_loaded > snapshot["container_remaining_cbm"]:
            raise HTTPException(
                status_code=400,
                detail="Cannot mark loaded: container capacity would be exceeded.",
            )

    if body.item_name is not None:
        item.item_name = body.item_name.strip()
    if body.supplier_details is not None:
        item.supplier_details = body.supplier_details.strip() or None
    if body.cartons is not None:
        item.cartons = body.cartons
    if body.cbm is not None:
        item.cbm = body.cbm
    if body.weight_kg is not None:
        item.weight_kg = body.weight_kg
    if body.status is not None:
        item.status = body.status
    if body.notes is not None:
        item.notes = body.notes.strip() or None
    _sync_packing_list_totals(db, packing_list)

    actor = admin.name or "Cargo Admin"
    actor_role = _actor_label(admin)
    _notify_sea_booking_user(
        db,
        sea_booking,
        notification_type="packing_item_status_updated",
        message=(
            f"{actor} ({actor_role}) updated packing item "
            f"'{item.item_name}' to {item.status}."
        ),
        target_type="packing_list_item",
        target_id=item.id,
    )
    db.commit()
    return {"message": "Packing list item updated"}


@router.patch("/sea-bookings/{sea_booking_id}/packing-lists/{packing_list_id}/stage")
def update_sea_booking_packing_stage(
    sea_booking_id: str,
    packing_list_id: str,
    body: SeaBookingPackingStageUpdateRequest,
    db: Session = Depends(get_db),
    admin: User = Depends(get_cargo_admin),
):
    sea_booking = _get_sea_booking_for_admin(db, sea_booking_id, admin.id)
    packing_list = (
        db.query(SeaBookingPackingList)
        .filter(
            SeaBookingPackingList.id == packing_list_id,
            SeaBookingPackingList.sea_booking_id == sea_booking.id,
        )
        .first()
    )
    if not packing_list:
        raise HTTPException(status_code=404, detail="Packing list not found")

    stage = (body.shipment_stage or "").strip().lower()
    if stage not in PACKING_WORKFLOW_STAGES:
        raise HTTPException(status_code=400, detail="Invalid shipment stage")
    packing_list.shipment_stage = stage

    if body.status is not None:
        if body.status not in PACKING_LIST_STATUSES:
            raise HTTPException(status_code=400, detail="Invalid packing list status")
        packing_list.status = body.status
        if body.status == "finalized":
            packing_list.confirmed_at = datetime.utcnow()
    if body.notes is not None:
        packing_list.notes = body.notes.strip() or None

    _sync_packing_list_totals(db, packing_list)
    snapshot = _get_sea_booking_packing_fill_snapshot(db, sea_booking)
    if snapshot["container_remaining_cbm"] <= 0:
        sea_booking.container.status = "full"

    TrackingService.create_tracking_event(
        db=db,
        entity_type="sea_booking",
        entity_id=str(sea_booking.id),
        event_type="logistics_operation_updated",
        description=f"Packing stage updated to {stage}",
        triggered_by=str(admin.id),
        extra_data={
            "logistics_stage": (
                "loaded_container"
                if stage == "products_loaded_into_container"
                else "packed_verified"
            ),
            "public_note": body.notes or "",
            "new_status": stage,
        },
    )

    actor = admin.name or "Cargo Admin"
    actor_role = _actor_label(admin)
    _notify_sea_booking_user(
        db,
        sea_booking,
        notification_type="packing_stage_updated",
        message=(
            f"{actor} ({actor_role}) updated your packing stage "
            f"to {stage.replace('_', ' ')}."
        ),
        target_type="packing_list",
        target_id=packing_list.id,
    )
    db.commit()
    return {"message": "Packing stage updated", "fill_summary": snapshot}


# ─── Dashboard ───────────────────────────────────────────


@router.get("/dashboard/operational-summary")
def cargo_admin_operational_summary(
    db: Session = Depends(get_db),
    admin: User = Depends(get_cargo_admin),
):
    """Role-unrestricted compatibility summary for legacy cargo operators."""
    from app.services.subscriptions import company_for_operator

    company = company_for_operator(db, admin.id)
    return build_cargo_dashboard(
        db,
        owner_id=admin.id,
        permissions=DEFAULT_CARGO_DASHBOARD_PERMISSIONS,
        role_name="Cargo Admin",
        role_scope="company",
        company_id=company.id if company else None,
    )


def _sea_booking_detail(sea_booking):
    """Helper function to return sea_booking details for API response"""
    return {
        "id": str(sea_booking.id),
        "container_id": (
            str(sea_booking.container_id) if sea_booking.container_id else None
        ),
        "user_id": str(sea_booking.user_id) if sea_booking.user_id else None,
        "goods_status": sea_booking.goods_status,
        "payment_status": sea_booking.payment_status,
        "cbm_booked": (
            float(sea_booking.cbm_booked) if sea_booking.cbm_booked else None
        ),
        "logistics_charge": (
            float(sea_booking.logistics_charge)
            if sea_booking.logistics_charge
            else None
        ),
        "currency": sea_booking.currency,
        "payment_due_date": (
            sea_booking.payment_due_date.isoformat()
            if sea_booking.payment_due_date
            else None
        ),
        "hold_reason": sea_booking.hold_reason,
        "hold_marked_by": (
            str(sea_booking.hold_marked_by) if sea_booking.hold_marked_by else None
        ),
        "hold_marked_at": (
            sea_booking.hold_marked_at.isoformat()
            if sea_booking.hold_marked_at
            else None
        ),
        "collected_at": (
            sea_booking.collected_at.isoformat() if sea_booking.collected_at else None
        ),
        "created_at": (
            sea_booking.created_at.isoformat() if sea_booking.created_at else None
        ),
    }


@router.get("/dashboard")
def cargo_admin_dashboard(
    db: Session = Depends(get_db),
    admin: User = Depends(get_cargo_admin),
):
    containers = db.query(Container).filter(Container.admin_id == admin.id)
    total_containers = containers.count()
    active = containers.filter(
        Container.status.in_(["open", "nearly_full", "full"])
    ).count()

    total_booked_cbm = (
        db.query(func.sum(SeaBooking.cbm_booked))
        .join(Container, SeaBooking.container_id == Container.id)
        .filter(Container.admin_id == admin.id)
        .scalar()
        or 0
    )

    overdue = (
        db.query(SeaBooking)
        .join(Container)
        .filter(
            Container.admin_id == admin.id,
            SeaBooking.payment_status == "overdue",
        )
        .count()
    )

    held = (
        db.query(SeaBooking)
        .join(Container)
        .filter(
            Container.admin_id == admin.id,
            SeaBooking.goods_status == "held",
        )
        .count()
    )

    sea_bookings_scope = (
        db.query(SeaBooking).join(Container).filter(Container.admin_id == admin.id)
    )
    total_sea_bookings = sea_bookings_scope.count()
    pending_payments = sea_bookings_scope.filter(
        SeaBooking.payment_status.in_(["pending", "due"])
    ).count()
    released_not_collected = sea_bookings_scope.filter(
        SeaBooking.goods_status == "released"
    ).count()

    air_bookings_scope = db.query(ExpressAirCargoBooking).filter(
        ExpressAirCargoBooking.cargo_admin_id == admin.id
    )
    pending_air_bookings = air_bookings_scope.filter(
        ExpressAirCargoBooking.status.in_(["pending", "confirmed", "label_created"])
    ).count()
    air_in_transit = air_bookings_scope.filter(
        ExpressAirCargoBooking.status == "in_transit"
    ).count()

    sea_booking_ids_query = (
        db.query(SeaBooking.id).join(Container).filter(Container.admin_id == admin.id)
    )
    air_booking_ids_query = db.query(ExpressAirCargoBooking.id).filter(
        ExpressAirCargoBooking.cargo_admin_id == admin.id
    )
    shipment_orders_scope = db.query(ShipmentOrder).filter(
        or_(
            ShipmentOrder.sea_booking_id.in_(sea_booking_ids_query),
            ShipmentOrder.air_booking_id.in_(air_booking_ids_query),
        )
    )
    shipment_orders_needing_update = shipment_orders_scope.filter(
        ShipmentOrder.status.in_(
            [
                ShipmentOrderStatus.pending,
                ShipmentOrderStatus.supplier_contacted,
                ShipmentOrderStatus.confirmed,
                ShipmentOrderStatus.shipped,
            ]
        )
    ).count()

    unread_notifications = (
        db.query(Notification)
        .filter(Notification.user_id == admin.id, Notification.is_read.is_(False))
        .count()
    )

    container_status_counts = {
        status: count
        for status, count in (
            db.query(Container.status, func.count(Container.id))
            .filter(Container.admin_id == admin.id)
            .group_by(Container.status)
            .all()
        )
    }

    def fmt_dt(value):
        return value.isoformat() if value else None

    def sea_booking_payload(row):
        sea_booking, container, user = row
        return {
            "id": str(sea_booking.id),
            "customer_name": user.name if user else "Guest",
            "customer_phone": user.phone_number if user else None,
            "container_id": str(container.id),
            "container_label": (
                f"{container.container_size or 'Container'} - {container.status}"
            ),
            "cbm_booked": float(sea_booking.cbm_booked or 0),
            "logistics_charge": float(sea_booking.logistics_charge or 0),
            "payment_status": sea_booking.payment_status,
            "goods_status": sea_booking.goods_status,
            "hold_reason": sea_booking.hold_reason,
            "created_at": fmt_dt(sea_booking.created_at),
            "route": f"/cargo/sea-bookings?focus={sea_booking.id}",
        }

    recent_sea_bookings = [
        sea_booking_payload(row)
        for row in (
            db.query(SeaBooking, Container, User)
            .join(Container, SeaBooking.container_id == Container.id)
            .join(User, SeaBooking.user_id == User.id, isouter=True)
            .filter(
                Container.admin_id == admin.id,
                or_(
                    SeaBooking.payment_status.in_(["pending", "due", "overdue"]),
                    SeaBooking.goods_status.in_(["held", "released"]),
                ),
            )
            .order_by(SeaBooking.created_at.desc())
            .limit(6)
            .all()
        )
    ]

    recent_air_bookings = [
        {
            "id": str(booking.id),
            "cargo_type": booking.cargo_type.name if booking.cargo_type else "Cargo",
            "customer_name": booking.customer.name if booking.customer else "Unknown",
            "customer_phone": (
                booking.customer.phone_number if booking.customer else None
            ),
            "status": booking.status,
            "weight_kg": float(booking.weight_kg or 0),
            "shipment_date": fmt_dt(booking.shipment_date),
            "created_at": fmt_dt(booking.created_at),
            "route": f"/cargo/express-air-cargo?focus={booking.id}",
        }
        for booking in (
            air_bookings_scope.options(
                joinedload(ExpressAirCargoBooking.customer),
                joinedload(ExpressAirCargoBooking.cargo_type),
            )
            .filter(
                ExpressAirCargoBooking.status.in_(
                    ["pending", "confirmed", "label_created", "in_transit"]
                )
            )
            .order_by(ExpressAirCargoBooking.created_at.desc())
            .limit(6)
            .all()
        )
    ]

    recent_shipment_orders = [
        {
            "id": str(order.id),
            "reference": order.display_reference,
            "supplier_name": order.supplier_name,
            "status": str(
                order.status.value if hasattr(order.status, "value") else order.status
            ),
            "tracking_number": order.tracking_number,
            "created_at": fmt_dt(order.created_at),
            "route": f"/cargo/shipment-orders?focus={order.id}",
        }
        for order in (
            shipment_orders_scope.order_by(ShipmentOrder.created_at.desc())
            .limit(6)
            .all()
        )
    ]

    shipment_order_ids = [order.id for order in shipment_orders_scope.limit(200).all()]
    recent_comments = []
    if shipment_order_ids:
        recent_comments = [
            {
                "id": str(interaction.id),
                "target_id": str(interaction.target_id),
                "author_name": interaction.user.name if interaction.user else "User",
                "content": interaction.content,
                "created_at": fmt_dt(interaction.created_at),
                "route": f"/cargo/shipment-orders?focus={interaction.target_id}",
            }
            for interaction in (
                db.query(Interaction)
                .options(joinedload(Interaction.user))
                .filter(
                    Interaction.target_type == "shipment",
                    Interaction.target_id.in_(shipment_order_ids),
                    Interaction.user_id != admin.id,
                )
                .order_by(Interaction.created_at.desc())
                .limit(5)
                .all()
            )
        ]

    container_ids = [
        row[0]
        for row in db.query(Container.id).filter(Container.admin_id == admin.id).all()
    ]
    sea_booking_ids = [row[0] for row in sea_booking_ids_query.limit(300).all()]
    air_booking_ids = [row[0] for row in air_booking_ids_query.limit(300).all()]
    recent_activity_filters = []
    if container_ids:
        recent_activity_filters.append(
            (TrackingEvent.entity_type == "container")
            & TrackingEvent.entity_id.in_(container_ids)
        )
    if sea_booking_ids:
        recent_activity_filters.append(
            (TrackingEvent.entity_type == "sea_booking")
            & TrackingEvent.entity_id.in_(sea_booking_ids)
        )
    if air_booking_ids:
        recent_activity_filters.append(
            (TrackingEvent.entity_type == "booking")
            & TrackingEvent.entity_id.in_(air_booking_ids)
        )
    if shipment_order_ids:
        recent_activity_filters.append(
            (TrackingEvent.entity_type == "shipment_order")
            & TrackingEvent.entity_id.in_(shipment_order_ids)
        )

    recent_activity = []
    if recent_activity_filters:
        recent_activity = [
            {
                "id": str(event.id),
                "entity_type": event.entity_type,
                "entity_id": str(event.entity_id),
                "event_type": event.event_type,
                "description": event.description,
                "created_at": fmt_dt(event.timestamp),
                "reference": (event.extra_data or {}).get("display_reference"),
            }
            for event in (
                db.query(TrackingEvent)
                .filter(or_(*recent_activity_filters))
                .order_by(TrackingEvent.timestamp.desc())
                .limit(8)
                .all()
            )
        ]

    notifications = [
        {
            "id": str(notification.id),
            "type": notification.type,
            "message": notification.message,
            "priority": notification.priority,
            "target_type": notification.target_type,
            "target_id": (
                str(notification.target_id) if notification.target_id else None
            ),
            "is_read": notification.is_read,
            "created_at": fmt_dt(notification.created_at),
        }
        for notification in (
            db.query(Notification)
            .filter(Notification.user_id == admin.id)
            .order_by(Notification.created_at.desc())
            .limit(6)
            .all()
        )
    ]

    pending_actions = [
        {
            "key": "payments",
            "label": "Confirm payments",
            "count": pending_payments + overdue,
            "priority": "critical" if overdue else "warning",
            "route": "/cargo/sea-bookings?payment=due",
        },
        {
            "key": "holds",
            "label": "Review held goods",
            "count": held,
            "priority": "critical" if held else "normal",
            "route": "/cargo/sea-bookings?status=held",
        },
        {
            "key": "collections",
            "label": "Goods ready for pickup",
            "count": released_not_collected,
            "priority": "warning" if released_not_collected else "normal",
            "route": "/cargo/sea-bookings?status=released",
        },
        {
            "key": "air",
            "label": "Air cargo needs processing",
            "count": pending_air_bookings,
            "priority": "warning" if pending_air_bookings else "normal",
            "route": "/cargo/express-air-cargo",
        },
        {
            "key": "shipments",
            "label": "Shipment orders need updates",
            "count": shipment_orders_needing_update,
            "priority": "warning" if shipment_orders_needing_update else "normal",
            "route": "/cargo/shipment-orders",
        },
    ]

    pending_invoices = (
        db.query(SeaBookingInvoice)
        .join(
            SeaBooking,
            SeaBookingInvoice.sea_booking_id == SeaBooking.id,
        )
        .join(Container, SeaBooking.container_id == Container.id)
        .filter(
            Container.admin_id == admin.id,
            SeaBookingInvoice.status.in_(["draft", "sent"]),
        )
        .count()
    )
    paid_invoices = (
        db.query(SeaBookingInvoice)
        .join(
            SeaBooking,
            SeaBookingInvoice.sea_booking_id == SeaBooking.id,
        )
        .join(Container, SeaBooking.container_id == Container.id)
        .filter(
            Container.admin_id == admin.id,
            SeaBookingInvoice.status == "paid",
        )
        .count()
    )
    receipts_issued = (
        db.query(Receipt)
        .join(
            SeaBooking,
            Receipt.sea_booking_id == SeaBooking.id,
        )
        .join(Container, SeaBooking.container_id == Container.id)
        .filter(Container.admin_id == admin.id, Receipt.status == "issued")
        .count()
    )
    packing_lists_in_progress = (
        db.query(SeaBookingPackingList)
        .join(
            SeaBooking,
            SeaBookingPackingList.sea_booking_id == SeaBooking.id,
        )
        .join(Container, SeaBooking.container_id == Container.id)
        .filter(
            Container.admin_id == admin.id,
            SeaBookingPackingList.status.in_(["draft", "in_progress"]),
        )
        .count()
    )
    containers_near_full = (
        db.query(Container)
        .filter(
            Container.admin_id == admin.id,
            Container.max_cbm > 0,
            (Container.booked_cbm / Container.max_cbm) >= 0.85,
            Container.status.in_(["open", "nearly_full"]),
        )
        .count()
    )

    return {
        "total_containers": total_containers,
        "active_containers": active,
        "total_sea_bookings": total_sea_bookings,
        "total_booked_cbm": float(total_booked_cbm),
        "overdue_payments": overdue,
        "held_goods": held,
        "goods_held": held,
        "pending_payments": pending_payments,
        "released_not_collected": released_not_collected,
        "pending_air_bookings": pending_air_bookings,
        "air_in_transit": air_in_transit,
        "shipment_orders_needing_update": shipment_orders_needing_update,
        "pending_invoices": pending_invoices,
        "paid_invoices": paid_invoices,
        "receipts_issued": receipts_issued,
        "packing_lists_in_progress": packing_lists_in_progress,
        "containers_near_full": containers_near_full,
        "unread_notifications": unread_notifications,
        "container_status_counts": container_status_counts,
        "pending_actions": pending_actions,
        "recent_sea_bookings": recent_sea_bookings,
        "recent_air_bookings": recent_air_bookings,
        "recent_shipment_orders": recent_shipment_orders,
        "recent_comments": recent_comments,
        "notifications": notifications,
        "recent_activity": recent_activity,
    }


# ─── Express Air Cargo (Cargo Admin View) ────────────────


def _normalize_schedule_datetime(value: Optional[datetime]) -> Optional[datetime]:
    """Persist all schedule times as UTC-naive values, matching existing models."""
    if value is None or value.tzinfo is None:
        return value
    return value.astimezone(timezone.utc).replace(tzinfo=None)


def _decode_recurrence_weekdays(value: Optional[str]) -> List[int]:
    if not value:
        return []
    try:
        return sorted({int(day) for day in value.split(",") if day.strip()})
    except ValueError:
        return []


def _encode_recurrence_weekdays(value: Optional[List[int]]) -> Optional[str]:
    if not value:
        return None
    return ",".join(str(day) for day in sorted(set(value)))


def _validate_air_departure_schedule(schedule: AirDepartureSchedule) -> None:
    if (
        schedule.booking_cutoff_at
        and schedule.booking_cutoff_at > schedule.departure_at
    ):
        raise HTTPException(
            status_code=422,
            detail="Booking cutoff must be on or before the departure time.",
        )
    if schedule.available_capacity_kg is not None and schedule.capacity_kg is None:
        raise HTTPException(
            status_code=422,
            detail="Set the total capacity before setting available capacity.",
        )
    if (
        schedule.capacity_kg is not None
        and schedule.available_capacity_kg is not None
        and schedule.available_capacity_kg > schedule.capacity_kg
    ):
        raise HTTPException(
            status_code=422,
            detail="Available capacity cannot exceed total capacity.",
        )
    if schedule.recurrence_frequency == "weekly" and not _decode_recurrence_weekdays(
        schedule.recurrence_weekdays
    ):
        raise HTTPException(
            status_code=422,
            detail="Choose at least one weekday for a weekly departure schedule.",
        )
    if schedule.recurrence_frequency is None and schedule.recurrence_weekdays:
        raise HTTPException(
            status_code=422,
            detail="Choose a recurrence frequency before selecting recurrence weekdays.",
        )
    if schedule.recurrence_until and schedule.recurrence_until < schedule.departure_at:
        raise HTTPException(
            status_code=422,
            detail="The recurrence end date cannot be before the first departure.",
        )


def _serialize_air_departure_schedule(schedule: AirDepartureSchedule) -> dict:
    return {
        "id": str(schedule.id),
        "route_label": schedule.route_label,
        "service_label": schedule.service_label,
        "departure_at": schedule.departure_at.isoformat(),
        "booking_cutoff_at": (
            schedule.booking_cutoff_at.isoformat()
            if schedule.booking_cutoff_at
            else None
        ),
        "recurrence_frequency": schedule.recurrence_frequency,
        "recurrence_weekdays": _decode_recurrence_weekdays(
            schedule.recurrence_weekdays
        ),
        "recurrence_until": (
            schedule.recurrence_until.isoformat() if schedule.recurrence_until else None
        ),
        "capacity_kg": (
            float(schedule.capacity_kg) if schedule.capacity_kg is not None else None
        ),
        "available_capacity_kg": (
            float(schedule.available_capacity_kg)
            if schedule.available_capacity_kg is not None
            else None
        ),
        "status": schedule.status,
        "notes": schedule.notes,
        "created_at": schedule.created_at.isoformat() if schedule.created_at else None,
        "updated_at": schedule.updated_at.isoformat() if schedule.updated_at else None,
    }


@router.get("/air-departure-schedules")
def list_air_departure_schedules(
    db: Session = Depends(get_db),
    admin: User = Depends(get_cargo_admin),
):
    """List schedules belonging only to the signed-in cargo administrator."""
    schedules = (
        db.query(AirDepartureSchedule)
        .filter(AirDepartureSchedule.cargo_admin_id == admin.id)
        .order_by(AirDepartureSchedule.departure_at.asc())
        .all()
    )
    return [_serialize_air_departure_schedule(schedule) for schedule in schedules]


@router.post("/air-departure-schedules", status_code=201)
def create_air_departure_schedule(
    body: AirDepartureScheduleCreate,
    db: Session = Depends(get_db),
    admin: User = Depends(get_cargo_admin),
):
    """Publish an operational departure schedule for this cargo admin only."""
    schedule = AirDepartureSchedule(
        cargo_admin_id=admin.id,
        route_label=body.route_label,
        service_label=body.service_label,
        departure_at=_normalize_schedule_datetime(body.departure_at),
        booking_cutoff_at=_normalize_schedule_datetime(body.booking_cutoff_at),
        recurrence_frequency=body.recurrence_frequency,
        recurrence_weekdays=_encode_recurrence_weekdays(body.recurrence_weekdays),
        recurrence_until=_normalize_schedule_datetime(body.recurrence_until),
        capacity_kg=body.capacity_kg,
        available_capacity_kg=body.available_capacity_kg,
        status=body.status,
        notes=body.notes.strip() if body.notes and body.notes.strip() else None,
    )
    _validate_air_departure_schedule(schedule)
    db.add(schedule)
    log_action(
        db=db,
        action="AIR_DEPARTURE_SCHEDULE_CREATED",
        user_id=admin.id,
        entity_type="air_departure_schedule",
        entity_id=schedule.id,
    )
    db.commit()
    db.refresh(schedule)
    return _serialize_air_departure_schedule(schedule)


@router.patch("/air-departure-schedules/{schedule_id}")
def update_air_departure_schedule(
    schedule_id: str,
    body: AirDepartureScheduleUpdate,
    db: Session = Depends(get_db),
    admin: User = Depends(get_cargo_admin),
):
    try:
        schedule_uuid = UUID(schedule_id)
    except ValueError:
        raise HTTPException(status_code=404, detail="Departure schedule not found.")

    schedule = (
        db.query(AirDepartureSchedule)
        .filter(
            AirDepartureSchedule.id == schedule_uuid,
            AirDepartureSchedule.cargo_admin_id == admin.id,
        )
        .first()
    )
    if not schedule:
        raise HTTPException(status_code=404, detail="Departure schedule not found.")

    changes = body.model_dump(exclude_unset=True)
    for field in ("departure_at", "booking_cutoff_at"):
        if field in changes:
            changes[field] = _normalize_schedule_datetime(changes[field])
    if "recurrence_until" in changes:
        changes["recurrence_until"] = _normalize_schedule_datetime(
            changes["recurrence_until"]
        )
    if "recurrence_weekdays" in changes:
        changes["recurrence_weekdays"] = _encode_recurrence_weekdays(
            changes["recurrence_weekdays"]
        )
    if "notes" in changes:
        changes["notes"] = (
            changes["notes"].strip()
            if changes["notes"] and changes["notes"].strip()
            else None
        )
    for field, value in changes.items():
        setattr(schedule, field, value)
    _validate_air_departure_schedule(schedule)

    log_action(
        db=db,
        action="AIR_DEPARTURE_SCHEDULE_UPDATED",
        user_id=admin.id,
        entity_type="air_departure_schedule",
        entity_id=schedule.id,
        metadata={"fields": sorted(changes)},
    )
    db.commit()
    db.refresh(schedule)
    return _serialize_air_departure_schedule(schedule)


@router.get("/express-air-cargo/bookings")
def list_express_air_cargo_bookings(
    status: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    admin: User = Depends(get_cargo_admin),
):
    """View all express air cargo bookings (operator overview)."""
    query = (
        db.query(ExpressAirCargoBooking)
        .options(
            joinedload(ExpressAirCargoBooking.customer),
            joinedload(ExpressAirCargoBooking.cargo_type),
            joinedload(ExpressAirCargoBooking.shipping_mark),
        )
        .filter(
            ExpressAirCargoBooking.cargo_admin_id == admin.id
        )  # Added security filter
        .order_by(ExpressAirCargoBooking.created_at.desc())
    )

    if status:
        query = query.filter(ExpressAirCargoBooking.status == status)

    bookings = query.all()

    return [
        {
            "booking_id": str(b.id),
            "tracking_number": b.tracking_number,
            "status": b.status,
            "weight_kg": float(b.weight_kg),
            "shipment_date": b.shipment_date,
            "created_at": b.created_at,
            "route_label": b.route_label,
            "service_label": b.service_label,
            "cargo_type": {
                "id": str(b.cargo_type.id) if b.cargo_type else None,
                "name": b.cargo_type.name if b.cargo_type else None,
            },
            "customer": {
                "id": str(b.customer.id) if b.customer else None,
                "name": b.customer.name if b.customer else None,
                "phone_number": b.customer.phone_number if b.customer else None,
            },
            "shipping_mark": {
                "code": b.shipping_mark.shipping_mark_code if b.shipping_mark else None,
                "destination_region": (
                    b.shipping_mark.destination_region if b.shipping_mark else None
                ),
                "carton_count": (
                    b.shipping_mark.carton_count if b.shipping_mark else None
                ),
            },
            "item_photos": parse_photos(b.photo_urls),
        }
        for b in bookings
    ]


@router.get("/public/warehouses/cargo-admin/{admin_id}/air-cargo")
def get_air_cargo_warehouse_by_admin(
    admin_id: str,
    db: Session = Depends(get_db),
):
    """
    Get air cargo warehouse for a specific cargo admin
    Returns the first warehouse with type 'air' or 'both'
    """
    try:
        # Validate UUID format
        admin_uuid = UUID(admin_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid admin ID format")

    warehouse = (
        db.query(Warehouse)
        .filter(
            Warehouse.admin_id == admin_uuid,
            Warehouse.warehouse_type.in_(["air", "both"]),
        )
        .order_by(Warehouse.created_at)
        .first()
    )

    if not warehouse:
        raise HTTPException(status_code=404, detail="Air cargo warehouse not found")

    # Public callers may discover that a service exists, but never receive a
    # supplier-ready address or China warehouse contact. Authenticated booking
    # flows resolve and return the personalized address instead.
    return {
        "name": warehouse.name,
        "city": warehouse.city,
        "country": warehouse.country,
        "warehouse_type": warehouse.warehouse_type,
        "address_available_after_booking": True,
    }


@router.get("/express-air-cargo/{booking_id}/shipping-label")
def get_express_air_cargo_label_admin(
    booking_id: str,
    db: Session = Depends(get_db),
    admin: User = Depends(get_cargo_admin),
):
    """Cargo admin: view printable shipping label data for express air cargo."""
    booking = (
        db.query(ExpressAirCargoBooking)
        .options(
            joinedload(ExpressAirCargoBooking.customer),
            joinedload(ExpressAirCargoBooking.cargo_type),
            joinedload(ExpressAirCargoBooking.shipping_mark),
        )
        .filter(
            ExpressAirCargoBooking.id == booking_id,
            ExpressAirCargoBooking.cargo_admin_id == admin.id,
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
            customer_name=booking.customer.name if booking.customer else None,
            customer_phone=booking.customer.phone_number if booking.customer else None,
            destination_region="Unknown",
            packing_list_summary=booking.cargo_description,
            carton_count=1,
            air_booking_id=booking.id,
        )
        db.commit()
        db.refresh(booking)

    company = operator_document_branding(db, admin.id)
    label = build_printable_label(mark, company["name"])
    photos = []
    if booking.photo_urls:
        try:
            photos = json.loads(booking.photo_urls)
            if not isinstance(photos, list):
                photos = []
        except Exception:
            photos = []

    # Get warehouse information for the current cargo admin (air cargo specific)
    warehouse = (
        db.query(Warehouse)
        .filter(
            Warehouse.admin_id == admin.id,
            Warehouse.warehouse_type.in_(["air", "both"]),
        )
        .order_by(Warehouse.created_at)
        .first()
    )

    warehouse_info = None
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
            "full_address": warehouse_full_address(warehouse),
            "warehouse_type": warehouse.warehouse_type,
        }

    return {
        "company": company,
        "booking": {
            "booking_id": str(booking.id),
            "tracking_number": booking.tracking_number,
            "status": booking.status,
            "shipment_date": booking.shipment_date,
            "weight_kg": float(booking.weight_kg),
            "route_label": booking.route_label,
            "service_label": booking.service_label,
            "cargo_type": {
                "id": str(booking.cargo_type_id),
                "name": booking.cargo_type.name if booking.cargo_type else None,
            },
        },
        "customer": {
            "name": booking.customer.name if booking.customer else None,
            "phone_number": booking.customer.phone_number if booking.customer else None,
        },
        "label": label,
        "item_photos": photos,
        "warehouse": warehouse_info,
    }


@router.patch("/express-air-cargo/{booking_id}/shipping-label")
def update_express_air_cargo_label_admin(
    booking_id: str,
    body: ShippingLabelUpdateRequest,
    db: Session = Depends(get_db),
    admin: User = Depends(get_cargo_admin),
):
    """Cargo admin: update shipping label fields for express air cargo."""
    booking = (
        db.query(ExpressAirCargoBooking)
        .options(joinedload(ExpressAirCargoBooking.shipping_mark))
        .filter(
            ExpressAirCargoBooking.id == booking_id,
            ExpressAirCargoBooking.cargo_admin_id == admin.id,
        )
        .first()
    )
    if not booking or not booking.shipping_mark:
        raise HTTPException(status_code=404, detail="Shipping label not found")

    if body.customer_name is not None:
        booking.shipping_mark.customer_name = body.customer_name
    if body.customer_phone is not None:
        booking.shipping_mark.customer_phone = body.customer_phone
    if body.destination_region is not None:
        booking.shipping_mark.destination_region = body.destination_region
    if body.packing_list_summary is not None:
        booking.shipping_mark.packing_list_summary = body.packing_list_summary
    if body.carton_count is not None:
        booking.shipping_mark.carton_count = body.carton_count

    db.commit()
    db.refresh(booking)

    return {
        "booking_id": str(booking.id),
        "tracking_number": booking.tracking_number,
        "status": booking.status,
        "shipment_date": booking.shipment_date,
        "weight_kg": float(booking.weight_kg),
        "route_label": booking.route_label,
        "service_label": booking.service_label,
        "cargo_type": {
            "id": str(booking.cargo_type_id),
            "name": booking.cargo_type.name if booking.cargo_type else None,
        },
        "customer": {
            "name": booking.customer.name if booking.customer else None,
            "phone_number": booking.customer.phone_number if booking.customer else None,
        },
        "label": build_printable_label(booking.shipping_mark),
        "item_photos": parse_photos(booking.photo_urls),
    }


@router.patch("/express-air-cargo/{booking_id}/status")
def update_express_air_cargo_status(
    booking_id: str,
    body: AirCargoBookingStatusUpdate,
    db: Session = Depends(get_db),
    admin: User = Depends(get_cargo_admin),
):
    """Cargo admin: progress express air cargo bookings through operations lifecycle."""
    booking = (
        db.query(ExpressAirCargoBooking)
        .filter(
            ExpressAirCargoBooking.id == booking_id,
            ExpressAirCargoBooking.cargo_admin_id == admin.id,
        )
        .first()
    )
    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found")

    next_status = (body.status or "").strip().lower()
    allowed_statuses = {
        "pending",
        "confirmed",
        "label_created",
        "in_transit",
        "delivered",
        "cancelled",
    }
    if next_status not in allowed_statuses:
        raise HTTPException(
            status_code=400,
            detail=(
                "Invalid status. Allowed values: "
                "pending, confirmed, label_created, in_transit, delivered, cancelled"
            ),
        )

    if booking.status == next_status:
        return {"message": f"Booking already in status '{next_status}'"}

    valid_transitions = {
        "pending": {"confirmed", "cancelled"},
        "confirmed": {"label_created", "in_transit", "cancelled"},
        "label_created": {"in_transit", "cancelled"},
        "in_transit": {"delivered"},
        "delivered": set(),
        "cancelled": set(),
    }
    if next_status not in valid_transitions.get(booking.status, set()):
        raise HTTPException(
            status_code=400,
            detail=f"Invalid transition: {booking.status} -> {next_status}",
        )

    previous_status = booking.status
    booking.status = next_status

    # Keep linked shipment orders in sync when cargo is fully received.
    if next_status == "delivered":
        linked_orders = (
            db.query(ShipmentOrder)
            .filter(ShipmentOrder.air_booking_id == booking.id)
            .all()
        )
        for order in linked_orders:
            if order.status != ShipmentOrderStatus.received_at_warehouse:
                old_order_status = order.status
                order.status = ShipmentOrderStatus.received_at_warehouse
                TrackingService.create_tracking_event(
                    db=db,
                    entity_type="shipment_order",
                    entity_id=str(order.id),
                    event_type="shipment_order_status_updated",
                    description=(
                        "Shipment order updated automatically after air cargo delivery "
                        f"from {old_order_status} to {order.status}"
                    ),
                    triggered_by=str(admin.id),
                    extra_data={
                        "old_status": str(old_order_status),
                        "new_status": str(order.status),
                        "source": "air_booking_delivery_sync",
                        "air_booking_id": str(booking.id),
                    },
                )

    status_label = next_status.replace("_", " ")
    reason_suffix = (
        f" Reason: {body.reason.strip()}" if body.reason and body.reason.strip() else ""
    )

    TrackingService.create_tracking_event(
        db=db,
        entity_type="booking",
        entity_id=str(booking.id),
        event_type="booking_status_updated",
        description=(
            f"Express air cargo booking status updated from "
            f"{previous_status.replace('_', ' ')} to {status_label}.{reason_suffix}"
        ),
        triggered_by=str(admin.id),
        extra_data={
            "old_status": previous_status,
            "new_status": next_status,
            "reason": body.reason,
        },
    )

    log_action(
        db=db,
        action=f"AIR_BOOKING_STATUS_{previous_status.upper()}_TO_{next_status.upper()}",
        user_id=admin.id,
        entity_type="express_air_booking",
        entity_id=booking.id,
        reason=body.reason,
        metadata={
            "old_status": previous_status,
            "new_status": next_status,
        },
    )

    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        # Most common cause: DB check constraint not migrated to include label_created.
        if "chk_express_booking_status" in str(exc):
            raise HTTPException(
                status_code=409,
                detail=(
                    "Database schema is outdated for air cargo statuses. "
                    "Please run migrations (alembic upgrade head) and retry."
                ),
            )
        raise
    db.refresh(booking)

    return {
        "message": f"Booking status updated to {next_status}",
        "booking_id": str(booking.id),
        "old_status": previous_status,
        "new_status": booking.status,
    }


# ─── Container Lifecycle ───────────────────────────────


@router.post("/containers/{container_id}/depart")
def mark_container_departed(
    container_id: str,
    db: Session = Depends(get_db),
    admin: User = Depends(get_cargo_admin),
):
    container = _get_container_for_admin(db, container_id, admin.id)

    if container.status not in ["full", "nearly_full"]:
        raise HTTPException(
            status_code=400,
            detail=(
                "Container must be full or nearly full to depart, current "
                f"status: {container.status}"
            ),
        )

    container.status = "in_transit"
    container.departure_date = container.departure_date or datetime.utcnow()

    # NEW: Create tracking event for container departure
    TrackingService.create_tracking_event(
        db,
        entity_type="container",
        entity_id=str(container.id),
        event_type="container_departed",
        description="Container departed from origin",
        triggered_by=str(admin.id),
        extra_data={
            "departure_date": (
                container.departure_date.isoformat()
                if container.departure_date
                else None
            )
        },
    )

    # NEW: Create tracking events for all sea_bookings in this container
    sea_bookings = (
        db.query(SeaBooking).filter(SeaBooking.container_id == container.id).all()
    )

    for sea_booking in sea_bookings:
        TrackingService.create_tracking_event(
            db,
            entity_type="sea_booking",
            entity_id=str(sea_booking.id),
            event_type="container_departed",
            description="Sea booking shipment departed with container",
            triggered_by=str(admin.id),
            extra_data={
                "container_id": str(container.id),
                "departure_date": (
                    container.departure_date.isoformat()
                    if container.departure_date
                    else None
                ),
            },
        )

    log_action(
        db=db,
        action="CONTAINER_DEPARTED",
        user_id=admin.id,
        entity_type="container",
        entity_id=container.id,
    )

    db.commit()
    db.refresh(container)

    return {
        "message": "Container marked as departed",
        "container": _container_detail(container),
    }


@router.post("/containers/{container_id}/arrive")
def mark_container_arrived(
    container_id: str,
    db: Session = Depends(get_db),
    admin: User = Depends(get_cargo_admin),
):
    container = _get_container_for_admin(db, container_id, admin.id)

    if container.status != "in_transit":
        raise HTTPException(
            status_code=400,
            detail=(
                "Container must be in transit to arrive, current status: "
                f"{container.status}"
            ),
        )

    container.status = "arrived"
    container.arrival_date = container.arrival_date or datetime.utcnow()

    # NEW: Create tracking event for container arrival
    TrackingService.create_tracking_event(
        db,
        entity_type="container",
        entity_id=str(container.id),
        event_type="container_arrived",
        description="Container arrived at destination",
        triggered_by=str(admin.id),
        extra_data={
            "arrival_date": (
                container.arrival_date.isoformat() if container.arrival_date else None
            )
        },
    )

    # NEW: Create tracking events for all sea_bookings in this container
    sea_bookings = (
        db.query(SeaBooking).filter(SeaBooking.container_id == container.id).all()
    )

    for sea_booking in sea_bookings:
        # Update payment status to due upon arrival
        if sea_booking.payment_status == "pending":
            sea_booking.payment_status = "due"
            # NEW: Create tracking event for payment due
            TrackingService.create_tracking_event(
                db,
                entity_type="sea_booking",
                entity_id=str(sea_booking.id),
                event_type="payment_due",
                description="Payment due for sea booking after container arrival",
                triggered_by=str(admin.id),
                extra_data={
                    "amount_due": float(sea_booking.logistics_charge),
                    "container_id": str(container.id),
                },
            )

        TrackingService.create_tracking_event(
            db,
            entity_type="sea_booking",
            entity_id=str(sea_booking.id),
            event_type="container_arrived",
            description="Sea booking shipment arrived with container",
            triggered_by=str(admin.id),
            extra_data={
                "container_id": str(container.id),
                "arrival_date": (
                    container.arrival_date.isoformat()
                    if container.arrival_date
                    else None
                ),
            },
        )

    log_action(
        db=db,
        action="CONTAINER_ARRIVED",
        user_id=admin.id,
        entity_type="container",
        entity_id=container.id,
    )

    db.commit()
    db.refresh(container)

    return {
        "message": "Container marked as arrived",
        "container": _container_detail(container),
    }


# ─── Helpers ─────────────────────────────────────────────


def _get_sea_booking_for_admin(
    db: Session, sea_booking_id: str, admin_id
) -> SeaBooking:
    sea_booking = (
        db.query(SeaBooking)
        .join(Container, SeaBooking.container_id == Container.id)
        .filter(
            SeaBooking.id == sea_booking_id,
            Container.admin_id == admin_id,
        )
        .first()
    )
    if not sea_booking:
        raise HTTPException(status_code=404, detail="Sea booking not found")
    return sea_booking


def _get_container_for_admin(db: Session, container_id: str, admin_id) -> Container:
    container = (
        db.query(Container)
        .filter(Container.id == container_id, Container.admin_id == admin_id)
        .first()
    )
    if not container:
        raise HTTPException(status_code=404, detail="Container not found")
    return container


def _get_or_create_sea_booking_shipping_mark(
    db: Session, sea_booking: SeaBooking
) -> tuple[ShippingMark, bool]:
    existing = (
        db.query(ShippingMark)
        .filter(ShippingMark.sea_booking_id == sea_booking.id)
        .first()
    )
    if existing:
        return existing, False

    destination_region = "Destination"
    if sea_booking.container and sea_booking.container.route:
        route_destination = sea_booking.container.route.destination
        if route_destination and route_destination.strip():
            destination_region = route_destination.strip()
    elif (
        sea_booking.container
        and sea_booking.container.destination_warehouse
        and sea_booking.container.destination_warehouse.name
    ):
        destination_region = sea_booking.container.destination_warehouse.name.strip()

    mark = create_shipping_mark(
        db,
        booking_id=sea_booking.id,
        cargo_type="SEA",
        customer_name=sea_booking.user.name if sea_booking.user else None,
        customer_phone=sea_booking.user.phone_number if sea_booking.user else None,
        destination_region=destination_region,
        packing_list_summary=(f"Booked CBM: {float(sea_booking.cbm_booked or 0):.2f}"),
        carton_count=1,
        sea_booking_id=sea_booking.id,
    )
    return mark, True


def _container_detail(container: Container) -> dict:
    return {
        "id": str(container.id),
        "reference": build_display_reference(
            "container", container.id, container.created_at
        ),
        "status": container.status,
        "container_size": container.container_size,
        "max_cbm": float(container.max_cbm) if container.max_cbm else 0.0,
        "booked_cbm": (float(container.booked_cbm) if container.booked_cbm else 0.0),
        "available_cbm": container.available_cbm,
        "fill_percentage": container.fill_percentage,
        "is_archived": bool(container.is_archived),
        "archived_at": (
            container.archived_at.isoformat() if container.archived_at else None
        ),
        "price_per_cbm": (
            float(container.price_per_cbm) if container.price_per_cbm else 0.0
        ),
        "currency": container.currency,
        "departure_date": (
            container.departure_date.isoformat() if container.departure_date else None
        ),
        "estimated_arrival_date": (
            container.estimated_arrival_date.isoformat()
            if container.estimated_arrival_date
            else None
        ),
        "arrival_date": (
            container.arrival_date.isoformat() if container.arrival_date else None
        ),
    }


def _actor_label(user: User) -> str:
    role_map = {
        "cargo_admin": "Cargo Admin",
        "super_admin": "Super Admin",
        "customer": "Customer",
        "sourcing_agent": "Sourcing Agent",
    }
    return role_map.get(user.role, "User")


def _notify_sea_booking_user(
    db: Session,
    sea_booking: SeaBooking,
    notification_type: str,
    message: str,
    priority: str = "info",
    target_type: Optional[str] = None,
    target_id=None,
):
    if not sea_booking.user_id:
        return
    create_notification(
        db=db,
        user_id=sea_booking.user_id,
        notification_type=notification_type,
        message=message,
        priority=priority,
        target_type=target_type,
        target_id=target_id,
    )


def _stream_cloudinary_document(document_url: str, filename: str) -> StreamingResponse:
    return stream_safe_document(document_url, filename)


def _get_sea_booking_packing_fill_snapshot(
    db: Session, sea_booking: SeaBooking
) -> dict:
    packing_lists = (
        db.query(SeaBookingPackingList)
        .filter(SeaBookingPackingList.sea_booking_id == sea_booking.id)
        .all()
    )
    packing_list_ids = [pl.id for pl in packing_lists]
    items = []
    if packing_list_ids:
        items = (
            db.query(SeaBookingPackingListItem)
            .filter(SeaBookingPackingListItem.packing_list_id.in_(packing_list_ids))
            .all()
        )

    total_cartons = int(sum(int(item.cartons or 0) for item in items))
    total_cbm = float(sum(float(item.cbm or 0) for item in items))
    total_weight_kg = float(sum(float(item.weight_kg or 0) for item in items))
    received_cbm = float(
        sum(
            float(item.cbm or 0)
            for item in items
            if item.status in {"received", "inspected", "packed", "loaded", "completed"}
        )
    )
    loaded_cbm = float(
        sum(
            float(item.cbm or 0)
            for item in items
            if item.status in {"loaded", "completed"}
        )
    )
    sea_booking_target_cbm = float(sea_booking.cbm_booked or 0)
    sea_booking_fill = (
        round((loaded_cbm / sea_booking_target_cbm) * 100, 2)
        if sea_booking_target_cbm > 0
        else 0.0
    )

    container = sea_booking.container
    container_loaded_cbm = float(
        db.query(func.coalesce(func.sum(SeaBookingPackingList.loaded_cbm), 0))
        .filter(SeaBookingPackingList.container_id == container.id)
        .scalar()
        or 0
    )
    container_max_cbm = float(container.max_cbm or 0)
    container_remaining_cbm = max(container_max_cbm - container_loaded_cbm, 0)
    container_fill = (
        round((container_loaded_cbm / container_max_cbm) * 100, 2)
        if container_max_cbm > 0
        else 0.0
    )

    return {
        "total_cartons": total_cartons,
        "total_cbm": total_cbm,
        "total_weight_kg": total_weight_kg,
        "received_cbm": received_cbm,
        "loaded_cbm": loaded_cbm,
        "sea_booking_target_cbm": sea_booking_target_cbm,
        "sea_booking_fill_percentage": sea_booking_fill,
        "container_loaded_cbm": container_loaded_cbm,
        "container_max_cbm": container_max_cbm,
        "container_remaining_cbm": container_remaining_cbm,
        "container_fill_percentage": container_fill,
    }


def _sync_packing_list_totals(db: Session, packing_list: SeaBookingPackingList):
    items = (
        db.query(SeaBookingPackingListItem)
        .filter(SeaBookingPackingListItem.packing_list_id == packing_list.id)
        .all()
    )
    packing_list.total_cartons = int(sum(int(item.cartons or 0) for item in items))
    packing_list.total_cbm = float(sum(float(item.cbm or 0) for item in items))
    packing_list.total_weight_kg = float(
        sum(float(item.weight_kg or 0) for item in items)
    )
    packing_list.received_cbm = float(
        sum(
            float(item.cbm or 0)
            for item in items
            if item.status in {"received", "inspected", "packed", "loaded", "completed"}
        )
    )
    packing_list.loaded_cbm = float(
        sum(
            float(item.cbm or 0)
            for item in items
            if item.status in {"loaded", "completed"}
        )
    )
    db.flush()


def _generate_receipt(db: Session, sea_booking_id=None, order_id=None):
    import secrets
    import uuid

    existing = None
    if sea_booking_id:
        existing = (
            db.query(Receipt)
            .filter(Receipt.sea_booking_id == sea_booking_id)
            .order_by(Receipt.generated_at.desc())
            .first()
        )
    elif order_id:
        existing = (
            db.query(Receipt)
            .filter(Receipt.order_id == order_id)
            .order_by(Receipt.generated_at.desc())
            .first()
        )
    if existing:
        if sea_booking_id and (existing.currency is None or existing.amount is None):
            sea_booking = (
                db.query(SeaBooking)
                .options(joinedload(SeaBooking.container))
                .filter(SeaBooking.id == sea_booking_id)
                .first()
            )
            if not sea_booking:
                raise ValueError("Sea booking not found while updating receipt")
            if existing.currency is None:
                existing.currency = snapshot_sea_booking_currency(db, sea_booking)
            if existing.amount is None:
                existing.amount = sea_booking.logistics_charge or 0
            db.flush()
        return existing

    receipt_number = (
        f"RCP-{datetime.utcnow().strftime('%Y%m%d')}-{str(uuid.uuid4())[:8].upper()}"
    )
    receipt_token = secrets.token_urlsafe(32)

    amount = None
    currency = None
    if sea_booking_id:
        sea_booking = (
            db.query(SeaBooking)
            .options(joinedload(SeaBooking.container))
            .filter(SeaBooking.id == sea_booking_id)
            .first()
        )
        if not sea_booking:
            raise ValueError("Sea booking not found while generating receipt")
        currency = snapshot_sea_booking_currency(db, sea_booking)
        amount = sea_booking.logistics_charge or 0

    receipt = Receipt(
        sea_booking_id=sea_booking_id,
        order_id=order_id,
        receipt_number=receipt_number,
        receipt_token=receipt_token,
        amount=amount,
        currency=currency,
    )
    db.add(receipt)
    db.flush()
    return receipt


@router.get("/activity-feed")
def get_admin_activity_feed(
    entity_type: str = Query(
        "all", description="all, container, sea_booking, booking, shipment_order"
    ),
    cursor_ts: Optional[str] = Query(
        None, description="Pagination cursor timestamp (ISO8601)"
    ),
    cursor_id: Optional[str] = Query(None, description="Pagination cursor event UUID"),
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_cargo_admin),
):
    allowed_entity_types = {
        "all",
        "container",
        "sea_booking",
        "booking",
        "shipment_order",
    }
    selected_entity_type = (entity_type or "all").strip().lower()
    if selected_entity_type not in allowed_entity_types:
        raise HTTPException(status_code=400, detail="Invalid entity_type filter")

    container_ids_q = db.query(Container.id).filter(
        Container.admin_id == current_user.id
    )
    sea_booking_ids_q = (
        db.query(SeaBooking.id)
        .join(Container, SeaBooking.container_id == Container.id)
        .filter(Container.admin_id == current_user.id)
    )
    booking_ids_q = db.query(ExpressAirCargoBooking.id).filter(
        ExpressAirCargoBooking.cargo_admin_id == current_user.id
    )
    shipment_order_ids_q = db.query(ShipmentOrder.id).filter(
        or_(
            ShipmentOrder.sea_booking_id.in_(sea_booking_ids_q),
            ShipmentOrder.air_booking_id.in_(booking_ids_q),
        )
    )

    event_scopes = {
        "container": (
            (TrackingEvent.entity_type == "container")
            & TrackingEvent.entity_id.in_(container_ids_q)
        ),
        "sea_booking": (
            (TrackingEvent.entity_type == "sea_booking")
            & TrackingEvent.entity_id.in_(sea_booking_ids_q)
        ),
        "booking": (
            (TrackingEvent.entity_type == "booking")
            & TrackingEvent.entity_id.in_(booking_ids_q)
        ),
        "shipment_order": (
            (TrackingEvent.entity_type == "shipment_order")
            & TrackingEvent.entity_id.in_(shipment_order_ids_q)
        ),
    }
    scope_filters = (
        [event_scopes[selected_entity_type]]
        if selected_entity_type != "all"
        else list(event_scopes.values())
    )

    query = db.query(TrackingEvent).filter(or_(*scope_filters))

    if cursor_ts:
        try:
            ts = datetime.fromisoformat(cursor_ts.replace("Z", "+00:00"))
        except ValueError as exc:
            raise HTTPException(
                status_code=400, detail="Invalid cursor_ts format"
            ) from exc

        if cursor_id:
            try:
                cursor_uuid = UUID(cursor_id)
            except ValueError as exc:
                raise HTTPException(
                    status_code=400, detail="Invalid cursor_id format"
                ) from exc
            query = query.filter(
                or_(
                    TrackingEvent.timestamp < ts,
                    and_(TrackingEvent.timestamp == ts, TrackingEvent.id < cursor_uuid),
                )
            )
        else:
            query = query.filter(TrackingEvent.timestamp < ts)

    rows = (
        query.order_by(TrackingEvent.timestamp.desc(), TrackingEvent.id.desc())
        .limit(limit + 1)
        .all()
    )
    has_more = len(rows) > limit
    rows = rows[:limit]

    next_cursor_ts = None
    next_cursor_id = None
    if has_more and rows:
        last_row = rows[-1]
        next_cursor_ts = last_row.timestamp.isoformat() if last_row.timestamp else None
        next_cursor_id = str(last_row.id)

    return {
        "items": [
            {
                "id": str(event.id),
                "entity_type": event.entity_type,
                "entity_id": str(event.entity_id),
                "event_type": event.event_type,
                "description": event.description,
                "created_at": event.timestamp.isoformat() if event.timestamp else None,
                "reference": (event.extra_data or {}).get("display_reference"),
            }
            for event in rows
        ],
        "limit": limit,
        "has_more": has_more,
        "next_cursor_ts": next_cursor_ts,
        "next_cursor_id": next_cursor_id,
    }


@router.get("/notifications")
def get_admin_notifications(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_cargo_admin),
):
    """Get all notifications for the current admin user."""
    notifications = (
        db.query(Notification)
        .filter(Notification.user_id == current_user.id)
        .order_by(Notification.created_at.desc())
        .limit(50)
        .all()
    )

    unread_count = (
        db.query(Notification)
        .filter(
            Notification.user_id == current_user.id,
            Notification.is_read.is_(False),
        )
        .count()
    )

    return {
        "notifications": [
            {
                "id": str(n.id),
                "type": n.type,
                "message": n.message,
                "is_read": n.is_read,
                "target_type": n.target_type,
                "target_id": str(n.target_id) if n.target_id else None,
                "created_at": n.created_at.isoformat(),
            }
            for n in notifications
        ],
        "unread_count": unread_count,
    }
