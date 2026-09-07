"""Shared tracking-event helpers for manual and scanned cargo intakes."""

from __future__ import annotations

from app.services.tracking import TrackingService

STATUS_STAGES = {
    "draft": "booking_received",
    "received": "cargo_received",
    "ready_for_packing_list": "packed_verified",
    "finalized": "completed",
    "cancelled": "booking_received",
    "ready_for_pickup": "ready_for_pickup",
    "completed": "completed",
}


def manual_intake_event_data(intake, *, status: str | None = None, **extra) -> dict:
    current_status = status or intake.status
    warehouse = getattr(intake, "warehouse", None)
    location = None
    if warehouse:
        location = warehouse.name or warehouse.city or warehouse.country
    return {
        "tracking_number": intake.tracking_number,
        "external_tracking_number": intake.external_tracking_number,
        "cargo_type": intake.cargo_type,
        "status": current_status,
        "new_status": current_status,
        "logistics_stage": STATUS_STAGES.get(current_status),
        "location": location,
        "destination_city": intake.destination_city,
        "destination_country": intake.destination_country,
        "total_cartons": intake.total_cartons,
        **extra,
    }


def create_manual_intake_tracking_event(
    db,
    intake,
    *,
    event_type: str,
    description: str,
    triggered_by=None,
    status: str | None = None,
    **extra,
):
    return TrackingService.create_tracking_event(
        db=db,
        entity_type="manual_cargo_intake",
        entity_id=str(intake.id),
        event_type=event_type,
        description=description,
        triggered_by=str(triggered_by) if triggered_by else None,
        extra_data=manual_intake_event_data(intake, status=status, **extra),
    )
