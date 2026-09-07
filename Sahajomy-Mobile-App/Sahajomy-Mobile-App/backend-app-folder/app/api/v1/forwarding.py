"""Shared China-forwarding preparation for every booking-capable user."""

from typing import Optional

from app.core.auth.auth_dependencies import get_current_user
from app.database import get_db
from app.models.air_cargo import AirCargoRate
from app.models.cargo_company import CargoOperatorProfile
from app.models.container import Container, Warehouse
from app.models.customer_china_address import CustomerChinaAddress
from app.models.user import User
from app.services.china_warehouse_address import (
    china_address_ready,
    is_china_warehouse,
    normalize_warehouse_china_address,
)
from app.services.company_service_governance import (
    company_service_is_bookable,
    require_company_service_bookable,
)
from app.services.customer_china_addresses import (
    copy_ready_address,
    ensure_customer_china_address,
    prepare_user_air_china_address,
)
from fastapi import APIRouter, Depends, Header, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session, joinedload

router = APIRouter(prefix="/forwarding", tags=["forwarding"])


def get_booking_user(
    current_user: User = Depends(get_current_user),
    workspace: Optional[str] = Header(None, alias="X-Sahajomy-Workspace"),
    company_header: Optional[str] = Header(None, alias="X-Sahajomy-Company"),
) -> User:
    """Resolve the person using booking services in the active workspace."""
    if company_header:
        raise HTTPException(
            status_code=403,
            detail="Switch to My Sahajomy Account for personal bookings.",
        )
    if workspace == "personal":
        return current_user
    # Preserve sourcing-agent booking tools in the sourcing-agent workspace and
    # old customer clients while all current clients send an explicit workspace.
    if current_user.role in {"customer", "sourcing_agent", "super_admin"}:
        return current_user
    raise HTTPException(
        status_code=403, detail="Switch to My Sahajomy Account for personal bookings."
    )


class ForwardingProfileRequest(BaseModel):
    full_name: Optional[str] = Field(None, min_length=2, max_length=150)
    phone: Optional[str] = Field(None, min_length=6, max_length=50)


class PrepareChinaAddressRequest(BaseModel):
    cargo_mode: str
    destination_city: str = Field(..., min_length=2, max_length=120)
    destination_country: str = Field(..., min_length=2, max_length=100)
    container_id: Optional[str] = None
    preferred_address_id: Optional[str] = None
    cargo_admin_id: Optional[str] = None
    warehouse_id: Optional[str] = None


@router.get("/air-services")
def list_air_forwarding_services(
    db: Session = Depends(get_db),
    user: User = Depends(get_booking_user),
):
    """List provider/warehouse choices that are ready for air bookings."""
    providers = (
        db.query(User)
        .filter(
            User.role == "cargo_admin",
            User.is_active.is_(True),
            User.status == "active",
        )
        .order_by(User.name.asc(), User.created_at.asc())
        .all()
    )
    existing = {
        str(address.warehouse_id): address
        for address in db.query(CustomerChinaAddress).filter(
            CustomerChinaAddress.customer_id == user.id,
            CustomerChinaAddress.cargo_mode == "air",
            CustomerChinaAddress.status == "active",
        )
    }
    services = []
    changed = False
    for provider in providers:
        if not company_service_is_bookable(
            db, operator_id=provider.id, service_type="air_cargo"
        ):
            continue
        operator_profile = (
            db.query(CargoOperatorProfile)
            .filter(CargoOperatorProfile.user_id == provider.id)
            .first()
        )
        published_routes = [
            row[0]
            for row in db.query(AirCargoRate.route)
            .filter(
                AirCargoRate.cargo_admin_id == provider.id,
                AirCargoRate.is_active.is_(True),
            )
            .distinct()
            .order_by(AirCargoRate.route.asc())
            .all()
            if row[0]
        ]
        warehouses = (
            db.query(Warehouse)
            .filter(
                Warehouse.admin_id == provider.id,
                Warehouse.warehouse_type.in_(["air", "both"]),
            )
            .order_by(Warehouse.created_at.asc())
            .all()
        )
        for warehouse in warehouses:
            changed = normalize_warehouse_china_address(warehouse) or changed
            if not (is_china_warehouse(warehouse) and china_address_ready(warehouse)):
                continue
            address = existing.get(str(warehouse.id))
            services.append(
                {
                    "cargo_admin_id": str(provider.id),
                    "cargo_admin_name": provider.name or "Cargo Provider",
                    "profile_image_url": provider.profile_image_url,
                    "warehouse_id": str(warehouse.id),
                    "warehouse_name": warehouse.name,
                    "city": warehouse.city or warehouse.china_city,
                    "country": warehouse.country or "China",
                    "destination_countries": (
                        list(operator_profile.destination_countries or [])
                        if operator_profile
                        else []
                    ),
                    "published_routes": published_routes,
                    "address": copy_ready_address(address) if address else None,
                }
            )
    if changed:
        db.commit()
    return {"services": services}


@router.get("/china-addresses")
def list_forwarding_addresses(
    db: Session = Depends(get_db),
    user: User = Depends(get_booking_user),
):
    addresses = (
        db.query(CustomerChinaAddress)
        .options(
            joinedload(CustomerChinaAddress.warehouse),
            joinedload(CustomerChinaAddress.customer),
        )
        .filter(
            CustomerChinaAddress.customer_id == user.id,
            CustomerChinaAddress.status == "active",
        )
        .order_by(CustomerChinaAddress.created_at.desc())
        .all()
    )
    return {
        "profile": {
            "name": user.name,
            "phone": user.secure_phone or user.phone_number,
        },
        "addresses": [copy_ready_address(address) for address in addresses],
    }


@router.patch("/profile")
def update_forwarding_profile(
    body: ForwardingProfileRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_booking_user),
):
    if body.full_name and not (user.name or "").strip():
        full_name = body.full_name.strip()
        if len(full_name) < 2:
            raise HTTPException(status_code=422, detail="Enter a valid full name.")
        user.name = full_name
    if body.phone and not (user.secure_phone or user.phone_number):
        phone = body.phone.strip()
        if len(phone) < 6:
            raise HTTPException(
                status_code=422, detail="Enter a valid Phone / WhatsApp Number."
            )
        duplicate = (
            db.query(User.id)
            .filter(User.phone_number == phone, User.id != user.id)
            .first()
        )
        if duplicate:
            raise HTTPException(
                status_code=409,
                detail="That phone / WhatsApp number is already linked to another account.",
            )
        user.phone_number = phone
    db.commit()
    return {"name": user.name, "phone": user.secure_phone or user.phone_number}


@router.post("/prepare-address")
def prepare_forwarding_address(
    body: PrepareChinaAddressRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_booking_user),
):
    mode = body.cargo_mode.strip().lower()
    destination_city = body.destination_city.strip()
    destination_country = body.destination_country.strip()
    if len(destination_city) < 2:
        raise HTTPException(
            status_code=422,
            detail="Enter the destination city required for your shipping mark.",
        )
    if mode == "air":
        address, _warehouse = prepare_user_air_china_address(
            db,
            user=user,
            destination_country=destination_country,
            destination_city=destination_city,
            preferred_address_id=body.preferred_address_id,
            cargo_admin_id=body.cargo_admin_id,
            warehouse_id=body.warehouse_id,
        )
    elif mode == "sea":
        if not body.container_id:
            raise HTTPException(status_code=422, detail="Choose a sea container first.")
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
        if container:
            require_company_service_bookable(
                db,
                operator_id=container.admin_id,
                service_type="shared_container",
            )
        if (
            not warehouse
            or warehouse.warehouse_type not in {"sea", "both"}
            or not is_china_warehouse(warehouse)
        ):
            raise HTTPException(
                status_code=409,
                detail="The selected sea service has no ready China forwarding warehouse.",
            )
        address = ensure_customer_china_address(
            db,
            customer=user,
            warehouse=warehouse,
            cargo_mode="sea",
            destination_country=destination_country,
            destination_city=destination_city,
        )
    else:
        raise HTTPException(status_code=422, detail="Cargo mode must be sea or air.")

    db.commit()
    db.refresh(address)
    return copy_ready_address(address)
