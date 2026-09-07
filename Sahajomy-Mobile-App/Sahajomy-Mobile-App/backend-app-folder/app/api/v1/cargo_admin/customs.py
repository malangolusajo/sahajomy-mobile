"""Cargo-admin CRM customers and customs packing-list endpoints."""

import json
import os
import tempfile
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from typing import Any, Literal, Optional

from app.core.audit import log_action
from app.core.cloudinary import upload_to_cloudinary
from app.core.config import settings
from app.core.dependencies import get_cargo_admin
from app.core.upload_validation import validated_image_format
from app.database import get_db
from app.models.air_cargo import ExpressAirCargoBooking
from app.models.cargo_customs import (
    CargoCustomer,
    CargoCustomerAddress,
    CargoCustomerContact,
    CustomsPackingList,
    CustomsPackingListItem,
    ManualCargoIntake,
    ManualCargoIntakeItem,
)
from app.models.container import Container, SeaBooking, Warehouse
from app.models.finance import SeaBookingPackingList, SeaBookingPackingListItem
from app.models.user import User
from app.services.cargo_intake_calculations import (
    DEFAULT_AIR_VOLUMETRIC_DIVISOR,
    freight_calculation,
    intake_totals,
    item_measurements,
)
from app.services.document_branding import operator_document_branding
from app.services.document_generation_service import DocumentGenerationService
from app.services.manual_cargo_tracking import create_manual_intake_tracking_event
from app.services.subscriptions import company_for_operator
from app.services.tracking_number import ensure_manual_intake_tracking_number
from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field, field_validator
from sqlalchemy import func, or_
from sqlalchemy.orm import Session, joinedload

router = APIRouter(tags=["Cargo Admin Customers & Customs Packing Lists"])

OPTIONAL_COLUMNS = {
    "hs_code",
    "sku",
    "brand",
    "model",
    "country_of_origin",
    "po_number",
    "unit",
    "net_weight",
    "unit_price",
    "total_value",
    "currency",
    "color",
    "size",
    "material",
    "batch_number",
    "serial_number",
}
CUSTOM_FIELD_TYPES = {"text", "number", "decimal", "date", "dropdown", "boolean"}
FALLBACK_ITEM_PHOTO_URL = "fallback://packing-item-photo"


class ContactInput(BaseModel):
    full_name: str = Field(min_length=1, max_length=160)
    role: Optional[str] = None
    phone: Optional[str] = None
    whatsapp: Optional[str] = None
    email: Optional[str] = None
    notes: Optional[str] = None
    is_primary: bool = False


class AddressInput(BaseModel):
    label: str = "Address"
    contact_person: Optional[str] = None
    phone: Optional[str] = None
    country: Optional[str] = None
    city: Optional[str] = None
    region: Optional[str] = None
    full_address: Optional[str] = None
    postal_code: Optional[str] = None
    notes: Optional[str] = None
    is_default_shipping: bool = False
    is_default_billing: bool = False


class CustomerInput(BaseModel):
    customer_type: Literal["individual", "company"] = "individual"
    name: str = Field(min_length=1, max_length=200)
    primary_contact_name: Optional[str] = None
    phone: Optional[str] = None
    whatsapp: Optional[str] = None
    email: Optional[str] = None
    country: Optional[str] = None
    city: Optional[str] = None
    region: Optional[str] = None
    full_address: Optional[str] = None
    tax_id: Optional[str] = None
    company_registration_number: Optional[str] = None
    preferred_cargo_type: Optional[Literal["sea", "air", "both"]] = None
    preferred_destination_port: Optional[str] = None
    preferred_destination_airport: Optional[str] = None
    notes: Optional[str] = None
    tags: list[str] = Field(default_factory=list)
    contacts: list[ContactInput] = Field(default_factory=list)
    addresses: list[AddressInput] = Field(default_factory=list)


class CustomerUpdate(CustomerInput):
    status: Literal["active", "inactive"] = "active"


class PackingItemInput(BaseModel):
    item_name: str = Field(min_length=1, max_length=200)
    item_description: str = Field(min_length=1, max_length=500)
    item_photo_url: Optional[str] = Field(default=None, max_length=2000)
    carton_count: int = Field(gt=0)
    qty_per_carton: Decimal = Field(ge=0)
    length_cm: Decimal = Field(ge=0)
    width_cm: Decimal = Field(ge=0)
    height_cm: Decimal = Field(ge=0)
    cbm_per_carton: Optional[Decimal] = Field(default=None, ge=0)
    gross_weight_per_carton_kg: Decimal = Field(ge=0)
    net_weight_per_carton_kg: Optional[Decimal] = Field(default=None, ge=0)
    remarks: Optional[str] = None
    optional_values: dict[str, Any] = Field(default_factory=dict)
    custom_values: dict[str, Any] = Field(default_factory=dict)


class CustomsPackingListInput(BaseModel):
    cargo_type: Literal["sea", "air"]
    customer_id: Optional[str] = None
    consignee_customer_id: Optional[str] = None
    warehouse_id: Optional[str] = None
    container_id: Optional[str] = None
    sea_booking_id: Optional[str] = None
    air_booking_id: Optional[str] = None
    origin_address: dict[str, Any] = Field(default_factory=dict)
    shipper_snapshot: dict[str, Any] = Field(default_factory=dict)
    consignee_snapshot: dict[str, Any] = Field(default_factory=dict)
    notify_party: dict[str, Any] = Field(default_factory=dict)
    shipment_references: dict[str, Any] = Field(default_factory=dict)
    optional_columns: list[str] = Field(default_factory=list)
    custom_columns: list[dict[str, Any]] = Field(default_factory=list)
    notes: Optional[str] = None
    items: list[PackingItemInput] = Field(default_factory=list)


class ManualCargoItemInput(BaseModel):
    item_name: str = Field(min_length=1, max_length=200)
    item_description: str = Field(min_length=1, max_length=500)
    item_photo_url: Optional[str] = Field(default=None, max_length=2000)
    carton_count: int = Field(gt=0)
    qty_per_carton: Decimal = Field(default=Decimal("0"), ge=0)
    length_cm: Decimal = Field(default=Decimal("0"), ge=0)
    width_cm: Decimal = Field(default=Decimal("0"), ge=0)
    height_cm: Decimal = Field(default=Decimal("0"), ge=0)
    cbm_per_carton: Optional[Decimal] = Field(default=None, ge=0)
    gross_weight_per_carton_kg: Optional[Decimal] = Field(default=None, ge=0)
    total_gross_weight_kg: Optional[Decimal] = Field(default=None, ge=0)
    charge_basis: Literal["cbm", "metric_ton", "flat", "custom", "kg"] = "cbm"
    rate_amount: Decimal = Field(default=Decimal("0"), ge=0)
    rate_currency: Literal["TZS", "RMB", "USD"] = "USD"
    custom_shipping_charge: Optional[Decimal] = Field(default=None, ge=0)
    hs_code: Optional[str] = Field(default=None, max_length=80)
    brand: Optional[str] = Field(default=None, max_length=120)
    model: Optional[str] = Field(default=None, max_length=120)
    country_of_origin: Optional[str] = Field(default=None, max_length=120)
    sku: Optional[str] = Field(default=None, max_length=120)
    remarks: Optional[str] = None

    @field_validator(
        "item_photo_url",
        "cbm_per_carton",
        "gross_weight_per_carton_kg",
        "total_gross_weight_kg",
        "custom_shipping_charge",
        "hs_code",
        "brand",
        "model",
        "country_of_origin",
        "sku",
        "remarks",
        mode="before",
    )
    @classmethod
    def blank_optional_values_are_null(cls, value):
        """Treat browser form blanks as absent optional values.

        HTML inputs submit an empty string, while Pydantic cannot coerce an
        empty string to Decimal.  Normalising it here keeps direct API clients
        and older frontend bundles from receiving an opaque 422 response.
        """
        return None if isinstance(value, str) and not value.strip() else value


class ManualCargoIntakeInput(BaseModel):
    customer_id: str = Field(min_length=1)
    warehouse_id: str = Field(min_length=1)
    cargo_type: Literal["sea", "air"]
    destination_country: Optional[str] = None
    destination_city: Optional[str] = None
    consignee_address: Optional[str] = None
    supplier_name: Optional[str] = None
    supplier_contact: Optional[str] = None
    external_tracking_number: Optional[str] = Field(default=None, max_length=100)
    received_at: Optional[datetime] = None
    # Legacy receipt-level rate fields are accepted for older clients. Item
    # fields are authoritative for all new and edited intakes.
    charge_basis: Literal["cbm", "metric_ton", "flat", "custom", "kg"] = "cbm"
    rate_amount: Decimal = Field(default=Decimal("0"), ge=0)
    rate_currency: Literal["TZS", "RMB", "USD"] = "USD"
    custom_shipping_charge: Optional[Decimal] = Field(default=None, ge=0)
    container_id: Optional[str] = None
    sea_booking_id: Optional[str] = None
    air_booking_id: Optional[str] = None
    notes: Optional[str] = None
    items: list[ManualCargoItemInput] = Field(default_factory=list)

    @field_validator(
        "destination_country",
        "destination_city",
        "consignee_address",
        "supplier_name",
        "supplier_contact",
        "external_tracking_number",
        "custom_shipping_charge",
        "container_id",
        "sea_booking_id",
        "air_booking_id",
        "notes",
        mode="before",
    )
    @classmethod
    def blank_optional_values_are_null(cls, value):
        return None if isinstance(value, str) and not value.strip() else value


def _as_decimal(value: Any) -> Decimal:
    try:
        return Decimal(str(value or 0))
    except (InvalidOperation, ValueError) as exc:
        raise HTTPException(status_code=422, detail="Invalid decimal value") from exc


def _next_reference(db: Session, model, column, prefix: str) -> str:
    # Human-friendly references are independent of UUIDs. Keep incrementing in
    # case a legacy document was deleted and left a gap in the sequence.
    count = db.query(func.count(model.id)).scalar() or 0
    sequence = int(count) + 1
    while db.query(model).filter(column == f"{prefix}{sequence:06d}").first():
        sequence += 1
    return f"{prefix}{sequence:06d}"


def _customer_or_404(db: Session, admin: User, customer_id: str) -> CargoCustomer:
    customer = (
        db.query(CargoCustomer)
        .filter(
            CargoCustomer.id == customer_id, CargoCustomer.cargo_admin_id == admin.id
        )
        .first()
    )
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")
    return customer


def _set_defaults(db: Session, customer_id, address: CargoCustomerAddress) -> None:
    if address.is_default_shipping:
        db.query(CargoCustomerAddress).filter(
            CargoCustomerAddress.customer_id == customer_id,
            CargoCustomerAddress.id != address.id,
        ).update({"is_default_shipping": False}, synchronize_session=False)
    if address.is_default_billing:
        db.query(CargoCustomerAddress).filter(
            CargoCustomerAddress.customer_id == customer_id,
            CargoCustomerAddress.id != address.id,
        ).update({"is_default_billing": False}, synchronize_session=False)


def _set_primary_contact(
    db: Session, customer_id, contact: CargoCustomerContact
) -> None:
    if contact.is_primary:
        db.query(CargoCustomerContact).filter(
            CargoCustomerContact.customer_id == customer_id,
            CargoCustomerContact.id != contact.id,
        ).update({"is_primary": False}, synchronize_session=False)


def _serialize_contact(contact: CargoCustomerContact) -> dict:
    return {
        "id": str(contact.id),
        "full_name": contact.full_name,
        "role": contact.role,
        "phone": contact.phone,
        "whatsapp": contact.whatsapp,
        "email": contact.email,
        "notes": contact.notes,
        "is_primary": contact.is_primary,
        "is_active": contact.is_active,
    }


def _serialize_address(address: CargoCustomerAddress) -> dict:
    return {
        "id": str(address.id),
        "label": address.label,
        "contact_person": address.contact_person,
        "phone": address.phone,
        "country": address.country,
        "city": address.city,
        "region": address.region,
        "full_address": address.full_address,
        "postal_code": address.postal_code,
        "notes": address.notes,
        "is_default_shipping": address.is_default_shipping,
        "is_default_billing": address.is_default_billing,
        "is_active": address.is_active,
    }


def _serialize_customer(customer: CargoCustomer, include_related: bool = False) -> dict:
    data = {
        "id": str(customer.id),
        "customer_reference": customer.customer_reference,
        "customer_type": customer.customer_type,
        "name": customer.name,
        "primary_contact_name": customer.primary_contact_name,
        "phone": customer.phone,
        "whatsapp": customer.whatsapp,
        "email": customer.email,
        "country": customer.country,
        "city": customer.city,
        "region": customer.region,
        "full_address": customer.full_address,
        "tax_id": customer.tax_id,
        "company_registration_number": customer.company_registration_number,
        "preferred_cargo_type": customer.preferred_cargo_type,
        "preferred_destination_port": customer.preferred_destination_port,
        "preferred_destination_airport": customer.preferred_destination_airport,
        "notes": customer.notes,
        "tags": customer.tags or [],
        "status": customer.status,
        "created_at": customer.created_at.isoformat() if customer.created_at else None,
    }
    if include_related:
        data["contacts"] = [
            _serialize_contact(row) for row in customer.contacts if row.is_active
        ]
        data["addresses"] = [
            _serialize_address(row) for row in customer.addresses if row.is_active
        ]
    return data


def _possible_duplicates(
    db: Session, admin: User, body: CustomerInput
) -> list[CargoCustomer]:
    tokens = [
        value.strip()
        for value in [
            body.phone,
            body.whatsapp,
            body.email,
            body.tax_id,
            body.company_registration_number,
        ]
        if value and value.strip()
    ]
    predicates = [CargoCustomer.name.ilike(body.name.strip())]
    for token in tokens:
        predicates.extend(
            [
                CargoCustomer.phone.ilike(token),
                CargoCustomer.whatsapp.ilike(token),
                CargoCustomer.email.ilike(token),
                CargoCustomer.tax_id.ilike(token),
                CargoCustomer.company_registration_number.ilike(token),
            ]
        )
    return (
        db.query(CargoCustomer)
        .filter(CargoCustomer.cargo_admin_id == admin.id, or_(*predicates))
        .limit(10)
        .all()
    )


@router.post("/packing-list-item-photo")
async def upload_packing_list_item_photo(
    file: UploadFile = File(...),
    admin: User = Depends(get_cargo_admin),
    db: Session = Depends(get_db),
):
    """Upload an admin-entered item photo once and retain its Cloudinary URL."""
    if file.content_type not in set(settings.ALLOWED_IMAGE_TYPES) | {"image/gif"}:
        raise HTTPException(
            status_code=400, detail="Invalid item photo. Use JPEG, PNG, GIF, or WebP."
        )
    content = await file.read()
    if len(content) > settings.MAX_IMAGE_SIZE_MB * 1024 * 1024:
        raise HTTPException(
            status_code=400,
            detail=f"Item photo is too large. Maximum size is {settings.MAX_IMAGE_SIZE_MB}MB.",
        )
    _, extension = validated_image_format(content, file.content_type, allow_gif=True)
    with tempfile.NamedTemporaryFile(delete=False, suffix=f".{extension}") as temporary:
        temporary.write(content)
        path = temporary.name
    try:
        company = company_for_operator(db, admin.id)
        image_url = upload_to_cloudinary(
            file=path,
            folder="cargo_packing_items",
            resource_type="image",
            db_session=db if company else None,
            company_id=company.id if company else None,
            uploaded_by_id=admin.id,
            asset_kind="cargo_packing_item_photo",
        )
        if not image_url:
            raise HTTPException(
                status_code=502, detail="Item photo upload did not return an image URL"
            )
        db.commit()
        return {"image_url": image_url}
    finally:
        os.unlink(path)


@router.get("/customers")
def list_customers(
    search: Optional[str] = None,
    status: Optional[Literal["active", "inactive"]] = None,
    db: Session = Depends(get_db),
    admin: User = Depends(get_cargo_admin),
):
    query = db.query(CargoCustomer).filter(CargoCustomer.cargo_admin_id == admin.id)
    if status:
        query = query.filter(CargoCustomer.status == status)
    if search and search.strip():
        token = f"%{search.strip()}%"
        query = query.filter(
            or_(
                CargoCustomer.customer_reference.ilike(token),
                CargoCustomer.name.ilike(token),
                CargoCustomer.primary_contact_name.ilike(token),
                CargoCustomer.phone.ilike(token),
                CargoCustomer.whatsapp.ilike(token),
                CargoCustomer.email.ilike(token),
                CargoCustomer.country.ilike(token),
                CargoCustomer.city.ilike(token),
                CargoCustomer.tax_id.ilike(token),
            )
        )
    rows = query.order_by(CargoCustomer.created_at.desc()).all()
    return {"customers": [_serialize_customer(row) for row in rows]}


@router.post("/customers/duplicates")
def check_customer_duplicates(
    body: CustomerInput,
    db: Session = Depends(get_db),
    admin: User = Depends(get_cargo_admin),
):
    return {
        "matches": [
            _serialize_customer(row) for row in _possible_duplicates(db, admin, body)
        ]
    }


@router.post("/customers")
def create_customer(
    body: CustomerInput,
    db: Session = Depends(get_db),
    admin: User = Depends(get_cargo_admin),
):
    customer = CargoCustomer(
        cargo_admin_id=admin.id,
        customer_reference=_next_reference(
            db, CargoCustomer, CargoCustomer.customer_reference, "CUS-"
        ),
        **body.model_dump(exclude={"contacts", "addresses"}),
    )
    db.add(customer)
    db.flush()
    for contact_input in body.contacts:
        contact = CargoCustomerContact(
            customer_id=customer.id, **contact_input.model_dump()
        )
        db.add(contact)
        db.flush()
        _set_primary_contact(db, customer.id, contact)
    for address_input in body.addresses:
        address = CargoCustomerAddress(
            customer_id=customer.id, **address_input.model_dump()
        )
        db.add(address)
        db.flush()
        _set_defaults(db, customer.id, address)
    log_action(
        db,
        "cargo_customer_created",
        admin.id,
        "cargo_customer",
        customer.id,
        {"customer_reference": customer.customer_reference},
    )
    db.commit()
    db.refresh(customer)
    return {
        "customer": _serialize_customer(customer, include_related=True),
        "possible_duplicates": [
            _serialize_customer(row)
            for row in _possible_duplicates(db, admin, body)
            if row.id != customer.id
        ],
    }


@router.get("/customers/{customer_id}")
def get_customer(
    customer_id: str,
    db: Session = Depends(get_db),
    admin: User = Depends(get_cargo_admin),
):
    customer = _customer_or_404(db, admin, customer_id)
    data = _serialize_customer(customer, include_related=True)
    if customer.linked_user_id:
        sea = (
            db.query(SeaBooking)
            .join(Container)
            .filter(
                SeaBooking.user_id == customer.linked_user_id,
                Container.admin_id == admin.id,
            )
        )
        air = db.query(ExpressAirCargoBooking).filter(
            ExpressAirCargoBooking.customer_id == customer.linked_user_id,
            ExpressAirCargoBooking.cargo_admin_id == admin.id,
        )
        data["shipment_summary"] = {
            "sea_shipments": sea.count(),
            "air_shipments": air.count(),
            "total_cbm": float(
                sum((_as_decimal(row.cbm_booked) for row in sea.all()), Decimal("0"))
            ),
            "total_weight_kg": float(
                sum((_as_decimal(row.weight_kg) for row in air.all()), Decimal("0"))
            ),
        }
    else:
        data["shipment_summary"] = {
            "sea_shipments": 0,
            "air_shipments": 0,
            "total_cbm": 0,
            "total_weight_kg": 0,
        }
    data["packing_lists"] = [
        _serialize_packing_list(row)
        for row in db.query(CustomsPackingList)
        .filter(
            CustomsPackingList.cargo_admin_id == admin.id,
            CustomsPackingList.customer_id == customer.id,
        )
        .order_by(CustomsPackingList.created_at.desc())
        .all()
    ]
    return data


@router.patch("/customers/{customer_id}")
def update_customer(
    customer_id: str,
    body: CustomerUpdate,
    db: Session = Depends(get_db),
    admin: User = Depends(get_cargo_admin),
):
    customer = _customer_or_404(db, admin, customer_id)
    for key, value in body.model_dump(exclude={"contacts", "addresses"}).items():
        setattr(customer, key, value)
    log_action(db, "cargo_customer_updated", admin.id, "cargo_customer", customer.id)
    db.commit()
    db.refresh(customer)
    return {"customer": _serialize_customer(customer, include_related=True)}


@router.post("/customers/{customer_id}/deactivate")
def deactivate_customer(
    customer_id: str,
    db: Session = Depends(get_db),
    admin: User = Depends(get_cargo_admin),
):
    customer = _customer_or_404(db, admin, customer_id)
    customer.status = "inactive"
    log_action(
        db, "cargo_customer_deactivated", admin.id, "cargo_customer", customer.id
    )
    db.commit()
    return {"message": "Customer deactivated"}


@router.post("/customers/{customer_id}/contacts")
def add_customer_contact(
    customer_id: str,
    body: ContactInput,
    db: Session = Depends(get_db),
    admin: User = Depends(get_cargo_admin),
):
    customer = _customer_or_404(db, admin, customer_id)
    contact = CargoCustomerContact(customer_id=customer.id, **body.model_dump())
    db.add(contact)
    db.flush()
    _set_primary_contact(db, customer.id, contact)
    log_action(
        db, "cargo_customer_contact_added", admin.id, "cargo_customer", customer.id
    )
    db.commit()
    return _serialize_contact(contact)


@router.patch("/customers/{customer_id}/contacts/{contact_id}")
def update_customer_contact(
    customer_id: str,
    contact_id: str,
    body: ContactInput,
    db: Session = Depends(get_db),
    admin: User = Depends(get_cargo_admin),
):
    customer = _customer_or_404(db, admin, customer_id)
    contact = (
        db.query(CargoCustomerContact)
        .filter(
            CargoCustomerContact.id == contact_id,
            CargoCustomerContact.customer_id == customer.id,
        )
        .first()
    )
    if not contact:
        raise HTTPException(status_code=404, detail="Contact not found")
    for key, value in body.model_dump().items():
        setattr(contact, key, value)
    _set_primary_contact(db, customer.id, contact)
    db.commit()
    return _serialize_contact(contact)


@router.delete("/customers/{customer_id}/contacts/{contact_id}")
def deactivate_customer_contact(
    customer_id: str,
    contact_id: str,
    db: Session = Depends(get_db),
    admin: User = Depends(get_cargo_admin),
):
    customer = _customer_or_404(db, admin, customer_id)
    contact = (
        db.query(CargoCustomerContact)
        .filter(
            CargoCustomerContact.id == contact_id,
            CargoCustomerContact.customer_id == customer.id,
        )
        .first()
    )
    if not contact:
        raise HTTPException(status_code=404, detail="Contact not found")
    contact.is_active = False
    db.commit()
    return {"message": "Contact deactivated"}


@router.post("/customers/{customer_id}/addresses")
def add_customer_address(
    customer_id: str,
    body: AddressInput,
    db: Session = Depends(get_db),
    admin: User = Depends(get_cargo_admin),
):
    customer = _customer_or_404(db, admin, customer_id)
    address = CargoCustomerAddress(customer_id=customer.id, **body.model_dump())
    db.add(address)
    db.flush()
    _set_defaults(db, customer.id, address)
    log_action(
        db, "cargo_customer_address_added", admin.id, "cargo_customer", customer.id
    )
    db.commit()
    return _serialize_address(address)


@router.patch("/customers/{customer_id}/addresses/{address_id}")
def update_customer_address(
    customer_id: str,
    address_id: str,
    body: AddressInput,
    db: Session = Depends(get_db),
    admin: User = Depends(get_cargo_admin),
):
    customer = _customer_or_404(db, admin, customer_id)
    address = (
        db.query(CargoCustomerAddress)
        .filter(
            CargoCustomerAddress.id == address_id,
            CargoCustomerAddress.customer_id == customer.id,
        )
        .first()
    )
    if not address:
        raise HTTPException(status_code=404, detail="Address not found")
    for key, value in body.model_dump().items():
        setattr(address, key, value)
    _set_defaults(db, customer.id, address)
    db.commit()
    return _serialize_address(address)


def _validate_custom_columns(columns: list[dict[str, Any]]) -> list[dict[str, Any]]:
    validated = []
    for column in columns:
        name = str(column.get("name") or "").strip()
        field_type = str(column.get("type") or "text").strip().lower()
        if not name or field_type not in CUSTOM_FIELD_TYPES:
            raise HTTPException(
                status_code=422,
                detail="Each custom column requires a name and valid type",
            )
        options = column.get("options") or []
        if field_type == "dropdown" and not isinstance(options, list):
            raise HTTPException(
                status_code=422, detail="Dropdown options must be a list"
            )
        validated.append({"name": name, "type": field_type, "options": options})
    return validated


def _packing_or_404(
    db: Session, admin: User, packing_list_id: str
) -> CustomsPackingList:
    row = (
        db.query(CustomsPackingList)
        .options(joinedload(CustomsPackingList.items))
        .filter(
            CustomsPackingList.id == packing_list_id,
            CustomsPackingList.cargo_admin_id == admin.id,
        )
        .first()
    )
    if not row:
        raise HTTPException(status_code=404, detail="Customs packing list not found")
    return row


def _customer_snapshot(customer: Optional[CargoCustomer]) -> dict:
    if not customer:
        return {}
    address = next(
        (
            row
            for row in customer.addresses
            if row.is_active and row.is_default_shipping
        ),
        None,
    ) or next((row for row in customer.addresses if row.is_active), None)
    return {
        "name": customer.name,
        "contact_person": customer.primary_contact_name,
        "phone": customer.phone,
        "whatsapp": customer.whatsapp,
        "email": customer.email,
        "tax_id": customer.tax_id,
        "address": (
            _serialize_address(address)
            if address
            else {
                "country": customer.country,
                "city": customer.city,
                "region": customer.region,
                "full_address": customer.full_address,
            }
        ),
    }


def _warehouse_snapshot(warehouse: Optional[Warehouse]) -> dict:
    if not warehouse:
        return {}
    return {
        "name": warehouse.name,
        "country": warehouse.country,
        "city": warehouse.city,
        "region": warehouse.state,
        "full_address": warehouse.address or warehouse.location,
        "phone": warehouse.contact_phone_1,
        "contact_person": warehouse.contact_name_1,
    }


def _air_booking_destination(booking: ExpressAirCargoBooking) -> Optional[str]:
    """Use the actual air-booking route/label fields; no destination column exists."""
    if booking.shipping_mark and booking.shipping_mark.destination_region:
        return booking.shipping_mark.destination_region
    route = str(booking.route_label or "")
    if "→" in route:
        return route.split("→", 1)[1].strip() or None
    if "->" in route:
        return route.split("->", 1)[1].strip() or None
    return None


def _apply_item(
    item: CustomsPackingListItem,
    body: PackingItemInput,
    *,
    divisor: Decimal = Decimal("6000"),
) -> None:
    values = body.model_dump()
    values["item_photo_url"] = (
        str(values.get("item_photo_url") or "").strip() or FALLBACK_ITEM_PHOTO_URL
    )
    for key, value in values.items():
        setattr(item, key, value)
    cartons = Decimal(item.carton_count)
    item.total_quantity = cartons * _as_decimal(item.qty_per_carton)
    direct_cbm = values.get("cbm_per_carton")
    item.cbm_source = "direct" if direct_cbm is not None else "dimensions"
    item.cbm_per_carton = (
        _as_decimal(direct_cbm)
        if direct_cbm is not None
        else (
            _as_decimal(item.length_cm)
            * _as_decimal(item.width_cm)
            * _as_decimal(item.height_cm)
        )
        / Decimal("1000000")
    )
    item.total_cbm = item.cbm_per_carton * cartons
    item.total_gross_weight_kg = _as_decimal(item.gross_weight_per_carton_kg) * cartons
    if item.net_weight_per_carton_kg is not None:
        item.total_net_weight_kg = _as_decimal(item.net_weight_per_carton_kg) * cartons
    else:
        item.total_net_weight_kg = None
    item.volumetric_weight_per_carton_kg = (
        _as_decimal(item.length_cm)
        * _as_decimal(item.width_cm)
        * _as_decimal(item.height_cm)
    ) / divisor
    item.total_volumetric_weight_kg = item.volumetric_weight_per_carton_kg * cartons


def _sync_totals(row: CustomsPackingList) -> None:
    items = row.items or []
    row.total_cartons = sum(int(item.carton_count or 0) for item in items)
    row.total_quantity = sum(
        (_as_decimal(item.total_quantity) for item in items), Decimal("0")
    )
    row.total_cbm = sum((_as_decimal(item.total_cbm) for item in items), Decimal("0"))
    row.total_gross_weight_kg = sum(
        (_as_decimal(item.total_gross_weight_kg) for item in items), Decimal("0")
    )
    net = [
        item.total_net_weight_kg
        for item in items
        if item.total_net_weight_kg is not None
    ]
    row.total_net_weight_kg = (
        sum((_as_decimal(value) for value in net), Decimal("0")) if net else None
    )
    if row.cargo_type == "air":
        row.total_volumetric_weight_kg = sum(
            (_as_decimal(item.total_volumetric_weight_kg) for item in items),
            Decimal("0"),
        )
        row.chargeable_weight_kg = max(
            _as_decimal(row.total_gross_weight_kg),
            _as_decimal(row.total_volumetric_weight_kg),
        )
    else:
        row.total_volumetric_weight_kg = None
        row.chargeable_weight_kg = None


def _source_item_inputs(db: Session, row: CustomsPackingList) -> list[PackingItemInput]:
    """Prefill only values that exist in the chosen operational source.

    The result is deliberately a draft. Measurements absent from the source are
    left as zero and the completion checker makes the cargo admin review them
    before a customs document can be finalized.
    """
    results: list[PackingItemInput] = []
    if row.air_booking:
        booking = row.air_booking
        photos = []
        try:
            photos = json.loads(booking.photo_urls or "[]")
        except (TypeError, ValueError, json.JSONDecodeError):
            photos = []
        carton_count = int(
            (booking.shipping_mark.carton_count if booking.shipping_mark else 0) or 0
        )
        if carton_count > 0:
            results.append(
                PackingItemInput(
                    item_name=(booking.cargo_description or "Air cargo item")[:200],
                    item_description=booking.cargo_description or "Air cargo item",
                    item_photo_url=next(
                        (photo for photo in photos if isinstance(photo, str) and photo),
                        None,
                    ),
                    carton_count=carton_count,
                    qty_per_carton=Decimal("0"),
                    length_cm=Decimal("0"),
                    width_cm=Decimal("0"),
                    height_cm=Decimal("0"),
                    gross_weight_per_carton_kg=_as_decimal(booking.weight_kg)
                    / Decimal(carton_count),
                    remarks="Prefilled from air booking. Confirm dimensions and quantity per carton.",
                )
            )
        return results

    sea_bookings = []
    if row.sea_booking:
        sea_bookings = [row.sea_booking]
    elif row.container:
        sea_bookings = (
            db.query(SeaBooking)
            .filter(SeaBooking.container_id == row.container.id)
            .all()
        )
    for sea_booking in sea_bookings:
        packing_lists = (
            db.query(SeaBookingPackingList)
            .filter(SeaBookingPackingList.sea_booking_id == sea_booking.id)
            .all()
        )
        packing_ids = [packing_list.id for packing_list in packing_lists]
        operational_items = (
            db.query(SeaBookingPackingListItem)
            .filter(SeaBookingPackingListItem.packing_list_id.in_(packing_ids))
            .all()
            if packing_ids
            else []
        )
        for source_item in operational_items:
            cartons = int(source_item.cartons or 0)
            if cartons <= 0:
                continue
            results.append(
                PackingItemInput(
                    item_name=source_item.item_name,
                    item_description=source_item.supplier_details
                    or source_item.item_name,
                    item_photo_url=None,
                    carton_count=cartons,
                    qty_per_carton=Decimal("0"),
                    length_cm=Decimal("0"),
                    width_cm=Decimal("0"),
                    height_cm=Decimal("0"),
                    gross_weight_per_carton_kg=_as_decimal(source_item.weight_kg)
                    / Decimal(cartons),
                    remarks="Prefilled from sea booking packing data. Confirm dimensions and quantity per carton.",
                )
            )
    return results


def _completion_issues(
    items: list[CustomsPackingListItem], source_type: str = "manual"
) -> list[str]:
    issues = []
    for position, item in enumerate(items, start=1):
        label = item.item_name or f"item {position}"
        if not item.item_name or not item.item_description:
            issues.append(f"{label}: Item Name and Item Description are required.")
        if source_type in {"manual", "manual_intake"} and (
            not item.item_photo_url or item.item_photo_url == FALLBACK_ITEM_PHOTO_URL
        ):
            issues.append(
                f"{label}: Item photo is required for manually entered cargo."
            )
        if item.cbm_source != "direct" and any(
            _as_decimal(getattr(item, field)) <= 0
            for field in ("length_cm", "width_cm", "height_cm")
        ):
            issues.append(
                f"{label}: enter CBM per Carton directly or provide all carton dimensions."
            )
    return issues


def _serialize_item(item: CustomsPackingListItem) -> dict:
    keys = [
        "qty_per_carton",
        "total_quantity",
        "length_cm",
        "width_cm",
        "height_cm",
        "cbm_per_carton",
        "total_cbm",
        "gross_weight_per_carton_kg",
        "total_gross_weight_kg",
        "net_weight_per_carton_kg",
        "total_net_weight_kg",
        "volumetric_weight_per_carton_kg",
        "total_volumetric_weight_kg",
    ]
    data = {
        "id": str(item.id),
        "item_name": item.item_name,
        "item_description": item.item_description,
        "item_photo_url": item.item_photo_url or FALLBACK_ITEM_PHOTO_URL,
        "uses_fallback_photo": not item.item_photo_url
        or item.item_photo_url == FALLBACK_ITEM_PHOTO_URL,
        "carton_count": item.carton_count,
        "cbm_source": item.cbm_source,
        "remarks": item.remarks,
        "optional_values": item.optional_values or {},
        "custom_values": item.custom_values or {},
    }
    data.update(
        {
            key: float(getattr(item, key)) if getattr(item, key) is not None else None
            for key in keys
        }
    )
    return data


def _serialize_packing_list(row: CustomsPackingList, detail: bool = False) -> dict:
    data = {
        "id": str(row.id),
        "packing_list_number": row.packing_list_number,
        "source_type": row.source_type,
        "cargo_type": row.cargo_type,
        "status": row.status,
        "customer_id": str(row.customer_id) if row.customer_id else None,
        "customer_name": (
            row.customer.name if row.customer else row.consignee_snapshot.get("name")
        ),
        "consignee_customer_id": (
            str(row.consignee_customer_id) if row.consignee_customer_id else None
        ),
        "issue_date": row.issue_date.isoformat() if row.issue_date else None,
        "total_cartons": row.total_cartons,
        "total_quantity": float(row.total_quantity or 0),
        "total_cbm": float(row.total_cbm or 0),
        "total_gross_weight_kg": float(row.total_gross_weight_kg or 0),
        "total_net_weight_kg": (
            float(row.total_net_weight_kg)
            if row.total_net_weight_kg is not None
            else None
        ),
        "total_volumetric_weight_kg": (
            float(row.total_volumetric_weight_kg)
            if row.total_volumetric_weight_kg is not None
            else None
        ),
        "chargeable_weight_kg": (
            float(row.chargeable_weight_kg)
            if row.chargeable_weight_kg is not None
            else None
        ),
        "created_at": row.created_at.isoformat() if row.created_at else None,
    }
    if detail:
        data.update(
            {
                "warehouse_id": str(row.warehouse_id) if row.warehouse_id else None,
                "container_id": str(row.container_id) if row.container_id else None,
                "sea_booking_id": (
                    str(row.sea_booking_id) if row.sea_booking_id else None
                ),
                "air_booking_id": (
                    str(row.air_booking_id) if row.air_booking_id else None
                ),
                "origin_address": row.origin_address or {},
                "shipper_snapshot": row.shipper_snapshot or {},
                "consignee_snapshot": row.consignee_snapshot or {},
                "notify_party": row.notify_party or {},
                "shipment_references": row.shipment_references or {},
                "optional_columns": row.optional_columns or [],
                "custom_columns": row.custom_columns or [],
                "notes": row.notes,
                "snapshot": row.snapshot if row.status == "finalized" else None,
                "items": [_serialize_item(item) for item in row.items or []],
                "completion_issues": _completion_issues(
                    row.items or [], row.source_type
                ),
            }
        )
    return data


def _apply_packing_fields(
    db: Session, admin: User, row: CustomsPackingList, body: CustomsPackingListInput
) -> None:
    if body.customer_id:
        row.customer = _customer_or_404(db, admin, body.customer_id)
    else:
        row.customer = None
    if body.consignee_customer_id:
        row.consignee_customer = _customer_or_404(db, admin, body.consignee_customer_id)
    else:
        row.consignee_customer = row.customer
    if body.warehouse_id:
        warehouse = (
            db.query(Warehouse)
            .filter(Warehouse.id == body.warehouse_id, Warehouse.admin_id == admin.id)
            .first()
        )
        if not warehouse:
            raise HTTPException(status_code=404, detail="Warehouse not found")
        row.warehouse = warehouse
    else:
        row.warehouse = None
    if body.container_id:
        container = (
            db.query(Container)
            .filter(Container.id == body.container_id, Container.admin_id == admin.id)
            .first()
        )
        if not container:
            raise HTTPException(status_code=404, detail="Container not found")
        row.container = container
    else:
        row.container = None
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
            raise HTTPException(status_code=404, detail="Sea booking not found")
        row.sea_booking = sea_booking
        row.container = sea_booking.container
    else:
        row.sea_booking = None
    if body.air_booking_id:
        booking = (
            db.query(ExpressAirCargoBooking)
            .filter(
                ExpressAirCargoBooking.id == body.air_booking_id,
                ExpressAirCargoBooking.cargo_admin_id == admin.id,
            )
            .first()
        )
        if not booking:
            raise HTTPException(status_code=404, detail="Air cargo booking not found")
        row.air_booking = booking
    else:
        row.air_booking = None
    if body.sea_booking_id and body.cargo_type != "sea":
        raise HTTPException(status_code=422, detail="A sea_booking requires Sea Cargo")
    if body.air_booking_id and body.cargo_type != "air":
        raise HTTPException(status_code=422, detail="An air booking requires Air Cargo")
    invalid = set(body.optional_columns) - OPTIONAL_COLUMNS
    if invalid:
        raise HTTPException(
            status_code=422,
            detail=f"Unsupported optional columns: {', '.join(sorted(invalid))}",
        )
    row.source_type = (
        "air_booking"
        if body.air_booking_id
        else (
            "sea_booking"
            if body.sea_booking_id
            else (
                "container"
                if body.container_id
                else "customer" if body.customer_id else "manual"
            )
        )
    )
    row.cargo_type = body.cargo_type
    row.origin_address = body.origin_address or _warehouse_snapshot(row.warehouse)
    row.shipper_snapshot = body.shipper_snapshot or {
        "name": admin.name or "Cargo Company"
    }
    row.consignee_snapshot = body.consignee_snapshot or _customer_snapshot(
        row.consignee_customer
    )
    row.notify_party = body.notify_party
    row.shipment_references = body.shipment_references
    row.optional_columns = body.optional_columns
    row.custom_columns = _validate_custom_columns(body.custom_columns)
    row.notes = body.notes


def _manual_intake_or_404(
    db: Session, admin: User, intake_id: str
) -> ManualCargoIntake:
    row = (
        db.query(ManualCargoIntake)
        .options(
            joinedload(ManualCargoIntake.items),
            joinedload(ManualCargoIntake.customer),
            joinedload(ManualCargoIntake.warehouse),
        )
        .filter(
            ManualCargoIntake.id == intake_id,
            ManualCargoIntake.cargo_admin_id == admin.id,
        )
        .first()
    )
    if not row:
        raise HTTPException(status_code=404, detail="Manual cargo intake not found")
    return row


def _manual_item_values(body: ManualCargoItemInput) -> dict:
    return body.model_dump()


def _validate_manual_item_rate(cargo_type: str, item: ManualCargoItemInput) -> None:
    if cargo_type == "air" and item.charge_basis != "kg":
        raise HTTPException(
            status_code=422,
            detail="Each Air Cargo item must use the Rate per kg charge basis",
        )
    if cargo_type == "sea" and item.charge_basis == "kg":
        raise HTTPException(
            status_code=422,
            detail="Sea Cargo items use CBM, Metric Ton, Flat Rate, or Custom charge basis",
        )


def _manual_item_with_legacy_rate(
    item: ManualCargoItemInput, body: ManualCargoIntakeInput
) -> ManualCargoItemInput:
    """Use receipt-level pricing only when an older client omitted item pricing."""
    fallback = {}
    for field in (
        "charge_basis",
        "rate_amount",
        "rate_currency",
        "custom_shipping_charge",
    ):
        if field not in item.model_fields_set:
            fallback[field] = getattr(body, field)
    return item.model_copy(update=fallback)


def _apply_manual_item(
    item: ManualCargoIntakeItem, body: ManualCargoItemInput, cargo_type: str
) -> None:
    _validate_manual_item_rate(cargo_type, body)
    values = _manual_item_values(body)
    calculated = item_measurements(values, DEFAULT_AIR_VOLUMETRIC_DIVISOR)
    for key, value in values.items():
        setattr(item, key, value)
    for key, value in calculated.items():
        setattr(item, key, value)
    item.cbm_source = (
        "direct" if values.get("cbm_per_carton") is not None else "dimensions"
    )
    totals = intake_totals([values], cargo_type, DEFAULT_AIR_VOLUMETRIC_DIVISOR)
    freight = freight_calculation(
        cargo_type, body.charge_basis, totals, body.rate_amount
    )
    item.calculated_billable_quantity = freight["billable_quantity"]
    item.calculated_shipping_charge = (
        body.custom_shipping_charge
        if body.charge_basis == "custom" and body.custom_shipping_charge is not None
        else freight["shipping_charge"]
    )


def _apply_manual_links(
    db: Session, admin: User, row: ManualCargoIntake, body: ManualCargoIntakeInput
) -> None:
    customer = _customer_or_404(db, admin, body.customer_id)
    warehouse = (
        db.query(Warehouse)
        .filter(Warehouse.id == body.warehouse_id, Warehouse.admin_id == admin.id)
        .first()
    )
    if not warehouse:
        raise HTTPException(status_code=404, detail="Warehouse not found")
    row.customer = customer
    row.warehouse = warehouse
    if body.container_id:
        container = (
            db.query(Container)
            .filter(Container.id == body.container_id, Container.admin_id == admin.id)
            .first()
        )
        if not container:
            raise HTTPException(status_code=404, detail="Container not found")
        row.container = container
    else:
        row.container = None
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
            raise HTTPException(status_code=404, detail="Sea booking not found")
        row.sea_booking = sea_booking
        row.container = sea_booking.container
    else:
        row.sea_booking = None
    if body.air_booking_id:
        booking = (
            db.query(ExpressAirCargoBooking)
            .filter(
                ExpressAirCargoBooking.id == body.air_booking_id,
                ExpressAirCargoBooking.cargo_admin_id == admin.id,
            )
            .first()
        )
        if not booking:
            raise HTTPException(status_code=404, detail="Air cargo booking not found")
        row.air_booking = booking
    else:
        row.air_booking = None
    if body.sea_booking_id and body.cargo_type != "sea":
        raise HTTPException(
            status_code=422, detail="A sea_booking can only be linked to Sea Cargo"
        )
    if body.air_booking_id and body.cargo_type != "air":
        raise HTTPException(
            status_code=422, detail="An air booking can only be linked to Air Cargo"
        )


def _sync_manual_intake(
    row: ManualCargoIntake, custom_shipping_charge: Optional[Decimal] = None
) -> None:
    source_items = [
        {
            "carton_count": item.carton_count,
            "qty_per_carton": item.qty_per_carton,
            "length_cm": item.length_cm,
            "width_cm": item.width_cm,
            "height_cm": item.height_cm,
            "cbm_per_carton": (
                item.cbm_per_carton if item.cbm_source == "direct" else None
            ),
            "gross_weight_per_carton_kg": item.gross_weight_per_carton_kg,
            "total_gross_weight_kg": item.total_gross_weight_kg,
        }
        for item in row.items or []
    ]
    totals = intake_totals(source_items, row.cargo_type, DEFAULT_AIR_VOLUMETRIC_DIVISOR)
    row.total_cartons = totals["total_cartons"]
    row.total_quantity = totals["total_quantity"]
    row.total_cbm = totals["total_cbm"]
    row.total_gross_weight_kg = totals["total_gross_weight_kg"]
    row.total_volumetric_weight_kg = totals["total_volumetric_weight_kg"]
    row.chargeable_weight_kg = totals["chargeable_weight_kg"]
    # Receipt-level amounts remain for legacy reporting. New intake items each
    # carry their own rate; their charges are summed only for backwards-compatible
    # reporting (use the item currency breakdown for mixed-currency intakes).
    row.calculated_billable_quantity = sum(
        (
            Decimal(str(item.calculated_billable_quantity or 0))
            for item in row.items or []
        ),
        Decimal("0"),
    )
    row.calculated_shipping_charge = sum(
        (
            Decimal(str(item.calculated_shipping_charge or 0))
            for item in row.items or []
        ),
        Decimal("0"),
    )


def _serialize_manual_item(item: ManualCargoIntakeItem) -> dict:
    keys = [
        "qty_per_carton",
        "total_quantity",
        "length_cm",
        "width_cm",
        "height_cm",
        "cbm_per_carton",
        "total_cbm",
        "gross_weight_per_carton_kg",
        "total_gross_weight_kg",
        "volumetric_weight_per_carton_kg",
        "total_volumetric_weight_kg",
        "rate_amount",
        "calculated_billable_quantity",
        "calculated_shipping_charge",
    ]
    data = {
        "id": str(item.id),
        "item_name": item.item_name,
        "item_description": item.item_description,
        "item_photo_url": item.item_photo_url or FALLBACK_ITEM_PHOTO_URL,
        "uses_fallback_photo": not item.item_photo_url,
        "carton_count": item.carton_count,
        "cbm_source": item.cbm_source,
        "charge_basis": item.charge_basis,
        "rate_currency": item.rate_currency,
        "hs_code": item.hs_code,
        "brand": item.brand,
        "model": item.model,
        "country_of_origin": item.country_of_origin,
        "sku": item.sku,
        "remarks": item.remarks,
    }
    data.update(
        {
            key: float(getattr(item, key)) if getattr(item, key) is not None else None
            for key in keys
        }
    )
    return data


def _serialize_manual_intake(row: ManualCargoIntake, detail: bool = False) -> dict:
    existing_packing = next(
        (
            packing
            for packing in getattr(row, "customs_packing_lists", [])
            if packing.cargo_admin_id == row.cargo_admin_id
        ),
        None,
    )
    data = {
        "id": str(row.id),
        "tracking_number": row.tracking_number,
        "external_tracking_number": row.external_tracking_number,
        "intake_number": row.intake_number,
        "customer_id": str(row.customer_id),
        "customer_name": row.customer.name if row.customer else None,
        "warehouse_id": str(row.warehouse_id),
        "warehouse_name": row.warehouse.name if row.warehouse else None,
        "cargo_type": row.cargo_type,
        "destination_country": row.destination_country,
        "destination_city": row.destination_city,
        "consignee_address": row.consignee_address,
        "supplier_name": row.supplier_name,
        "supplier_contact": row.supplier_contact,
        "received_at": row.received_at.isoformat() if row.received_at else None,
        "charge_basis": row.charge_basis,
        "rate_amount": float(row.rate_amount or 0),
        "rate_currency": row.rate_currency,
        "calculated_billable_quantity": float(row.calculated_billable_quantity or 0),
        "calculated_shipping_charge": float(row.calculated_shipping_charge or 0),
        "total_cartons": row.total_cartons,
        "total_quantity": float(row.total_quantity or 0),
        "total_cbm": float(row.total_cbm or 0),
        "total_gross_weight_kg": float(row.total_gross_weight_kg or 0),
        "total_volumetric_weight_kg": (
            float(row.total_volumetric_weight_kg)
            if row.total_volumetric_weight_kg is not None
            else None
        ),
        "chargeable_weight_kg": (
            float(row.chargeable_weight_kg)
            if row.chargeable_weight_kg is not None
            else None
        ),
        "status": row.status,
        "intake_method": row.intake_method,
        "carrier": row.carrier,
        "shipping_mark": row.shipping_mark,
        "payment_status": row.payment_status,
        "collection_status": row.collection_status,
        "collected_at": row.collected_at.isoformat() if row.collected_at else None,
        "packing_list_id": str(existing_packing.id) if existing_packing else None,
        "created_at": row.created_at.isoformat() if row.created_at else None,
    }
    if detail:
        data.update(
            {
                "container_id": str(row.container_id) if row.container_id else None,
                "sea_booking_id": (
                    str(row.sea_booking_id) if row.sea_booking_id else None
                ),
                "air_booking_id": (
                    str(row.air_booking_id) if row.air_booking_id else None
                ),
                "notes": row.notes,
                "items": [_serialize_manual_item(item) for item in row.items or []],
            }
        )
    return data


@router.get("/manual-cargo-intakes")
def list_manual_cargo_intakes(
    status: Optional[
        Literal["draft", "received", "ready_for_packing_list", "finalized", "cancelled"]
    ] = None,
    cargo_type: Optional[Literal["sea", "air"]] = None,
    search: Optional[str] = None,
    db: Session = Depends(get_db),
    admin: User = Depends(get_cargo_admin),
):
    query = (
        db.query(ManualCargoIntake)
        .options(
            joinedload(ManualCargoIntake.customer),
            joinedload(ManualCargoIntake.warehouse),
            joinedload(ManualCargoIntake.customs_packing_lists),
        )
        .filter(ManualCargoIntake.cargo_admin_id == admin.id)
    )
    if status:
        query = query.filter(ManualCargoIntake.status == status)
    if cargo_type:
        query = query.filter(ManualCargoIntake.cargo_type == cargo_type)
    if search and search.strip():
        token = f"%{search.strip()}%"
        query = query.join(CargoCustomer).filter(
            or_(
                ManualCargoIntake.intake_number.ilike(token),
                CargoCustomer.name.ilike(token),
            )
        )
    return {
        "intakes": [
            _serialize_manual_intake(row)
            for row in query.order_by(ManualCargoIntake.received_at.desc()).all()
        ]
    }


@router.post("/manual-cargo-intakes")
def create_manual_cargo_intake(
    body: ManualCargoIntakeInput,
    db: Session = Depends(get_db),
    admin: User = Depends(get_cargo_admin),
):
    if not body.items:
        raise HTTPException(
            status_code=422, detail="Add at least one received cargo item"
        )
    row = ManualCargoIntake(
        cargo_admin_id=admin.id,
        intake_number=_next_reference(
            db,
            ManualCargoIntake,
            ManualCargoIntake.intake_number,
            f"WRI-{date.today().year}-",
        ),
        cargo_type=body.cargo_type,
        charge_basis=body.items[0].charge_basis,
        rate_amount=body.items[0].rate_amount,
        rate_currency=body.items[0].rate_currency,
        received_at=body.received_at or datetime.utcnow(),
        received_by=admin.id,
        destination_country=body.destination_country,
        destination_city=body.destination_city,
        consignee_address=body.consignee_address,
        supplier_name=body.supplier_name,
        supplier_contact=body.supplier_contact,
        external_tracking_number=(
            body.external_tracking_number.strip().upper()
            if body.external_tracking_number
            else None
        ),
        notes=body.notes,
    )
    _apply_manual_links(db, admin, row, body)
    ensure_manual_intake_tracking_number(db, row)
    db.add(row)
    db.flush()
    for index, item_body in enumerate(body.items):
        item_body = _manual_item_with_legacy_rate(item_body, body)
        item = ManualCargoIntakeItem(
            intake_id=row.id,
            sort_order=index,
            item_name=item_body.item_name,
            item_description=item_body.item_description,
        )
        _apply_manual_item(item, item_body, body.cargo_type)
        db.add(item)
        row.items.append(item)
    _sync_manual_intake(row)
    create_manual_intake_tracking_event(
        db,
        row,
        event_type="manual_cargo_intake_created",
        description="Cargo intake registered",
        triggered_by=admin.id,
    )
    log_action(
        db,
        "manual_cargo_intake_created",
        admin.id,
        "manual_cargo_intake",
        row.id,
        {"intake_number": row.intake_number},
    )
    db.commit()
    db.refresh(row)
    return _serialize_manual_intake(
        _manual_intake_or_404(db, admin, str(row.id)), detail=True
    )


@router.get("/manual-cargo-intakes/{intake_id}")
def get_manual_cargo_intake(
    intake_id: str,
    db: Session = Depends(get_db),
    admin: User = Depends(get_cargo_admin),
):
    return _serialize_manual_intake(
        _manual_intake_or_404(db, admin, intake_id), detail=True
    )


@router.patch("/manual-cargo-intakes/{intake_id}")
def update_manual_cargo_intake(
    intake_id: str,
    body: ManualCargoIntakeInput,
    db: Session = Depends(get_db),
    admin: User = Depends(get_cargo_admin),
):
    row = _manual_intake_or_404(db, admin, intake_id)
    if row.status not in {"draft", "received", "ready_for_packing_list"}:
        raise HTTPException(
            status_code=409, detail="Only open cargo intakes can be edited"
        )
    if not body.items:
        raise HTTPException(
            status_code=422, detail="Add at least one received cargo item"
        )
    row.cargo_type = body.cargo_type
    # Preserve a receipt-level value for legacy reports; item-level rates are
    # authoritative for all newly created or edited cargo intakes.
    row.charge_basis = body.items[0].charge_basis
    row.rate_amount = body.items[0].rate_amount
    row.rate_currency = body.items[0].rate_currency
    row.received_at = body.received_at or row.received_at
    row.destination_country = body.destination_country
    row.destination_city = body.destination_city
    row.consignee_address = body.consignee_address
    row.supplier_name = body.supplier_name
    row.supplier_contact = body.supplier_contact
    row.external_tracking_number = (
        body.external_tracking_number.strip().upper()
        if body.external_tracking_number
        else None
    )
    row.notes = body.notes
    _apply_manual_links(db, admin, row, body)
    db.query(ManualCargoIntakeItem).filter(
        ManualCargoIntakeItem.intake_id == row.id
    ).delete(synchronize_session=False)
    row.items = []
    for index, item_body in enumerate(body.items):
        item_body = _manual_item_with_legacy_rate(item_body, body)
        item = ManualCargoIntakeItem(
            intake_id=row.id,
            sort_order=index,
            item_name=item_body.item_name,
            item_description=item_body.item_description,
        )
        _apply_manual_item(item, item_body, body.cargo_type)
        db.add(item)
        row.items.append(item)
    _sync_manual_intake(row)
    log_action(
        db, "manual_cargo_intake_updated", admin.id, "manual_cargo_intake", row.id
    )
    db.commit()
    return _serialize_manual_intake(
        _manual_intake_or_404(db, admin, intake_id), detail=True
    )


@router.post("/manual-cargo-intakes/{intake_id}/mark-received")
def mark_manual_cargo_received(
    intake_id: str,
    db: Session = Depends(get_db),
    admin: User = Depends(get_cargo_admin),
):
    row = _manual_intake_or_404(db, admin, intake_id)
    if row.status != "draft":
        raise HTTPException(
            status_code=409, detail="Only draft cargo intakes can be marked received"
        )
    row.status = "received"
    row.received_by = admin.id
    create_manual_intake_tracking_event(
        db,
        row,
        event_type="manual_cargo_received",
        description="Cargo received at warehouse",
        triggered_by=admin.id,
    )
    log_action(db, "manual_cargo_received", admin.id, "manual_cargo_intake", row.id)
    db.commit()
    return _serialize_manual_intake(
        _manual_intake_or_404(db, admin, intake_id), detail=True
    )


@router.post("/manual-cargo-intakes/{intake_id}/packing-list")
def generate_packing_list_from_manual_intake(
    intake_id: str,
    db: Session = Depends(get_db),
    admin: User = Depends(get_cargo_admin),
):
    intake = _manual_intake_or_404(db, admin, intake_id)
    existing = (
        db.query(CustomsPackingList)
        .filter(
            CustomsPackingList.cargo_admin_id == admin.id,
            CustomsPackingList.manual_intake_id == intake.id,
        )
        .first()
    )
    if existing:
        return _serialize_packing_list(
            _packing_or_404(db, admin, str(existing.id)), detail=True
        )
    if not intake.items:
        raise HTTPException(
            status_code=422,
            detail="Add received cargo items before generating a packing list",
        )
    packing = CustomsPackingList(
        cargo_admin_id=admin.id,
        packing_list_number=_next_reference(
            db,
            CustomsPackingList,
            CustomsPackingList.packing_list_number,
            f"PL-{date.today().year}-",
        ),
        manual_intake_id=intake.id,
        source_type="manual_intake",
        cargo_type=intake.cargo_type,
        customer_id=intake.customer_id,
        consignee_customer_id=intake.customer_id,
        warehouse_id=intake.warehouse_id,
        container_id=intake.container_id,
        sea_booking_id=intake.sea_booking_id,
        air_booking_id=intake.air_booking_id,
        origin_address=_warehouse_snapshot(intake.warehouse),
        shipper_snapshot={"name": admin.name or "Cargo Company"},
        consignee_snapshot=_customer_snapshot(intake.customer),
        shipment_references={
            "warehouse_receipt": intake.intake_number,
            "destination": ", ".join(
                part
                for part in [intake.destination_city, intake.destination_country]
                if part
            ),
        },
        notes=intake.notes,
    )
    db.add(packing)
    db.flush()
    for index, source in enumerate(intake.items):
        per_carton = source.gross_weight_per_carton_kg
        if per_carton is None and source.carton_count:
            per_carton = _as_decimal(source.total_gross_weight_kg) / Decimal(
                source.carton_count
            )
        item_body = PackingItemInput(
            item_name=source.item_name,
            item_description=source.item_description,
            item_photo_url=source.item_photo_url,
            carton_count=source.carton_count,
            qty_per_carton=source.qty_per_carton,
            length_cm=source.length_cm,
            width_cm=source.width_cm,
            height_cm=source.height_cm,
            cbm_per_carton=(
                source.cbm_per_carton if source.cbm_source == "direct" else None
            ),
            gross_weight_per_carton_kg=per_carton,
            remarks=source.remarks,
        )
        item = CustomsPackingListItem(
            packing_list_id=packing.id,
            sort_order=index,
            item_name=source.item_name,
            item_description=source.item_description,
        )
        _apply_item(item, item_body)
        db.add(item)
        packing.items.append(item)
    _sync_totals(packing)
    intake.status = "ready_for_packing_list"
    create_manual_intake_tracking_event(
        db,
        intake,
        event_type="manual_cargo_packing_list_generated",
        description="Packing list generated and cargo verified",
        triggered_by=admin.id,
        packing_list_id=str(packing.id),
    )
    log_action(
        db,
        "manual_cargo_packing_list_generated",
        admin.id,
        "manual_cargo_intake",
        intake.id,
        {"packing_list_id": str(packing.id)},
    )
    db.commit()
    return _serialize_packing_list(
        _packing_or_404(db, admin, str(packing.id)), detail=True
    )


@router.get("/customs-packing-lists/lookups")
def customs_lookups(
    db: Session = Depends(get_db), admin: User = Depends(get_cargo_admin)
):
    air_bookings = (
        db.query(ExpressAirCargoBooking)
        .options(joinedload(ExpressAirCargoBooking.shipping_mark))
        .filter(ExpressAirCargoBooking.cargo_admin_id == admin.id)
        .all()
    )
    return {
        "customers": [
            _serialize_customer(row)
            for row in db.query(CargoCustomer)
            .filter(
                CargoCustomer.cargo_admin_id == admin.id,
                CargoCustomer.status == "active",
            )
            .order_by(CargoCustomer.name)
            .all()
        ],
        "warehouses": [
            {
                "id": str(row.id),
                "name": row.name,
                "city": row.city,
                "country": row.country,
                "address": row.address or row.location,
            }
            for row in db.query(Warehouse).filter(Warehouse.admin_id == admin.id).all()
        ],
        "containers": [
            {
                "id": str(row.id),
                "reference": str(row.id),
                "status": row.status,
                "route": (
                    f"{row.route.origin} → {row.route.destination}"
                    if row.route
                    else None
                ),
            }
            for row in db.query(Container)
            .options(joinedload(Container.route))
            .filter(Container.admin_id == admin.id)
            .all()
        ],
        "sea_bookings": [
            {
                "id": str(row.id),
                "container_id": str(row.container_id),
                "customer_name": row.user.name if row.user else None,
            }
            for row in db.query(SeaBooking)
            .join(Container)
            .filter(Container.admin_id == admin.id)
            .all()
        ],
        "air_bookings": [
            {
                "id": str(row.id),
                "tracking_number": row.tracking_number,
                "cargo_description": row.cargo_description,
                "destination": _air_booking_destination(row),
            }
            for row in air_bookings
        ],
        "volumetric_divisor": 6000,
    }


@router.get("/customs-packing-lists")
def list_customs_packing_lists(
    status: Optional[Literal["draft", "finalized", "cancelled"]] = None,
    search: Optional[str] = None,
    db: Session = Depends(get_db),
    admin: User = Depends(get_cargo_admin),
):
    query = (
        db.query(CustomsPackingList)
        .options(joinedload(CustomsPackingList.customer))
        .filter(CustomsPackingList.cargo_admin_id == admin.id)
    )
    if status:
        query = query.filter(CustomsPackingList.status == status)
    if search:
        query = query.filter(
            CustomsPackingList.packing_list_number.ilike(f"%{search.strip()}%")
        )
    return {
        "packing_lists": [
            _serialize_packing_list(row)
            for row in query.order_by(CustomsPackingList.created_at.desc()).all()
        ]
    }


@router.post("/customs-packing-lists/prefill")
def prefill_customs_packing_list(
    body: CustomsPackingListInput,
    db: Session = Depends(get_db),
    admin: User = Depends(get_cargo_admin),
):
    """Preview trustworthy rows pulled from a sea_booking, container, or booking."""
    preview = CustomsPackingList(
        cargo_admin_id=admin.id,
        packing_list_number="PREVIEW",
        cargo_type=body.cargo_type,
    )
    _apply_packing_fields(db, admin, preview, body)
    rows = []
    for index, item_body in enumerate(_source_item_inputs(db, preview)):
        item = CustomsPackingListItem(
            packing_list_id=preview.id,
            sort_order=index,
            item_name=item_body.item_name,
            item_description=item_body.item_description,
        )
        _apply_item(item, item_body)
        rows.append(_serialize_item(item))
    return {
        "source_type": preview.source_type,
        "items": rows,
        "message": (
            "Source rows were prefilled. Review every dimension and quantity "
            "before finalizing the customs document."
            if rows
            else "No detailed source rows were available; add the Excel-style item rows manually."
        ),
    }


@router.post("/customs-packing-lists")
def create_customs_packing_list(
    body: CustomsPackingListInput,
    db: Session = Depends(get_db),
    admin: User = Depends(get_cargo_admin),
):
    row = CustomsPackingList(
        cargo_admin_id=admin.id,
        packing_list_number=_next_reference(
            db,
            CustomsPackingList,
            CustomsPackingList.packing_list_number,
            f"PL-{date.today().year}-",
        ),
        cargo_type=body.cargo_type,
    )
    db.add(row)
    db.flush()
    _apply_packing_fields(db, admin, row, body)
    item_inputs = body.items or _source_item_inputs(db, row)
    for index, item_body in enumerate(item_inputs):
        item = CustomsPackingListItem(
            packing_list_id=row.id,
            sort_order=index,
            item_name=item_body.item_name,
            item_description=item_body.item_description,
        )
        _apply_item(item, item_body)
        db.add(item)
        row.items.append(item)
    _sync_totals(row)
    log_action(
        db,
        "customs_packing_list_created",
        admin.id,
        "customs_packing_list",
        row.id,
        {"packing_list_number": row.packing_list_number},
    )
    db.commit()
    db.refresh(row)
    return _serialize_packing_list(row, detail=True)


@router.get("/customs-packing-lists/{packing_list_id}")
def get_customs_packing_list(
    packing_list_id: str,
    db: Session = Depends(get_db),
    admin: User = Depends(get_cargo_admin),
):
    return _serialize_packing_list(
        _packing_or_404(db, admin, packing_list_id), detail=True
    )


@router.patch("/customs-packing-lists/{packing_list_id}")
def update_customs_packing_list(
    packing_list_id: str,
    body: CustomsPackingListInput,
    db: Session = Depends(get_db),
    admin: User = Depends(get_cargo_admin),
):
    row = _packing_or_404(db, admin, packing_list_id)
    if row.status != "draft":
        raise HTTPException(
            status_code=409, detail="Only draft packing lists can be edited"
        )
    _apply_packing_fields(db, admin, row, body)
    db.query(CustomsPackingListItem).filter(
        CustomsPackingListItem.packing_list_id == row.id
    ).delete(synchronize_session=False)
    row.items = []
    for index, item_body in enumerate(body.items):
        item = CustomsPackingListItem(
            packing_list_id=row.id,
            sort_order=index,
            item_name=item_body.item_name,
            item_description=item_body.item_description,
        )
        _apply_item(item, item_body)
        db.add(item)
        row.items.append(item)
    _sync_totals(row)
    log_action(
        db, "customs_packing_list_updated", admin.id, "customs_packing_list", row.id
    )
    db.commit()
    return _serialize_packing_list(
        _packing_or_404(db, admin, packing_list_id), detail=True
    )


@router.post("/customs-packing-lists/{packing_list_id}/duplicate")
def duplicate_customs_packing_list(
    packing_list_id: str,
    db: Session = Depends(get_db),
    admin: User = Depends(get_cargo_admin),
):
    source = _packing_or_404(db, admin, packing_list_id)
    duplicate = CustomsPackingList(
        cargo_admin_id=admin.id,
        packing_list_number=_next_reference(
            db,
            CustomsPackingList,
            CustomsPackingList.packing_list_number,
            f"PL-{date.today().year}-",
        ),
        customer_id=source.customer_id,
        consignee_customer_id=source.consignee_customer_id,
        warehouse_id=source.warehouse_id,
        container_id=source.container_id,
        sea_booking_id=source.sea_booking_id,
        air_booking_id=source.air_booking_id,
        source_type=source.source_type,
        cargo_type=source.cargo_type,
        origin_address=source.origin_address,
        shipper_snapshot=source.shipper_snapshot,
        consignee_snapshot=source.consignee_snapshot,
        notify_party=source.notify_party,
        shipment_references=source.shipment_references,
        optional_columns=source.optional_columns,
        custom_columns=source.custom_columns,
        notes=source.notes,
    )
    db.add(duplicate)
    db.flush()
    for item in source.items:
        clone = CustomsPackingListItem(
            packing_list_id=duplicate.id,
            sort_order=item.sort_order,
            item_name=item.item_name,
            item_description=item.item_description,
            item_photo_url=item.item_photo_url,
            carton_count=item.carton_count,
            qty_per_carton=item.qty_per_carton,
            total_quantity=item.total_quantity,
            length_cm=item.length_cm,
            width_cm=item.width_cm,
            height_cm=item.height_cm,
            cbm_per_carton=item.cbm_per_carton,
            total_cbm=item.total_cbm,
            gross_weight_per_carton_kg=item.gross_weight_per_carton_kg,
            total_gross_weight_kg=item.total_gross_weight_kg,
            net_weight_per_carton_kg=item.net_weight_per_carton_kg,
            total_net_weight_kg=item.total_net_weight_kg,
            volumetric_weight_per_carton_kg=item.volumetric_weight_per_carton_kg,
            total_volumetric_weight_kg=item.total_volumetric_weight_kg,
            remarks=item.remarks,
            optional_values=item.optional_values,
            custom_values=item.custom_values,
        )
        db.add(clone)
        duplicate.items.append(clone)
    _sync_totals(duplicate)
    log_action(
        db,
        "customs_packing_list_duplicated",
        admin.id,
        "customs_packing_list",
        duplicate.id,
        {"source_id": str(source.id)},
    )
    db.commit()
    return _serialize_packing_list(duplicate, detail=True)


@router.post("/customs-packing-lists/{packing_list_id}/finalize")
def finalize_customs_packing_list(
    packing_list_id: str,
    db: Session = Depends(get_db),
    admin: User = Depends(get_cargo_admin),
):
    row = _packing_or_404(db, admin, packing_list_id)
    if row.status != "draft":
        raise HTTPException(
            status_code=409, detail="Only draft packing lists can be finalized"
        )
    if not row.items:
        raise HTTPException(
            status_code=422, detail="Add at least one packing item before finalizing"
        )
    issues = _completion_issues(row.items, row.source_type)
    if issues:
        raise HTTPException(
            status_code=422,
            detail={
                "message": "Complete the customs packing-list review before finalizing.",
                "issues": issues,
            },
        )
    _sync_totals(row)
    row.snapshot = _serialize_packing_list(row, detail=True)
    row.status = "finalized"
    row.finalized_at = datetime.utcnow()
    if row.manual_intake_id:
        intake = _manual_intake_or_404(db, admin, str(row.manual_intake_id))
        intake.status = "finalized"
        create_manual_intake_tracking_event(
            db,
            intake,
            event_type="manual_cargo_finalized",
            description="Cargo documentation finalized",
            triggered_by=admin.id,
            packing_list_id=str(row.id),
        )
    log_action(
        db, "customs_packing_list_finalized", admin.id, "customs_packing_list", row.id
    )
    db.commit()
    return _serialize_packing_list(row, detail=True)


@router.post("/customs-packing-lists/{packing_list_id}/cancel")
def cancel_customs_packing_list(
    packing_list_id: str,
    db: Session = Depends(get_db),
    admin: User = Depends(get_cargo_admin),
):
    row = _packing_or_404(db, admin, packing_list_id)
    if row.status == "finalized":
        raise HTTPException(
            status_code=409,
            detail="Finalized packing lists are historical documents and cannot be cancelled",
        )
    row.status = "cancelled"
    row.cancelled_at = datetime.utcnow()
    log_action(
        db, "customs_packing_list_cancelled", admin.id, "customs_packing_list", row.id
    )
    db.commit()
    return {"message": "Packing list cancelled"}


@router.get("/customs-packing-lists/{packing_list_id}/pdf")
def export_customs_packing_list_pdf(
    packing_list_id: str,
    db: Session = Depends(get_db),
    admin: User = Depends(get_cargo_admin),
):
    row = _packing_or_404(db, admin, packing_list_id)
    payload = (
        row.snapshot
        if row.status == "finalized" and row.snapshot
        else _serialize_packing_list(row, detail=True)
    )
    payload = dict(payload)
    brand = operator_document_branding(db, admin.id)
    current_shipper = dict(payload.get("shipper_snapshot") or {})
    current_address = current_shipper.get("address")
    if not isinstance(current_address, dict):
        current_address = {}
    payload["shipper_snapshot"] = {
        **current_shipper,
        "name": brand["name"],
        "phone": current_shipper.get("phone") or brand.get("phone"),
        "email": current_shipper.get("email") or brand.get("email"),
        "registration_number": current_shipper.get("registration_number")
        or brand.get("registration_number"),
        "address": {
            **current_address,
            "full_address": current_address.get("full_address") or brand.get("address"),
            "city": current_address.get("city") or brand.get("city"),
            "country": current_address.get("country") or brand.get("country"),
        },
    }
    content = DocumentGenerationService.generate_customs_packing_list_pdf(payload)
    log_action(
        db, "customs_packing_list_generated", admin.id, "customs_packing_list", row.id
    )
    db.commit()
    return StreamingResponse(
        iter([content]),
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'inline; filename="{row.packing_list_number}.pdf"'
        },
    )
