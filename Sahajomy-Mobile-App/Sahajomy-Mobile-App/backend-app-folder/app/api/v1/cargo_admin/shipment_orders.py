from typing import Dict, List, Optional
from uuid import UUID

from app.core.dependencies import get_cargo_admin  # Correct import for cargo admin auth
from app.database import get_db
from app.models.shipment_orders import ShipmentOrder, ShipmentOrderStatus
from app.models.tracking import TrackingEvent
from app.models.user import User
from app.schemas.shipment_orders import ShipmentOrderResponse
from app.services.shipment_orders_service import (
    cargo_admin_can_access_shipment_order,
    get_all_shipment_orders,
    update_shipment_order_status,
)
from app.services.tracking import TrackingService
from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

# Rename the dependency to match what's used in the file
get_current_cargo_admin_user = get_cargo_admin

router = APIRouter()


class ShipmentOperationUpdate(BaseModel):
    action: str
    note: Optional[str] = None
    public_note: Optional[str] = None
    warehouse_status: Optional[str] = None
    cargo_readiness: Optional[str] = None
    container_id: Optional[str] = None
    quantity_confirmed: Optional[bool] = None
    carton_count: Optional[int] = None
    damaged: Optional[bool] = None
    damage_report: Optional[str] = None
    photo_urls: Optional[List[str]] = None


OPERATION_WORKFLOW: Dict[str, Dict[str, str]] = {
    "approve_booking": {
        "stage": "booking_approved",
        "label": "Booking approved",
        "status": "confirmed",
    },
    "reject_booking": {
        "stage": "booking_received",
        "label": "Booking rejected",
        "issue": "true",
    },
    "supplier_contacted": {
        "stage": "supplier_contacted",
        "label": "Supplier contacted",
        "status": "supplier_contacted",
    },
    "supplier_confirmed": {
        "stage": "supplier_confirmed",
        "label": "Supplier confirmed",
        "status": "confirmed",
    },
    "awaiting_supplier_shipment": {
        "stage": "awaiting_supplier_shipment",
        "label": "Awaiting supplier shipment",
        "status": "confirmed",
    },
    "supplier_issue": {
        "stage": "supplier_contacted",
        "label": "Supplier issue reported",
        "issue": "true",
    },
    "cargo_received": {
        "stage": "cargo_received",
        "label": "Cargo received at warehouse",
        "status": "received_at_warehouse",
    },
    "inspection_completed": {
        "stage": "inspection_completed",
        "label": "Inspection completed",
        "status": "received_at_warehouse",
    },
    "damaged_cargo": {
        "stage": "inspection_completed",
        "label": "Damaged cargo reported",
        "issue": "true",
        "status": "received_at_warehouse",
    },
    "carton_verified": {
        "stage": "packed_verified",
        "label": "Cartons verified",
        "status": "received_at_warehouse",
    },
    "quantity_confirmed": {
        "stage": "packed_verified",
        "label": "Quantity confirmed",
        "status": "received_at_warehouse",
    },
    "warehouse_remark": {"stage": "cargo_received", "label": "Warehouse remark added"},
    "assigned_container": {
        "stage": "assigned_container",
        "label": "Assigned to container",
        "status": "shipped",
    },
    "loading_progress": {
        "stage": "loaded_container",
        "label": "Container loading progress updated",
        "status": "shipped",
    },
    "loaded_container": {
        "stage": "loaded_container",
        "label": "Loaded into container",
        "status": "shipped",
    },
    "container_sealed": {
        "stage": "container_sealed",
        "label": "Container sealed",
        "status": "shipped",
    },
    "departed_china": {
        "stage": "departed_china",
        "label": "Departed China",
        "status": "shipped",
    },
    "in_transit": {"stage": "in_transit", "label": "In transit", "status": "shipped"},
    "destination_arrival": {
        "stage": "destination_arrival",
        "label": "Arrived at destination port",
        "status": "shipped",
    },
    "customs_clearance": {
        "stage": "customs_clearance",
        "label": "Customs clearance",
        "status": "shipped",
    },
    "ready_for_pickup": {
        "stage": "ready_for_pickup",
        "label": "Ready for pickup",
        "status": "received_at_warehouse",
    },
    "delivered_completed": {
        "stage": "completed",
        "label": "Delivered/completed",
        "status": "received_at_warehouse",
    },
}

SEA_ONLY_ACTIONS = {
    "assigned_container",
    "loading_progress",
    "loaded_container",
    "container_sealed",
}

# These names represent the existing dashboard groupings. Individual persisted
# shipment-order statuses remain valid filter values as well.
SHIPMENT_ORDER_STATUS_GROUPS = {
    "supplier": [
        ShipmentOrderStatus.supplier_contacted,
        ShipmentOrderStatus.confirmed,
    ],
    "warehouse": [ShipmentOrderStatus.received_at_warehouse],
    "moving": [ShipmentOrderStatus.shipped],
}


@router.get("", response_model=List[ShipmentOrderResponse])
def get_all_shipment_orders_endpoint(
    skip: int = 0,
    limit: int = 100,
    status_filter: Optional[str] = Query(default=None, alias="status"),
    current_user: User = Depends(get_current_cargo_admin_user),
    db: Session = Depends(get_db),
):
    """Get all shipment orders (admin view)"""
    admin_scope = None if current_user.role == "super_admin" else current_user.id
    statuses = None
    if status_filter:
        statuses = SHIPMENT_ORDER_STATUS_GROUPS.get(status_filter)
        if statuses is None:
            try:
                statuses = [ShipmentOrderStatus(status_filter)]
            except ValueError as exc:
                valid_filters = [
                    *[item.value for item in ShipmentOrderStatus],
                    *SHIPMENT_ORDER_STATUS_GROUPS.keys(),
                ]
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                    detail=f"Invalid status filter. Valid values are: {valid_filters}",
                ) from exc

    orders = get_all_shipment_orders(
        db,
        skip=skip,
        limit=limit,
        admin_id=admin_scope,
        statuses=statuses,
    )

    order_ids = [order.id for order in orders]
    latest_event_map = {}
    if order_ids:
        tracking_events = (
            db.query(TrackingEvent)
            .filter(
                TrackingEvent.entity_type == "shipment_order",
                TrackingEvent.entity_id.in_(order_ids),
            )
            .order_by(TrackingEvent.timestamp.desc())
            .all()
        )
        for event in tracking_events:
            if event.entity_id not in latest_event_map:
                latest_event_map[event.entity_id] = event

    for order in orders:
        latest_event = latest_event_map.get(order.id)
        setattr(
            order, "latest_update", latest_event.description if latest_event else None
        )
        setattr(
            order, "latest_update_at", latest_event.timestamp if latest_event else None
        )

    return orders


@router.put("/{shipment_order_id}/status")
def update_shipment_order_status_endpoint(
    shipment_order_id: UUID,
    new_status: str,  # Using query param for simplicity
    current_user: User = Depends(get_current_cargo_admin_user),
    db: Session = Depends(get_db),
):
    """Update the status of a shipment order (admin action)"""
    # Validate the status is one of the allowed values
    from app.models.shipment_orders import ShipmentOrderStatus

    try:
        status_enum = ShipmentOrderStatus(new_status)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid status. Valid statuses are: {[s.value for s in ShipmentOrderStatus]}",
        )

    # Get current order to compare status
    current_order = (
        db.query(ShipmentOrder).filter(ShipmentOrder.id == shipment_order_id).first()
    )
    if not current_order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Shipment order not found"
        )
    if (
        current_user.role != "super_admin"
        and not cargo_admin_can_access_shipment_order(
            db, shipment_order_id, current_user.id
        )
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to update this shipment order",
        )

    previous_status = current_order.status
    updated_order = update_shipment_order_status(db, shipment_order_id, new_status)

    if updated_order and str(updated_order.status) != str(previous_status):
        # Create tracking event for status update
        TrackingService.create_tracking_event(
            db=db,
            entity_type="shipment_order",
            entity_id=str(updated_order.id),
            event_type="shipment_order_status_updated",
            description=f"Shipment order status updated by admin from {previous_status} to {updated_order.status}",
            triggered_by=str(current_user.id),
            extra_data={
                "old_status": str(previous_status),
                "new_status": updated_order.status,
                "order_description": updated_order.order_description,
                "updated_by_role": current_user.role,
            },
        )
        db.commit()
        db.refresh(updated_order)

    return updated_order


@router.post("/{shipment_order_id}/operations", response_model=ShipmentOrderResponse)
def update_shipment_order_operation_endpoint(
    shipment_order_id: UUID,
    body: ShipmentOperationUpdate,
    current_user: User = Depends(get_current_cargo_admin_user),
    db: Session = Depends(get_db),
):
    """Record a professional logistics operation against an existing shipment order.

    This reuses shipment_orders.status for backward-compatible coarse state and
    tracking_events.extra_data for detailed operations history, notes, photos,
    warehouse checks, and user-visible timeline progress.
    """
    normalized_action = (body.action or "").strip().lower()

    # ─── ALLOW SKIP ACTIONS ──────────────────────────────────────────────
    # If the action starts with "skip_", treat it as a stage skip.
    # This does NOT change the order's main status – only records a tracking event.
    if normalized_action.startswith("skip_"):
        operation = {
            "stage": "skipped",
            "label": "Stage skipped",
            "status": None,  # No status change
        }
    else:
        operation = OPERATION_WORKFLOW.get(normalized_action)
        if not operation:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid operation. Valid operations are: {list(OPERATION_WORKFLOW.keys())}",
            )

    order = (
        db.query(ShipmentOrder).filter(ShipmentOrder.id == shipment_order_id).first()
    )
    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Shipment order not found"
        )

    if (
        current_user.role != "super_admin"
        and not cargo_admin_can_access_shipment_order(
            db, shipment_order_id, current_user.id
        )
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to update this shipment order",
        )

    # Enforce operation scope by shipment mode:
    # - air booking orders cannot use sea container assignment/loading operations.
    is_air_order = bool(order.air_booking_id) and not bool(order.sea_booking_id)
    if is_air_order and normalized_action in SEA_ONLY_ACTIONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This operation is only valid for sea cargo shipment orders.",
        )

    old_status = order.status
    mapped_status = operation.get("status")
    if mapped_status:
        order.status = ShipmentOrderStatus(mapped_status)

    note = (body.note or "").strip()
    public_note = (body.public_note or note or operation["label"]).strip()
    if note:
        existing_notes = (order.notes or "").strip()
        order.notes = f"{existing_notes}\n[{operation['label']}] {note}".strip()

    extra_data = {
        "operation": normalized_action,
        "logistics_stage": operation["stage"],
        "stage_label": operation["label"],
        "old_status": str(old_status),
        "new_status": str(order.status),
        "public_note": public_note,
        "admin_note": note or None,
        "warehouse_status": body.warehouse_status,
        "cargo_readiness": body.cargo_readiness,
        "container_id": body.container_id,
        "quantity_confirmed": body.quantity_confirmed,
        "carton_count": body.carton_count,
        "damaged": body.damaged,
        "damage_report": body.damage_report,
        "photo_urls": body.photo_urls,
        "updated_by_role": current_user.role,
    }
    event_type = (
        "shipment_issue_reported"
        if operation.get("issue") == "true" or body.damaged
        else "logistics_operation_updated"
    )
    TrackingService.create_tracking_event(
        db=db,
        entity_type="shipment_order",
        entity_id=str(order.id),
        event_type=event_type,
        description=f"{operation['label']}: {public_note}",
        triggered_by=str(current_user.id),
        extra_data=extra_data,
    )
    db.commit()
    db.refresh(order)
    return order
