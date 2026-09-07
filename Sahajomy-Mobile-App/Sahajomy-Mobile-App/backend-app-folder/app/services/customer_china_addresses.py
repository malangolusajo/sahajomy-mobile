"""Authoritative generation and formatting of customer China delivery addresses."""

from __future__ import annotations

import re
import secrets

from app.models.container import Warehouse
from app.models.customer_china_address import CustomerChinaAddress
from app.models.user import User
from app.services.china_warehouse_address import (
    china_address_ready,
    is_china_warehouse,
    normalize_warehouse_china_address,
)
from fastapi import HTTPException
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session


def _phone(user: User) -> str | None:
    return user.secure_phone or user.phone_number


def _normalized_address_part(value: str | None) -> str:
    return re.sub(r"\s+", "", str(value or "")).strip()


def _unique_address_parts(*values: str | None) -> list[str]:
    """Keep the most complete occurrence of overlapping address fields.

    Legacy detailed-address values sometimes already contain the province,
    city, district, receiver, or phone. Prefer that complete value instead of
    repeating its structured fragments in the copy-ready address.
    """
    parts: list[tuple[str, str]] = []
    for value in values:
        rendered = str(value or "").strip()
        normalized = _normalized_address_part(rendered)
        if normalized and normalized not in {item[1] for item in parts}:
            parts.append((rendered, normalized))

    return [
        rendered
        for index, (rendered, normalized) in enumerate(parts)
        if not any(
            index != other_index
            and len(other_normalized) > len(normalized)
            and normalized in other_normalized
            for other_index, (_, other_normalized) in enumerate(parts)
        )
    ]


def ensure_customer_china_address(
    db: Session,
    *,
    customer: User,
    warehouse: Warehouse,
    cargo_mode: str,
    destination_country: str,
    destination_city: str,
) -> CustomerChinaAddress:
    if cargo_mode not in {"sea", "air"}:
        raise HTTPException(status_code=422, detail="Cargo mode must be sea or air.")
    if not (customer.name or "").strip() or not (_phone(customer) or "").strip():
        raise HTTPException(
            status_code=422,
            detail="Add your name and Phone / WhatsApp Number to continue.",
        )
    normalize_warehouse_china_address(warehouse)
    if not china_address_ready(warehouse):
        raise HTTPException(
            status_code=409,
            detail="This warehouse delivery address is being updated. Please contact the cargo provider.",
        )
    existing = (
        db.query(CustomerChinaAddress)
        .filter(
            CustomerChinaAddress.customer_id == customer.id,
            CustomerChinaAddress.warehouse_id == warehouse.id,
            CustomerChinaAddress.cargo_mode == cargo_mode,
        )
        .first()
    )
    if existing:
        # A disabled address cannot be silently reused for a new booking.
        if existing.status == "active":
            existing.destination_country = destination_country.strip()
            existing.destination_city = destination_city.strip()
            return existing
        raise HTTPException(
            status_code=409,
            detail="This China delivery address is no longer active. Please contact the cargo provider.",
        )
    prefix = "SH-SEA" if cargo_mode == "sea" else "SH-AIR"
    for _ in range(10):
        address = CustomerChinaAddress(
            customer_id=customer.id,
            cargo_admin_id=warehouse.admin_id,
            warehouse_id=warehouse.id,
            cargo_mode=cargo_mode,
            shipping_mark=f"{prefix}-{secrets.randbelow(10000):04d}",
            destination_country=destination_country.strip(),
            destination_city=destination_city.strip(),
        )
        try:
            with db.begin_nested():
                db.add(address)
                db.flush()
            return address
        except IntegrityError:
            continue
    raise HTTPException(
        status_code=503, detail="Could not create a shipping mark. Please try again."
    )


def prepare_user_air_china_address(
    db: Session,
    *,
    user: User,
    destination_country: str,
    destination_city: str,
    preferred_address_id: str | None = None,
    cargo_admin_id: str | None = None,
    warehouse_id: str | None = None,
) -> tuple[CustomerChinaAddress, Warehouse]:
    """Resolve a ready air service and create the user's address before booking."""
    warehouse = None
    if preferred_address_id:
        preferred = (
            db.query(CustomerChinaAddress)
            .filter(
                CustomerChinaAddress.id == preferred_address_id,
                CustomerChinaAddress.customer_id == user.id,
                CustomerChinaAddress.cargo_mode == "air",
                CustomerChinaAddress.status == "active",
            )
            .first()
        )
        if preferred:
            candidate = preferred.warehouse
            provider = db.get(User, candidate.admin_id) if candidate else None
            if candidate:
                normalize_warehouse_china_address(candidate)
            if (
                candidate
                and provider
                and provider.is_active
                and provider.status == "active"
                and candidate.warehouse_type in {"air", "both"}
                and is_china_warehouse(candidate)
                and china_address_ready(candidate)
                and (
                    not cargo_admin_id or str(candidate.admin_id) == str(cargo_admin_id)
                )
                and (not warehouse_id or str(candidate.id) == str(warehouse_id))
            ):
                warehouse = candidate
            else:
                raise HTTPException(
                    status_code=409,
                    detail="The saved China address does not belong to the selected cargo service.",
                )
        else:
            raise HTTPException(
                status_code=404, detail="Saved China air address not found."
            )

    if warehouse is None:
        # Local import avoids coupling the generic assignment service back to
        # customer-address persistence.
        if cargo_admin_id:
            from app.services.air_cargo_assignment import (
                select_ready_air_service_for_admin,
            )

            _provider, warehouse = select_ready_air_service_for_admin(
                db, cargo_admin_id=cargo_admin_id, warehouse_id=warehouse_id
            )
        else:
            from app.services.air_cargo_assignment import select_best_ready_air_service

            _admin_id, warehouse = select_best_ready_air_service(db)

    address = ensure_customer_china_address(
        db,
        customer=user,
        warehouse=warehouse,
        cargo_mode="air",
        destination_country=destination_country,
        destination_city=destination_city,
    )
    return address, warehouse


def copy_ready_address(address: CustomerChinaAddress) -> dict:
    warehouse = address.warehouse
    customer = address.customer
    phone = (_phone(customer) or "").replace(" ", "")
    display_mark = f"{address.shipping_mark} {customer.name.upper()} {phone} {address.destination_city.upper()}"
    detailed = warehouse.china_detailed_address
    complete_address = "\n".join(
        [
            *_unique_address_parts(
                warehouse.name_zh or warehouse.name,
                warehouse.china_receiver_name,
                warehouse.china_mobile,
                warehouse.china_province,
                warehouse.china_city,
                warehouse.china_district,
                warehouse.china_street,
                detailed,
            ),
            f"【{display_mark}】",
        ]
    )
    return {
        "id": str(address.id),
        "shipping_mark": address.shipping_mark,
        "cargo_mode": address.cargo_mode,
        "cargo_admin": {
            "id": str(address.cargo_admin_id),
            "name": warehouse.admin.name if warehouse.admin else "Cargo Provider",
            "profile_image_url": (
                warehouse.admin.profile_image_url if warehouse.admin else None
            ),
        },
        "destination": {
            "country": address.destination_country,
            "city": address.destination_city,
        },
        "warehouse": {
            "id": str(warehouse.id),
            "name_en": warehouse.name,
            "name_zh": warehouse.name_zh,
            "receiver": warehouse.china_receiver_name,
            "china_mobile": warehouse.china_mobile,
            "province": warehouse.china_province,
            "city": warehouse.china_city,
            "district": warehouse.china_district,
            "street": warehouse.china_street,
            "detailed_address": detailed,
        },
        "customer": {"name": customer.name, "phone": _phone(customer)},
        "status": address.status,
        "created_at": address.created_at.isoformat() if address.created_at else None,
        "copy": {
            "receiver": warehouse.china_receiver_name,
            "china_mobile": warehouse.china_mobile,
            "province": warehouse.china_province,
            "city": warehouse.china_city,
            "district": warehouse.china_district,
            "street": warehouse.china_street,
            "detailed_address": detailed,
            "shipping_mark": display_mark,
            "complete_address": complete_address,
        },
    }
