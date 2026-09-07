"""
Tracking API - Unified tracking for containers, sea_bookings, orders, and bookings.
"""

from typing import Optional

from app.core.dependencies import (
    get_cargo_admin,
    get_current_user,
    get_customer,
    get_sourcing_agent,
)
from app.core.reference_ids import build_display_reference
from app.database import get_db
from app.models.tracking import TrackingEvent
from app.models.user import User
from app.services.tracking import TrackingService, resolve_logistics_stage
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import or_
from sqlalchemy.orm import Session

router = APIRouter(prefix="/tracking", tags=["Tracking"])

DB_SESSION = Depends(get_db)
CUSTOMER_USER = Depends(get_customer)
CARGO_ADMIN_USER = Depends(get_cargo_admin)
SOURCING_AGENT_USER = Depends(get_sourcing_agent)
AUTHENTICATED_USER = Depends(get_current_user)


class TrackingEventResponse:
    id: str
    entity_type: str
    entity_id: str
    event_type: str
    description: str
    timestamp: str
    triggered_by: Optional[str]
    extra_data: Optional[dict]
    logistics_stage: Optional[str]
    stage_label: Optional[str]
    stage_sequence: Optional[int]
    stage_owner_role: Optional[str]
    progress: Optional[int]
    display_reference: Optional[str]
    reference_id: Optional[str]
    canonical_entity_type: str
    canonical_entity_id: str
    shipment_key: str
    shipment_reference: str

    def __init__(
        self,
        event: TrackingEvent,
        *,
        canonical_entity_type: Optional[str] = None,
        canonical_entity_id: Optional[str] = None,
    ):
        self.id = str(event.id)
        self.entity_type = event.entity_type
        self.entity_id = event.entity_id
        self.event_type = event.event_type
        self.description = event.description
        self.timestamp = event.timestamp
        self.triggered_by = str(event.triggered_by) if event.triggered_by else None
        self.extra_data = event.extra_data
        stage = resolve_logistics_stage(event.event_type, event.extra_data) or {}
        self.logistics_stage = stage.get("logistics_stage")
        self.stage_label = stage.get("stage_label")
        self.stage_sequence = stage.get("stage_sequence")
        self.stage_owner_role = stage.get("stage_owner_role")
        self.progress = stage.get("progress")
        manual_tracking_number = (
            (event.extra_data or {}).get("tracking_number")
            if event.entity_type == "manual_cargo_intake"
            else None
        )
        self.display_reference = manual_tracking_number or build_display_reference(
            event.entity_type, event.entity_id, event.timestamp
        )
        self.reference_id = self.display_reference
        self.canonical_entity_type = canonical_entity_type or event.entity_type
        self.canonical_entity_id = str(canonical_entity_id or event.entity_id)
        self.shipment_key = f"{self.canonical_entity_type}_{self.canonical_entity_id}"
        self.shipment_reference = manual_tracking_number or build_display_reference(
            self.canonical_entity_type,
            self.canonical_entity_id,
            event.timestamp,
        )


TRACKING_STATUS_FILTERS = {"pending", "in_transit", "delivered"}


def _filter_tracking_events_by_latest_status(
    events: list[TrackingEventResponse], status_filter: Optional[str]
) -> list[TrackingEventResponse]:
    """Keep complete timelines only for entities whose latest status matches."""
    if not status_filter:
        return events

    normalized_filter = status_filter.strip().lower()
    if normalized_filter not in TRACKING_STATUS_FILTERS:
        raise HTTPException(
            status_code=422,
            detail=f"Invalid status filter. Valid values are: {sorted(TRACKING_STATUS_FILTERS)}",
        )

    grouped_events: dict[tuple[str, str], list[TrackingEventResponse]] = {}
    for event in events:
        grouped_events.setdefault((event.entity_type, event.entity_id), []).append(
            event
        )

    matching_entities = set()
    for entity_key, entity_events in grouped_events.items():
        latest_event = max(entity_events, key=lambda event: event.timestamp)
        extra_data = latest_event.extra_data or {}
        latest_status = str(
            extra_data.get("new_status")
            or extra_data.get("status")
            or latest_event.event_type
        ).lower()

        if normalized_filter == "pending" and latest_status == "pending":
            matching_entities.add(entity_key)
        elif normalized_filter == "in_transit" and latest_status in {
            "in_transit",
            "departed",
            "departed_origin",
            "container_departed",
            "shipped",
        }:
            matching_entities.add(entity_key)
        elif normalized_filter == "delivered" and latest_status in {
            "delivered",
            "goods_collected",
            "completed",
        }:
            matching_entities.add(entity_key)

    return [
        event
        for event in events
        if (event.entity_type, event.entity_id) in matching_entities
    ]


def _shipment_order_tracking_events(db: Session, shipment_orders) -> list:
    """Attach order events to the booking/sea_booking they operationalize.

    A ShipmentOrder is the fulfilment record for a booking, not a second
    shipment. The original event identity is retained for timeline/audit use,
    while the canonical identity lets every frontend render one shipment card.
    """
    responses = []
    for order in shipment_orders:
        if order.sea_booking_id:
            canonical_type = "sea_booking"
            canonical_id = str(order.sea_booking_id)
        elif order.air_booking_id:
            canonical_type = "booking"
            canonical_id = str(order.air_booking_id)
        else:
            canonical_type = "shipment_order"
            canonical_id = str(order.id)

        events = TrackingService.get_entity_timeline(
            db, "shipment_order", str(order.id)
        )
        responses.extend(
            TrackingEventResponse(
                event,
                canonical_entity_type=canonical_type,
                canonical_entity_id=canonical_id,
            )
            for event in events
        )
    return responses


def _manual_intake_tracking_events(db: Session, intakes) -> list:
    responses = []
    for intake in intakes:
        events = TrackingService.get_entity_timeline(
            db, "manual_cargo_intake", str(intake.id)
        )
        responses.extend(TrackingEventResponse(event) for event in events)
    return responses


@router.get("/customer/sea-bookings")
def get_customer_sea_booking_tracking(
    db: Session = DB_SESSION, current_user: User = CUSTOMER_USER
):
    """Get tracking timeline for customer's sea_bookings."""
    from app.models.container import SeaBooking

    # Get customer's sea_bookings
    sea_bookings = (
        db.query(SeaBooking).filter(SeaBooking.user_id == current_user.id).all()
    )

    all_events = []
    for sea_booking in sea_bookings:
        events = TrackingService.get_entity_timeline(
            db, "sea_booking", str(sea_booking.id)
        )
        all_events.extend([TrackingEventResponse(event) for event in events])

    # Sort by timestamp descending
    all_events.sort(key=lambda x: x.timestamp, reverse=True)
    return all_events


@router.get("/customer/bookings")
def get_customer_booking_tracking(
    db: Session = DB_SESSION, current_user: User = CUSTOMER_USER
):
    """Get tracking timeline for customer's air cargo bookings."""
    from app.models.air_cargo import ExpressAirCargoBooking

    # Get customer's air cargo bookings
    bookings = (
        db.query(ExpressAirCargoBooking)
        .filter(ExpressAirCargoBooking.customer_id == current_user.id)
        .all()
    )

    all_events = []
    for booking in bookings:
        events = TrackingService.get_entity_timeline(db, "booking", str(booking.id))
        all_events.extend([TrackingEventResponse(event) for event in events])

    # Sort by timestamp descending
    all_events.sort(key=lambda x: x.timestamp, reverse=True)
    return all_events


@router.get("/customer/shipment_orders")
def get_customer_shipment_order_tracking(
    db: Session = DB_SESSION, current_user: User = CUSTOMER_USER
):
    """Get tracking timeline for customer's shipment orders."""
    from app.models.shipment_orders import ShipmentOrder

    # Get customer's shipment orders
    shipment_orders = (
        db.query(ShipmentOrder)
        .filter(ShipmentOrder.created_by_user_id == current_user.id)
        .all()
    )

    all_events = _shipment_order_tracking_events(db, shipment_orders)

    # Sort by timestamp descending
    all_events.sort(key=lambda x: x.timestamp, reverse=True)
    return all_events


@router.get("/customer/manual-intakes")
def get_customer_manual_intake_tracking(
    db: Session = DB_SESSION, current_user: User = CUSTOMER_USER
):
    """Get warehouse intake timelines linked to the signed-in customer."""
    from app.models.cargo_customs import CargoCustomer, ManualCargoIntake

    intakes = (
        db.query(ManualCargoIntake)
        .join(CargoCustomer)
        .filter(CargoCustomer.linked_user_id == current_user.id)
        .all()
    )
    events = _manual_intake_tracking_events(db, intakes)
    events.sort(key=lambda event: event.timestamp, reverse=True)
    return events


@router.get("/admin/containers")
def get_admin_container_tracking(
    status_filter: Optional[str] = Query(default=None, alias="status"),
    db: Session = DB_SESSION,
    current_user: User = CARGO_ADMIN_USER,
):
    """Get tracking timeline for admin's containers."""
    from app.models.container import Container

    # Cargo admins see their own containers; super admins see all containers.
    if current_user.role == "super_admin":
        containers = db.query(Container).all()
    else:
        containers = (
            db.query(Container).filter(Container.admin_id == current_user.id).all()
        )

    all_events = []
    for container in containers:
        events = TrackingService.get_entity_timeline(db, "container", str(container.id))
        all_events.extend([TrackingEventResponse(event) for event in events])

    # Sort by timestamp descending
    all_events.sort(key=lambda x: x.timestamp, reverse=True)
    return _filter_tracking_events_by_latest_status(all_events, status_filter)


@router.get("/admin/sea-bookings")
def get_admin_sea_booking_tracking(
    status_filter: Optional[str] = Query(default=None, alias="status"),
    db: Session = DB_SESSION,
    current_user: User = CARGO_ADMIN_USER,
):
    """Get tracking timeline for admin's sea bookings."""
    from app.models.container import Container, SeaBooking

    # Cargo admins see sea_bookings for their containers; super admins see all.
    if current_user.role == "super_admin":
        sea_bookings = db.query(SeaBooking).all()
    else:
        sea_bookings = (
            db.query(SeaBooking)
            .join(Container, SeaBooking.container_id == Container.id)
            .filter(Container.admin_id == current_user.id)
            .all()
        )

    all_events = []
    for sea_booking in sea_bookings:
        events = TrackingService.get_entity_timeline(
            db, "sea_booking", str(sea_booking.id)
        )
        all_events.extend([TrackingEventResponse(event) for event in events])

    # Sort by timestamp descending
    all_events.sort(key=lambda x: x.timestamp, reverse=True)
    return _filter_tracking_events_by_latest_status(all_events, status_filter)


@router.get("/admin/bookings")
def get_admin_booking_tracking(
    status_filter: Optional[str] = Query(default=None, alias="status"),
    db: Session = DB_SESSION,
    current_user: User = CARGO_ADMIN_USER,
):
    """Get tracking timeline for admin's air cargo bookings."""
    from app.models.air_cargo import ExpressAirCargoBooking

    # Cargo admins see assigned bookings; super admins see all bookings.
    if current_user.role == "super_admin":
        bookings = db.query(ExpressAirCargoBooking).all()
    else:
        bookings = (
            db.query(ExpressAirCargoBooking)
            .filter(ExpressAirCargoBooking.cargo_admin_id == current_user.id)
            .all()
        )

    all_events = []
    for booking in bookings:
        events = TrackingService.get_entity_timeline(db, "booking", str(booking.id))
        all_events.extend([TrackingEventResponse(event) for event in events])

    # Sort by timestamp descending
    all_events.sort(key=lambda x: x.timestamp, reverse=True)
    return _filter_tracking_events_by_latest_status(all_events, status_filter)


@router.get("/admin/shipment_orders")
def get_admin_shipment_order_tracking(
    status_filter: Optional[str] = Query(default=None, alias="status"),
    db: Session = DB_SESSION,
    current_user: User = CARGO_ADMIN_USER,
):
    """Get tracking timeline for admin's shipment orders."""
    from app.models.air_cargo import ExpressAirCargoBooking
    from app.models.container import Container, SeaBooking
    from app.models.shipment_orders import ShipmentOrder

    if current_user.role == "super_admin":
        shipment_orders = db.query(ShipmentOrder).all()
    else:
        # Cargo admins can see orders linked to their own containers or air
        # bookings explicitly assigned to them.
        shipment_orders = (
            db.query(ShipmentOrder)
            .join(
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
                    Container.admin_id == current_user.id,
                    ExpressAirCargoBooking.cargo_admin_id == current_user.id,
                )
            )
            .all()
        )

    all_events = _shipment_order_tracking_events(db, shipment_orders)

    # Sort by timestamp descending
    all_events.sort(key=lambda x: x.timestamp, reverse=True)
    return _filter_tracking_events_by_latest_status(all_events, status_filter)


@router.get("/admin/manual-intakes")
def get_admin_manual_intake_tracking(
    db: Session = DB_SESSION,
    current_user: User = CARGO_ADMIN_USER,
):
    """Get manual/scanned cargo timelines in the administrator's scope."""
    from app.models.cargo_customs import ManualCargoIntake

    query = db.query(ManualCargoIntake)
    if current_user.role != "super_admin":
        query = query.filter(ManualCargoIntake.cargo_admin_id == current_user.id)
    events = _manual_intake_tracking_events(db, query.all())
    events.sort(key=lambda event: event.timestamp, reverse=True)
    return events


@router.get("/agent/bookings")
def get_agent_booking_tracking(
    db: Session = DB_SESSION, current_user: User = SOURCING_AGENT_USER
):
    """Get tracking timeline for sourcing agent's air cargo bookings."""
    from app.models.air_cargo import ExpressAirCargoBooking

    # Get agent's air cargo bookings (agents are stored as customer_id)
    bookings = (
        db.query(ExpressAirCargoBooking)
        .filter(ExpressAirCargoBooking.customer_id == current_user.id)
        .all()
    )

    all_events = []
    for booking in bookings:
        events = TrackingService.get_entity_timeline(db, "booking", str(booking.id))
        all_events.extend([TrackingEventResponse(event) for event in events])

    # Sort by timestamp descending
    all_events.sort(key=lambda x: x.timestamp, reverse=True)
    return all_events


@router.get("/agent/manual-intakes")
def get_agent_manual_intake_tracking(
    db: Session = DB_SESSION, current_user: User = SOURCING_AGENT_USER
):
    """Get warehouse intake timelines linked to the sourcing agent."""
    from app.models.cargo_customs import CargoCustomer, ManualCargoIntake

    intakes = (
        db.query(ManualCargoIntake)
        .join(CargoCustomer)
        .filter(CargoCustomer.linked_user_id == current_user.id)
        .all()
    )
    events = _manual_intake_tracking_events(db, intakes)
    events.sort(key=lambda event: event.timestamp, reverse=True)
    return events


@router.get("/agent/shipment_orders")
def get_agent_shipment_order_tracking(
    db: Session = DB_SESSION, current_user: User = SOURCING_AGENT_USER
):
    """Get tracking timeline for sourcing agent's shipment orders."""
    from app.models.container import SeaBooking
    from app.models.shipment_orders import ShipmentOrder

    # Get agent's own shipment orders (created directly by agent)
    agent_own_orders = (
        db.query(ShipmentOrder)
        .filter(ShipmentOrder.created_by_user_id == current_user.id)
        .all()
    )

    # Get all batches owned by this agent
    agent_batch_ids = [b.id for b in current_user.sourcing_batches]

    shipment_orders_from_batches = []
    if agent_batch_ids:
        # Get sea_bookings linked to agent's batches
        batch_sea_bookings = (
            db.query(SeaBooking)
            .filter(
                SeaBooking.source_type == "batch",
                SeaBooking.source_id.in_(agent_batch_ids),
            )
            .all()
        )

        # Get shipment orders linked to these sea_bookings
        sea_booking_ids = [r.id for r in batch_sea_bookings]
        if sea_booking_ids:
            shipment_orders_from_batches = (
                db.query(ShipmentOrder)
                .filter(ShipmentOrder.sea_booking_id.in_(sea_booking_ids))
                .all()
            )

    # Combine all shipment orders
    all_shipment_orders = list(set(agent_own_orders + shipment_orders_from_batches))

    all_events = _shipment_order_tracking_events(db, all_shipment_orders)

    # Sort by timestamp descending
    all_events.sort(key=lambda x: x.timestamp, reverse=True)
    return all_events


@router.get("/agent/sea-bookings")
def get_agent_sea_booking_tracking(
    db: Session = DB_SESSION, current_user: User = SOURCING_AGENT_USER
):
    """Get tracking timeline for sourcing agent sea-cargo sea_bookings from batches."""
    from app.models.container import SeaBooking

    # Get all batches owned by this agent
    agent_batch_ids = [b.id for b in current_user.sourcing_batches]

    if not agent_batch_ids:
        return []

    # Get sea_bookings linked to agent's batches
    sea_bookings = (
        db.query(SeaBooking)
        .filter(
            SeaBooking.source_type == "batch",
            SeaBooking.source_id.in_(agent_batch_ids),
        )
        .all()
    )

    all_events = []
    for sea_booking in sea_bookings:
        events = TrackingService.get_entity_timeline(
            db, "sea_booking", str(sea_booking.id)
        )
        all_events.extend([TrackingEventResponse(event) for event in events])

    # Sort by timestamp descending
    all_events.sort(key=lambda x: x.timestamp, reverse=True)
    return all_events


@router.get("/{entity_type}/{entity_id}")
def get_tracking_timeline(
    entity_type: str,
    entity_id: str,
    db: Session = DB_SESSION,
    current_user: User = AUTHENTICATED_USER,
):
    """
    Get the tracking timeline for a specific entity.
    Entity can be: container, sea_booking, order, booking, manual_cargo_intake
    """
    # Verify user has permission to view this entity
    if not _has_permission(db, current_user, entity_type, entity_id):
        raise HTTPException(
            status_code=403, detail="Not authorized to view this tracking information"
        )

    events = TrackingService.get_entity_timeline(db, entity_type, entity_id)
    return [TrackingEventResponse(event) for event in events]


def _has_permission(db: Session, user: User, entity_type: str, entity_id: str) -> bool:
    """Check if user has permission to view tracking information for an entity."""
    if user.role == "super_admin":
        return True

    if entity_type == "container":
        from app.models.container import Container

        container = db.query(Container).filter(Container.id == entity_id).first()
        if not container:
            return False
        return container.admin_id == user.id or user.role == "super_admin"

    elif entity_type == "sea_booking":
        from app.models.container import SeaBooking

        sea_booking = db.query(SeaBooking).filter(SeaBooking.id == entity_id).first()
        if not sea_booking:
            return False

        if user.role == "customer":
            return sea_booking.user_id == user.id
        elif user.role == "sourcing_agent":
            # Sourcing agents can view sea_bookings linked to their batches
            if sea_booking.source_type == "batch" and sea_booking.source_id:
                from app.models.sourcing import SourcingBatch

                batch = (
                    db.query(SourcingBatch)
                    .filter(
                        SourcingBatch.id == sea_booking.source_id,
                        SourcingBatch.agent_id == user.id,
                    )
                    .first()
                )
                return batch is not None
            return False
        elif user.role in ["cargo_admin", "super_admin"]:
            from app.models.container import Container

            container = (
                db.query(Container)
                .filter(Container.id == sea_booking.container_id)
                .first()
            )
            return container.admin_id == user.id if container else False

    elif entity_type == "manual_cargo_intake":
        from app.models.cargo_customs import CargoCustomer, ManualCargoIntake

        intake = (
            db.query(ManualCargoIntake)
            .join(CargoCustomer)
            .filter(ManualCargoIntake.id == entity_id)
            .first()
        )
        if not intake:
            return False
        if user.role in {"customer", "sourcing_agent"}:
            return intake.customer.linked_user_id == user.id
        if user.role == "cargo_admin":
            return intake.cargo_admin_id == user.id
        return False

    elif entity_type == "booking":
        from app.models.air_cargo import ExpressAirCargoBooking

        booking = (
            db.query(ExpressAirCargoBooking)
            .filter(ExpressAirCargoBooking.id == entity_id)
            .first()
        )
        if not booking:
            return False
        return (
            booking.customer_id == user.id
            or booking.cargo_admin_id == user.id
            or user.role == "super_admin"
        )

    elif entity_type == "shipment_order":
        from app.models.air_cargo import ExpressAirCargoBooking
        from app.models.container import Container, SeaBooking
        from app.models.shipment_orders import ShipmentOrder

        shipment_order = (
            db.query(ShipmentOrder).filter(ShipmentOrder.id == entity_id).first()
        )
        if not shipment_order:
            return False
        if shipment_order.created_by_user_id == user.id:
            return True
        if user.role == "cargo_admin":
            return (
                db.query(ShipmentOrder.id)
                .join(
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
                    ShipmentOrder.id == shipment_order.id,
                    or_(
                        Container.admin_id == user.id,
                        ExpressAirCargoBooking.cargo_admin_id == user.id,
                    ),
                )
                .first()
                is not None
            )
        return user.role == "super_admin"

    return False
