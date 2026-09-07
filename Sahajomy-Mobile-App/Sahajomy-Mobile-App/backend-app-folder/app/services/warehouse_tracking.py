"""Shared warehouse tracking updates for booking-linked parcel operations."""

from __future__ import annotations

import re
from urllib.parse import unquote

from app.models.shipment_orders import ShipmentOrder, ShipmentOrderStatus
from app.services.shipment_orders_service import (
    ensure_shipment_order_for_air_booking,
    ensure_shipment_order_for_sea_booking,
)
from app.services.tracking import TrackingService

PLATFORM_LABEL_PATTERN = re.compile(
    r"(?:/label/|SAHAJOMY[:/| -]+)(sea|air)[:/| -]+"
    r"([0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12})",
    re.IGNORECASE,
)


def platform_label_reference(raw_code: str) -> tuple[str, str] | None:
    """Extract a typed booking UUID from a platform label URL or scan payload."""
    decoded = unquote((raw_code or "").strip())
    match = PLATFORM_LABEL_PATTERN.search(decoded)
    if not match:
        return None
    return match.group(1).lower(), match.group(2).lower()


def record_booking_warehouse_event(
    db,
    *,
    sea_booking=None,
    air_booking=None,
    event_type: str,
    description: str,
    logistics_stage: str,
    actor_id=None,
    location: str | None = None,
    status: str | None = None,
    extra_data: dict | None = None,
) -> ShipmentOrder | None:
    """Write one operational event to both the booking and canonical shipment order."""
    if bool(sea_booking) == bool(air_booking):
        return None

    booking = sea_booking or air_booking
    entity_type = "sea_booking" if sea_booking else "booking"
    event_data = {
        "logistics_stage": logistics_stage,
        "location": location,
        "status": status or logistics_stage,
        "new_status": status or logistics_stage,
        **(extra_data or {}),
    }
    TrackingService.create_tracking_event(
        db=db,
        entity_type=entity_type,
        entity_id=str(booking.id),
        event_type=event_type,
        description=description,
        triggered_by=str(actor_id) if actor_id else None,
        extra_data=event_data,
    )

    order = None
    if sea_booking:
        order = (
            db.query(ShipmentOrder)
            .filter(ShipmentOrder.sea_booking_id == sea_booking.id)
            .order_by(ShipmentOrder.created_at.desc())
            .first()
        )
        if not order and sea_booking.user_id:
            order = ensure_shipment_order_for_sea_booking(db, sea_booking)
    else:
        order = (
            db.query(ShipmentOrder)
            .filter(ShipmentOrder.air_booking_id == air_booking.id)
            .order_by(ShipmentOrder.created_at.desc())
            .first()
        )
        if not order and air_booking.customer_id:
            order = ensure_shipment_order_for_air_booking(db, air_booking)

    if not order:
        return None

    if logistics_stage == "cargo_received":
        order.status = ShipmentOrderStatus.received_at_warehouse
    elif logistics_stage in {
        "loaded_container",
        "container_sealed",
        "departed_china",
        "in_transit",
        "destination_arrival",
        "customs_clearance",
        "ready_for_pickup",
        "completed",
    }:
        order.status = ShipmentOrderStatus.shipped

    TrackingService.create_tracking_event(
        db=db,
        entity_type="shipment_order",
        entity_id=str(order.id),
        event_type=event_type,
        description=description,
        triggered_by=str(actor_id) if actor_id else None,
        extra_data={
            **event_data,
            "new_status": order.status.value,
            "booking_entity_type": entity_type,
            "booking_id": str(booking.id),
        },
    )
    return order
