from app.models.air_cargo import ExpressAirCargoBooking
from app.models.container import Warehouse
from app.models.user import User
from app.services.china_warehouse_address import (
    china_address_ready,
    is_china_warehouse,
    normalize_warehouse_china_address,
)
from app.services.company_service_governance import company_service_is_bookable
from fastapi import HTTPException
from sqlalchemy import func
from sqlalchemy.orm import Session


def select_ready_air_service_for_admin(
    db: Session, *, cargo_admin_id: str, warehouse_id: str | None = None
) -> tuple[User, Warehouse]:
    """Resolve an explicit provider/warehouse pair without cross-provider fallback."""
    provider = (
        db.query(User)
        .filter(
            User.id == cargo_admin_id,
            User.role == "cargo_admin",
            User.is_active.is_(True),
            User.status == "active",
        )
        .first()
    )
    if not provider:
        raise HTTPException(
            status_code=409, detail="The selected cargo provider is unavailable."
        )
    if not company_service_is_bookable(
        db, operator_id=provider.id, service_type="air_cargo"
    ):
        raise HTTPException(
            status_code=409,
            detail="The selected cargo provider is not currently accepting air bookings.",
        )

    query = db.query(Warehouse).filter(
        Warehouse.admin_id == provider.id,
        Warehouse.warehouse_type.in_(["air", "both"]),
    )
    if warehouse_id:
        query = query.filter(Warehouse.id == warehouse_id)
    for warehouse in query.order_by(Warehouse.created_at.asc()).all():
        normalize_warehouse_china_address(warehouse)
        if is_china_warehouse(warehouse) and china_address_ready(warehouse):
            return provider, warehouse

    raise HTTPException(
        status_code=409,
        detail="The selected cargo provider has no ready China air warehouse.",
    )


def _active_cargo_admin_booking_counts(db: Session):
    """Return active cargo admins ordered by current workload and account age."""
    return (
        db.query(User.id, func.count(ExpressAirCargoBooking.id).label("booking_count"))
        .outerjoin(
            ExpressAirCargoBooking,
            (User.id == ExpressAirCargoBooking.cargo_admin_id)
            & (ExpressAirCargoBooking.status.notin_(["delivered", "cancelled"])),
        )
        .filter(
            User.role == "cargo_admin",
            User.is_active.is_(True),
            User.status == "active",
        )
        .group_by(User.id)
        .order_by(func.count(ExpressAirCargoBooking.id).asc(), User.created_at.asc())
        .all()
    )


def select_best_cargo_admin_id(db: Session):
    """Select the cargo admin with the least current air cargo bookings for optimal load balancing."""
    admin_booking_counts = [
        row
        for row in _active_cargo_admin_booking_counts(db)
        if company_service_is_bookable(
            db, operator_id=row[0], service_type="air_cargo"
        )
    ]

    if admin_booking_counts:
        return admin_booking_counts[0][0]  # Return the admin ID with least bookings

    # Fallback: get any cargo admin if active/status data is incomplete
    fallback_admin = (
        db.query(User)
        .filter(User.role == "cargo_admin")
        .order_by(User.created_at.asc())
        .first()
    )
    if fallback_admin:
        return fallback_admin.id

    raise HTTPException(
        status_code=503,
        detail="No cargo admin is currently available for air booking assignment.",
    )


def select_best_ready_air_service(db: Session) -> tuple[object, Warehouse]:
    """Select the least-loaded operator that has a ready China air warehouse.

    A customer address cannot be generated from partial provider data. Skipping
    incomplete operators prevents a customer from uploading files and then
    receiving a warehouse-configuration conflict when another ready operator
    is available.
    """
    for admin_id, _booking_count in _active_cargo_admin_booking_counts(db):
        if not company_service_is_bookable(
            db, operator_id=admin_id, service_type="air_cargo"
        ):
            continue
        warehouses = (
            db.query(Warehouse)
            .filter(
                Warehouse.admin_id == admin_id,
                Warehouse.warehouse_type.in_(["air", "both"]),
            )
            .order_by(Warehouse.created_at.asc())
            .all()
        )
        for warehouse in warehouses:
            normalize_warehouse_china_address(warehouse)
            if is_china_warehouse(warehouse) and china_address_ready(warehouse):
                return admin_id, warehouse

    raise HTTPException(
        status_code=503,
        detail=(
            "Express Air Cargo is temporarily unavailable because no cargo provider "
            "has a ready China forwarding warehouse. Please try again later."
        ),
    )


def assign_cargo_admin_to_air_booking(db: Session, booking):
    """Assign a cargo admin to an air booking if not already assigned."""
    if booking.cargo_admin_id is None:
        cargo_admin_id = select_best_cargo_admin_id(db)
        booking.cargo_admin_id = cargo_admin_id
    return booking
