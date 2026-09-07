from typing import List, Optional
from uuid import UUID

from app.models.air_cargo import ExpressAirCargoBooking  # Correct class name
from app.models.container import Container, SeaBooking
from app.models.shipment_orders import ShipmentOrder, ShipmentOrderStatus
from app.models.user import User
from app.schemas.shipment_orders import ShipmentOrderCreate, ShipmentOrderUpdate
from app.services.tracking import TrackingService
from app.services.tracking_number import generate_unique_tracking_number
from fastapi import HTTPException, status
from sqlalchemy import or_
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, joinedload


def _sea_booking_destination_region(sea_booking: SeaBooking) -> str:
    """Return the best available destination token for a sea tracking number."""
    container = sea_booking.container
    if not container:
        return "Destination"
    if container.route and container.route.destination:
        return container.route.destination

    warehouse = container.destination_warehouse
    if warehouse:
        return warehouse.city or warehouse.location or warehouse.name or "Destination"
    return "Destination"


def _air_booking_destination_region(booking: ExpressAirCargoBooking) -> str:
    """Return the destination token encoded in an air booking's route label."""
    if booking.shipping_mark and booking.shipping_mark.destination_region:
        return booking.shipping_mark.destination_region
    route_parts = (booking.route_label or "").split("→")
    if len(route_parts) >= 2 and route_parts[-1].strip():
        return route_parts[-1].strip()
    return "Destination"


def _record_tracking_number_assignment(
    db: Session,
    order: ShipmentOrder,
    *,
    cargo_type: str,
    triggered_by: UUID | None,
) -> None:
    """Add the initial public-safe event to the shipment-order timeline."""
    TrackingService.create_tracking_event(
        db=db,
        entity_type="shipment_order",
        entity_id=str(order.id),
        event_type="tracking_number_assigned",
        description="Tracking number assigned to shipment",
        triggered_by=str(triggered_by) if triggered_by else None,
        extra_data={"tracking_number": order.tracking_number, "cargo_type": cargo_type},
    )


def ensure_shipment_order_for_sea_booking(
    db: Session,
    sea_booking: SeaBooking,
    *,
    destination_region: str | None = None,
) -> ShipmentOrder:
    """Create or reuse the one operational shipment order for a sea booking."""
    order = (
        db.query(ShipmentOrder)
        .filter(ShipmentOrder.sea_booking_id == sea_booking.id)
        .order_by(ShipmentOrder.created_at.desc())
        .first()
    )
    region = (
        destination_region or _sea_booking_destination_region(sea_booking)
    ).strip()
    region = region or "Destination"

    if order:
        if not order.tracking_number:
            order.tracking_number = generate_unique_tracking_number(
                db, "SEA", region, sea_booking.id
            )
            db.flush()
            _record_tracking_number_assignment(
                db,
                order,
                cargo_type="SEA",
                triggered_by=sea_booking.user_id,
            )
        return order

    order = ShipmentOrder(
        created_by_user_id=sea_booking.user_id,
        sea_booking_id=sea_booking.id,
        tracking_number=generate_unique_tracking_number(
            db, "SEA", region, sea_booking.id
        ),
        status="pending",
        order_description=f"Auto-created from sea cargo booking #{sea_booking.id}",
    )
    db.add(order)
    db.flush()
    _record_tracking_number_assignment(
        db,
        order,
        cargo_type="SEA",
        triggered_by=sea_booking.user_id,
    )
    return order


def ensure_shipment_order_for_air_booking(
    db: Session,
    booking: ExpressAirCargoBooking,
    *,
    destination_region: str | None = None,
) -> ShipmentOrder:
    """Create or reuse the one operational shipment order for an air booking."""
    order = (
        db.query(ShipmentOrder)
        .filter(ShipmentOrder.air_booking_id == booking.id)
        .order_by(ShipmentOrder.created_at.desc())
        .first()
    )
    if order and booking.tracking_number and order.tracking_number:
        if booking.tracking_number != order.tracking_number:
            raise ValueError(
                "Air booking and shipment order have conflicting tracking numbers."
            )

    if not booking.tracking_number and order and order.tracking_number:
        booking.tracking_number = order.tracking_number
        db.flush()

    if not booking.tracking_number:
        region = (
            destination_region or _air_booking_destination_region(booking)
        ).strip()
        booking.tracking_number = generate_unique_tracking_number(
            db, "AIR", region or "Destination", booking.id
        )
        db.flush()

    if order:
        if not order.tracking_number:
            order.tracking_number = booking.tracking_number
            db.flush()
            _record_tracking_number_assignment(
                db,
                order,
                cargo_type="AIR",
                triggered_by=booking.customer_id,
            )
        return order

    order = ShipmentOrder(
        created_by_user_id=booking.customer_id,
        air_booking_id=booking.id,
        tracking_number=booking.tracking_number,
        status="pending",
        order_description=(
            booking.cargo_description.strip()
            if booking.cargo_description and booking.cargo_description.strip()
            else f"Auto-created from express air booking #{booking.id}"
        ),
    )
    db.add(order)
    db.flush()
    _record_tracking_number_assignment(
        db,
        order,
        cargo_type="AIR",
        triggered_by=booking.customer_id,
    )
    return order


def create_shipment_order(
    db: Session, shipment_order: ShipmentOrderCreate
) -> ShipmentOrder:
    """
    Creates a new shipment order and validates that the associated
    sea booking or air cargo booking exists and belongs to the user
    """
    # Validate that either sea_booking_id or air_booking_id is provided
    if not shipment_order.sea_booking_id and not shipment_order.air_booking_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Either sea_booking_id or air_booking_id must be provided",
        )

    # Validate ownership of the associated sea_booking/booking
    if shipment_order.sea_booking_id:
        sea_booking = (
            db.query(SeaBooking)
            .filter(
                SeaBooking.id == shipment_order.sea_booking_id,
                SeaBooking.user_id == shipment_order.created_by_user_id,
            )
            .first()
        )
        if not sea_booking:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Container sea_booking not found or does not belong to user",
            )
    elif shipment_order.air_booking_id:
        air_booking = (
            db.query(ExpressAirCargoBooking)
            .filter(
                ExpressAirCargoBooking.id == shipment_order.air_booking_id,
                ExpressAirCargoBooking.customer_id == shipment_order.created_by_user_id,
            )
            .first()
        )
        if not air_booking:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Air cargo booking not found or does not belong to user",
            )

    # Create the shipment order
    db_shipment_order = ShipmentOrder(**shipment_order.model_dump())
    db.add(db_shipment_order)

    try:
        db.commit()
        db.refresh(db_shipment_order)
        return db_shipment_order
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Shipment order already exists",
        )


def get_shipment_order(
    db: Session, shipment_order_id: UUID, user_id: UUID
) -> Optional[ShipmentOrder]:
    """Retrieves a shipment order by ID for the specified user"""
    return (
        db.query(ShipmentOrder)
        .filter(
            ShipmentOrder.id == shipment_order_id,
            ShipmentOrder.created_by_user_id == user_id,
        )
        .first()
    )


def get_shipment_orders_by_user(
    db: Session, user_id: UUID, skip: int = 0, limit: int = 100
) -> List[ShipmentOrder]:
    """Retrieves all shipment orders for the specified user"""
    return (
        db.query(ShipmentOrder)
        .options(
            joinedload(ShipmentOrder.created_by_user),
            joinedload(ShipmentOrder.sea_booking).joinedload(SeaBooking.shipping_mark),
            joinedload(ShipmentOrder.sea_booking)
            .joinedload(SeaBooking.container)
            .joinedload(Container.route),
            joinedload(ShipmentOrder.sea_booking)
            .joinedload(SeaBooking.container)
            .joinedload(Container.origin_warehouse),
            joinedload(ShipmentOrder.air_booking).joinedload(
                ExpressAirCargoBooking.shipping_mark
            ),
            joinedload(ShipmentOrder.air_booking).joinedload(
                ExpressAirCargoBooking.cargo_type
            ),
        )
        .filter(ShipmentOrder.created_by_user_id == user_id)
        .offset(skip)
        .limit(limit)
        .all()
    )


def get_shipment_orders_by_sea_booking(
    db: Session, sea_booking_id: UUID, user_id: UUID
) -> List[ShipmentOrder]:
    """Retrieves all shipment orders for a specific sea booking"""
    return (
        db.query(ShipmentOrder)
        .filter(
            ShipmentOrder.sea_booking_id == sea_booking_id,
            ShipmentOrder.created_by_user_id == user_id,
        )
        .all()
    )


def get_shipment_orders_by_air_booking(
    db: Session, air_booking_id: UUID, user_id: UUID
) -> List[ShipmentOrder]:
    """Retrieves all shipment orders for a specific air cargo booking"""
    return (
        db.query(ShipmentOrder)
        .filter(
            ShipmentOrder.air_booking_id == air_booking_id,
            ShipmentOrder.created_by_user_id == user_id,
        )
        .all()
    )


def update_shipment_order(
    db: Session,
    shipment_order_id: UUID,
    shipment_order_update: ShipmentOrderUpdate,
    user_id: UUID,
) -> Optional[ShipmentOrder]:
    """Updates a shipment order with the specified values"""
    db_shipment_order = (
        db.query(ShipmentOrder)
        .filter(
            ShipmentOrder.id == shipment_order_id,
            ShipmentOrder.created_by_user_id == user_id,
        )
        .first()
    )

    if not db_shipment_order:
        return None

    # Update fields that are provided in the update object
    update_data = shipment_order_update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(db_shipment_order, field, value)

    try:
        db.commit()
        db.refresh(db_shipment_order)
        return db_shipment_order
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Error updating shipment order",
        )


def delete_shipment_order(db: Session, shipment_order_id: UUID, user_id: UUID) -> bool:
    """Deletes a shipment order by ID for the specified user"""
    db_shipment_order = (
        db.query(ShipmentOrder)
        .filter(
            ShipmentOrder.id == shipment_order_id,
            ShipmentOrder.created_by_user_id == user_id,
        )
        .first()
    )

    if not db_shipment_order:
        return False

    db.delete(db_shipment_order)
    db.commit()
    return True


def get_all_shipment_orders(
    db: Session,
    skip: int = 0,
    limit: int = 100,
    admin_id: UUID | None = None,
    statuses: Optional[List[ShipmentOrderStatus]] = None,
) -> List[ShipmentOrder]:
    """Retrieves all shipment orders (for admin use)"""
    query = db.query(ShipmentOrder).options(
        joinedload(ShipmentOrder.created_by_user),
        joinedload(ShipmentOrder.sea_booking).joinedload(SeaBooking.shipping_mark),
        joinedload(ShipmentOrder.sea_booking)
        .joinedload(SeaBooking.container)
        .joinedload(Container.route),
        joinedload(ShipmentOrder.sea_booking)
        .joinedload(SeaBooking.container)
        .joinedload(Container.origin_warehouse),
        joinedload(ShipmentOrder.air_booking).joinedload(
            ExpressAirCargoBooking.shipping_mark
        ),
        joinedload(ShipmentOrder.air_booking).joinedload(
            ExpressAirCargoBooking.cargo_type
        ),
    )

    # Cargo admins are scoped to shipment orders linked to their own containers or air bookings.
    if admin_id:
        query = (
            query.join(
                SeaBooking,
                ShipmentOrder.sea_booking_id == SeaBooking.id,
                isouter=True,
            )
            .join(
                Container,
                SeaBooking.container_id == Container.id,
                isouter=True,
            )
            .join(
                ExpressAirCargoBooking,
                ShipmentOrder.air_booking_id == ExpressAirCargoBooking.id,
                isouter=True,
            )
            .filter(
                or_(
                    Container.admin_id == admin_id,
                    ExpressAirCargoBooking.cargo_admin_id == admin_id,
                )
            )
        )

    if statuses:
        query = query.filter(ShipmentOrder.status.in_(statuses))

    return query.offset(skip).limit(limit).all()


def cargo_admin_can_access_shipment_order(
    db: Session, shipment_order_id: UUID, admin_id: UUID
) -> bool:
    """Check if a cargo admin can access a shipment order.

    Cargo admins can access:
    - sea shipment orders linked to containers they own
    - air-booking-linked shipment orders where the air booking is assigned to them
    """
    return (
        db.query(ShipmentOrder.id)
        .join(
            SeaBooking,
            ShipmentOrder.sea_booking_id == SeaBooking.id,
            isouter=True,
        )
        .join(Container, SeaBooking.container_id == Container.id, isouter=True)
        .join(
            ExpressAirCargoBooking,
            ShipmentOrder.air_booking_id == ExpressAirCargoBooking.id,
            isouter=True,
        )
        .filter(
            ShipmentOrder.id == shipment_order_id,
            or_(
                Container.admin_id == admin_id,
                ExpressAirCargoBooking.cargo_admin_id == admin_id,
            ),
        )
        .first()
        is not None
    )


def update_shipment_order_status(
    db: Session, shipment_order_id: UUID, new_status: str, user_id: UUID = None
) -> Optional[ShipmentOrder]:
    """Updates only the status of a shipment order"""
    query = db.query(ShipmentOrder).filter(ShipmentOrder.id == shipment_order_id)

    # If user_id is provided, restrict to user's orders (for customer updates)
    if user_id:
        query = query.filter(ShipmentOrder.created_by_user_id == user_id)

    db_shipment_order = query.first()

    if not db_shipment_order:
        return None

    db_shipment_order.status = new_status
    try:
        db.commit()
        db.refresh(db_shipment_order)
        return db_shipment_order
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Error updating shipment order status",
        )
