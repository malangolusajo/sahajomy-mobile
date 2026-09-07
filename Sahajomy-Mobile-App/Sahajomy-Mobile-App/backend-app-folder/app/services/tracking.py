"""Tracking and notification services for logistics platform."""

from typing import Dict, Iterable, List, Optional

from app.core.reference_ids import build_display_reference
from app.models.air_cargo import ExpressAirCargoBooking
from app.models.container import SeaBooking
from app.models.finance import Notification
from app.models.tracking import TrackingEvent
from app.services.realtime_notifications import create_notification
from sqlalchemy.orm import Session

LOGISTICS_TIMELINE_STAGES = [
    {
        "key": "booking_received",
        "label": "Booking Received",
        "sequence": 1,
        "owner_role": "User",
    },
    {
        "key": "booking_approved",
        "label": "Booking Approved",
        "sequence": 2,
        "owner_role": "Cargo Admin",
    },
    {
        "key": "supplier_contacted",
        "label": "Supplier Contacted",
        "sequence": 3,
        "owner_role": "Cargo Admin",
    },
    {
        "key": "supplier_confirmed",
        "label": "Supplier Confirmed",
        "sequence": 4,
        "owner_role": "Cargo Admin",
    },
    {
        "key": "awaiting_supplier_shipment",
        "label": "Awaiting Supplier Shipment",
        "sequence": 5,
        "owner_role": "Supplier",
    },
    {
        "key": "cargo_received",
        "label": "Cargo Received at Warehouse",
        "sequence": 6,
        "owner_role": "Warehouse Staff",
    },
    {
        "key": "inspection_completed",
        "label": "Inspection Completed",
        "sequence": 7,
        "owner_role": "Warehouse Staff",
    },
    {
        "key": "packed_verified",
        "label": "Packed & Verified",
        "sequence": 8,
        "owner_role": "Warehouse Staff",
    },
    {
        "key": "assigned_container",
        "label": "Assigned to Container",
        "sequence": 9,
        "owner_role": "Cargo Admin",
    },
    {
        "key": "loaded_container",
        "label": "Loaded into Container",
        "sequence": 10,
        "owner_role": "Warehouse Staff",
    },
    {
        "key": "container_sealed",
        "label": "Container Sealed",
        "sequence": 11,
        "owner_role": "Logistics Admin",
    },
    {
        "key": "departed_china",
        "label": "Departed China",
        "sequence": 12,
        "owner_role": "Logistics Admin",
    },
    {
        "key": "in_transit",
        "label": "In Transit",
        "sequence": 13,
        "owner_role": "Logistics Admin",
    },
    {
        "key": "destination_arrival",
        "label": "Arrived Destination Port",
        "sequence": 14,
        "owner_role": "Logistics Admin",
    },
    {
        "key": "customs_clearance",
        "label": "Customs Clearance",
        "sequence": 15,
        "owner_role": "Logistics Admin",
    },
    {
        "key": "ready_for_pickup",
        "label": "Ready for Pickup",
        "sequence": 16,
        "owner_role": "Support/Admin",
    },
    {
        "key": "completed",
        "label": "Delivered/Completed",
        "sequence": 17,
        "owner_role": "Support/Admin",
    },
]

_STAGE_BY_KEY = {stage["key"]: stage for stage in LOGISTICS_TIMELINE_STAGES}


def _stage_payload(stage_key: str | None) -> Dict | None:
    if not stage_key or stage_key not in _STAGE_BY_KEY:
        return None
    stage = _STAGE_BY_KEY[stage_key]
    return {
        "logistics_stage": stage["key"],
        "stage_label": stage["label"],
        "stage_sequence": stage["sequence"],
        "stage_owner_role": stage["owner_role"],
        "progress": round(stage["sequence"] / len(LOGISTICS_TIMELINE_STAGES) * 100),
    }


def resolve_logistics_stage(
    event_type: str, extra_data: Optional[Dict] = None
) -> Dict | None:
    """Map existing platform events/statuses onto the professional shipment timeline."""
    extra_data = extra_data or {}
    explicit_stage = extra_data.get("logistics_stage")
    if explicit_stage:
        return _stage_payload(str(explicit_stage))

    status = str(extra_data.get("new_status") or extra_data.get("status") or "").lower()
    mapping = {
        "sea_booking_created": "booking_received",
        "booking_created": "booking_received",
        "shipment_order_created": "booking_received",
        "manual_cargo_intake_created": "booking_received",
        "manual_cargo_received": "cargo_received",
        "manual_cargo_packing_list_generated": "packed_verified",
        "manual_cargo_ready_for_pickup": "ready_for_pickup",
        "manual_cargo_collected": "completed",
        "manual_cargo_finalized": "completed",
        "packing_list_created": "packed_verified",
        "packing_list_submitted": "packed_verified",
        "shipment_details_uploaded": "booking_received",
        "shipment_information_updated": "booking_received",
        "logistics_operation_updated": extra_data.get("logistics_stage"),
        "goods_released": "ready_for_pickup",
        "goods_collected": "completed",
        "container_departed": "departed_china",
        "container_arrived": "destination_arrival",
        "payment_confirmed": "customs_clearance",
    }
    status_mapping = {
        "pending": "booking_received",
        "supplier_contacted": "supplier_contacted",
        "confirmed": "booking_approved",
        "supplier_confirmed": "supplier_confirmed",
        "awaiting_supplier_shipment": "awaiting_supplier_shipment",
        "label_created": "packed_verified",
        "received_at_warehouse": "cargo_received",
        "shipped": "loaded_container",
        "loaded": "loaded_container",
        "sealed": "container_sealed",
        "departed": "departed_china",
        "in_transit": "in_transit",
        "arrived": "destination_arrival",
        "customs_clearance": "customs_clearance",
        "ready_for_pickup": "ready_for_pickup",
        "delivered": "completed",
        "completed": "completed",
    }
    return _stage_payload(status_mapping.get(status) or mapping.get(event_type))


def resolve_current_location(
    events: Iterable[TrackingEvent],
    *,
    origin: Optional[str] = None,
    destination: Optional[str] = None,
) -> Optional[str]:
    """Return the best honest current-location label for a shipment.

    A booking, approval, or other administrative update is not evidence that a
    shipment has reached its destination.  Until a movement event or an
    explicit location is recorded, cargo remains at its origin.  ``In transit``
    is deliberately used instead of inventing a geographic location between
    origin and destination.
    """
    destination_stages = {
        "destination_arrival",
        "customs_clearance",
        "ready_for_pickup",
        "completed",
    }
    transit_stages = {"departed_china", "in_transit"}

    # Callers provide chronological events, but sorting makes the helper safe
    # for the existing service method which returns reverse-chronological rows.
    ordered_events = sorted(
        events, key=lambda event: event.timestamp or 0, reverse=True
    )
    for event in ordered_events:
        extra_data = event.extra_data or {}
        explicit_location = str(extra_data.get("location") or "").strip()
        if explicit_location:
            return explicit_location

        stage = resolve_logistics_stage(event.event_type, extra_data) or {}
        stage_key = stage.get("logistics_stage")
        if stage_key in destination_stages:
            return destination or origin or "Destination"
        if stage_key in transit_stages:
            return "In transit"

        # A recognized pre-departure stage confirms the cargo is still at its
        # origin. Unknown administrative events are ignored so they cannot
        # overwrite a prior movement event.
        if stage_key:
            return origin or "Origin"

    return origin or "Origin"


class TrackingService:
    """Service class to handle tracking events and notifications."""

    @staticmethod
    def create_tracking_event(
        db: Session,
        entity_type: str,
        entity_id: str,
        event_type: str,
        description: str,
        triggered_by: Optional[str] = None,
        extra_data: Optional[Dict] = None,
    ) -> TrackingEvent:
        """Create a new tracking event and trigger associated notifications."""
        display_reference = build_display_reference(entity_type, entity_id)
        event_extra_data = {**(extra_data or {})}
        event_extra_data.setdefault("display_reference", display_reference)
        event_extra_data.setdefault("reference_id", display_reference)

        event = TrackingEvent(
            entity_type=entity_type,
            entity_id=entity_id,
            event_type=event_type,
            description=description,
            triggered_by=triggered_by,
            extra_data=event_extra_data,
        )
        db.add(event)
        db.flush()  # Don't commit here; let the caller commit

        # Trigger notifications based on the event
        NotificationService.trigger_notifications_for_event(
            db, event, entity_type, entity_id, triggered_by
        )

        return event

    @staticmethod
    def get_entity_timeline(
        db: Session, entity_type: str, entity_id: str
    ) -> List[TrackingEvent]:
        """Get all tracking events for a specific entity ordered by timestamp."""
        events = (
            db.query(TrackingEvent)
            .filter(
                TrackingEvent.entity_type == entity_type,
                TrackingEvent.entity_id == entity_id,
            )
            .order_by(TrackingEvent.timestamp.desc())
            .all()
        )

        return events


class NotificationService:
    """Service class to handle notifications."""

    # Define event-to-notification mappings
    EVENT_NOTIFICATION_MAPPING = {
        "booking_created": {
            "type": "booking_confirmation",
            "message_template": (
                "Your express air cargo booking has been created successfully. "
                "Booking ID: {entity_id}"
            ),
            "role_message_templates": {
                "cargo_admin": (
                    "{actor_name} ({actor_role_label}) created a new express air "
                    "cargo booking. Booking ID: {entity_id}"
                ),
                "super_admin": (
                    "{actor_name} ({actor_role_label}) created a new express air "
                    "cargo booking. Booking ID: {entity_id}"
                ),
            },
            "target_roles": ["customer", "sourcing_agent", "cargo_admin"],
        },
        "booking_status_updated": {
            "type": "booking_update",
            "message_template": (
                "Your express air cargo booking status is now: {new_status}"
            ),
            "role_message_templates": {
                "customer": (
                    "{actor_name} ({actor_role_label}) updated your express air "
                    "cargo booking status to: {new_status}."
                ),
                "sourcing_agent": (
                    "{actor_name} ({actor_role_label}) updated booking status to: "
                    "{new_status}."
                ),
                "cargo_admin": (
                    "{actor_name} ({actor_role_label}) updated booking status to: "
                    "{new_status}."
                ),
            },
            "target_roles": ["customer", "sourcing_agent", "cargo_admin"],
        },
        "sea_booking_created": {
            "type": "sea_booking_confirmation",
            "message_template": (
                "Your sea cargo booking has been created successfully. "
                "Sea booking ID: {entity_id}"
            ),
            "role_message_templates": {
                "cargo_admin": (
                    "{actor_name} ({actor_role_label}) created a sea cargo "
                    "booking. Sea booking ID: {entity_id}."
                ),
                "super_admin": (
                    "{actor_name} ({actor_role_label}) created a sea cargo "
                    "booking. Sea booking ID: {entity_id}."
                ),
            },
            "target_roles": ["customer", "sourcing_agent", "cargo_admin"],
        },
        "shipment_order_created": {
            "type": "shipment_order_created",
            "message_template": (
                "New shipment details were submitted by {actor_name} "
                "({actor_role_label}). Order ID: {entity_id}"
            ),
            "target_roles": ["cargo_admin"],
            "priority": "warning",
        },
        "shipment_order_status_updated": {
            "type": "shipment_timeline_update",
            "message_template": (
                "Shipment update: {stage_label}. Current status: {new_status}"
            ),
            "role_message_templates": {
                "customer": (
                    "{actor_name} ({actor_role_label}) updated shipment status "
                    "to: {new_status}. Stage: {stage_label}."
                ),
                "sourcing_agent": (
                    "{actor_name} ({actor_role_label}) updated shipment status "
                    "to: {new_status}. Stage: {stage_label}."
                ),
            },
            "target_roles": ["customer", "sourcing_agent"],
        },
        "logistics_operation_updated": {
            "type": "shipment_timeline_update",
            "message_template": (
                "{actor_name} ({actor_role_label}) updated shipment operation: "
                "{stage_label}. {public_note}"
            ),
            "target_roles": ["customer", "sourcing_agent", "cargo_admin"],
        },
        "shipment_issue_reported": {
            "type": "shipment_issue",
            "message_template": (
                "{actor_name} ({actor_role_label}) reported a shipment issue: "
                "{stage_label}. {public_note}"
            ),
            "target_roles": ["customer", "sourcing_agent", "cargo_admin"],
            "priority": "warning",
        },
        "goods_held": {
            "type": "goods_status_update",
            "message_template": (
                "{actor_name} ({actor_role_label}) held your goods for review. "
                "Reason: {hold_reason}"
            ),
            "target_roles": ["customer"],
        },
        "goods_released": {
            "type": "goods_status_update",
            "message_template": (
                "{actor_name} ({actor_role_label}) released your goods. They "
                "are ready for collection."
            ),
            "target_roles": ["customer"],
        },
        "goods_collected": {
            "type": "goods_status_update",
            "message_template": (
                "{actor_name} ({actor_role_label}) marked your goods as " "collected."
            ),
            "target_roles": ["customer"],
        },
        "container_created": {
            "type": "container_update",
            "message_template": (
                "{actor_name} ({actor_role_label}) created container {entity_id}. "
                "Current status: {status}."
            ),
            "target_roles": ["cargo_admin"],
        },
        "container_status_updated": {
            "type": "container_update",
            "message_template": (
                "{actor_name} ({actor_role_label}) changed container status "
                "from {old_status} to {new_status}."
            ),
            "target_roles": ["cargo_admin", "customer"],
        },
        "container_departed": {
            "type": "shipment_update",
            "message_template": (
                "{actor_name} ({actor_role_label}) marked container "
                "{entity_id} as departed."
            ),
            "target_roles": ["customer", "cargo_admin"],
        },
        "container_arrived": {
            "type": "shipment_update",
            "message_template": (
                "{actor_name} ({actor_role_label}) marked container "
                "{entity_id} as arrived at destination port."
            ),
            "target_roles": ["customer", "cargo_admin"],
        },
        "packing_list_created": {
            "type": "packing_list_submitted",
            "message_template": (
                "A packing list was submitted for batch {batch_title}. "
                "Packing list: {packing_list_name}"
            ),
            "target_roles": ["cargo_admin"],
            "priority": "warning",
        },
        "shipment_details_uploaded": {
            "type": "shipment_details_uploaded",
            "message_template": (
                "Shipment details were uploaded for {order_description}."
            ),
            "target_roles": ["cargo_admin"],
            "priority": "warning",
        },
        "shipment_information_updated": {
            "type": "shipment_information_updated",
            "message_template": (
                "Shipment information was updated for {order_description}."
            ),
            "target_roles": ["cargo_admin"],
            "priority": "warning",
        },
        "payment_due": {
            "type": "payment_update",
            "message_template": "Payment is now due. Amount: {amount_due}.",
            "target_roles": ["customer"],
            "priority": "warning",
        },
        "payment_confirmed": {
            "type": "payment_update",
            "message_template": (
                "{actor_name} ({actor_role_label}) confirmed payment. "
                "Amount: {amount}."
            ),
            "target_roles": ["customer"],
        },
        "batch_opened": {
            "type": "batch_update",
            "message_template": "Batch {entity_id} is now open for orders.",
            "target_roles": ["sourcing_agent"],
        },
        "batch_closed": {
            "type": "batch_update",
            "message_template": "Batch {entity_id} has been closed for new orders.",
            "target_roles": ["sourcing_agent"],
        },
        "guest_order_created": {
            "type": "order_update",
            "message_template": (
                "Guest order received from {guest_name}. "
                "Order {order_id} total: {total_product_amount}."
            ),
            "target_roles": ["sourcing_agent"],
            "priority": "warning",
        },
    }

    @classmethod
    def trigger_notifications_for_event(
        cls, db, event, entity_type, entity_id, triggered_by
    ):
        """Trigger notifications based on the event type."""
        if event.event_type in cls.EVENT_NOTIFICATION_MAPPING:
            mapping = cls.EVENT_NOTIFICATION_MAPPING[event.event_type]
            display_reference = build_display_reference(
                entity_type, entity_id, event.timestamp
            )
            stage = resolve_logistics_stage(event.event_type, event.extra_data)
            actor_context = cls._resolve_actor_context(db, triggered_by)

            render_context = {
                "entity_id": display_reference,
                "reference_id": display_reference,
                "display_reference": display_reference,
                **actor_context,
            }
            if event.extra_data:
                render_context.update(event.extra_data)
            if stage:
                render_context.update(stage)

            # Determine target users based on entity type and role
            target_users = cls._get_target_users_for_event(
                db, entity_type, entity_id, mapping["target_roles"], triggered_by
            )

            # Create notifications for target users
            for user in target_users:
                role_templates = mapping.get("role_message_templates", {})
                template = role_templates.get(user.role) or mapping["message_template"]
                message = cls._render_message(template, render_context)
                cls.create_notification(
                    db,
                    user.id,
                    mapping["type"],
                    message,
                    mapping.get("priority", "info"),
                    target_type=entity_type,
                    target_id=entity_id,
                )

    @staticmethod
    def _get_target_users_for_event(
        db, entity_type, entity_id, target_roles, triggered_by
    ):
        """Get users who should receive notifications for an event."""
        users = []

        if entity_type == "sea_booking":
            sea_booking = (
                db.query(SeaBooking).filter(SeaBooking.id == entity_id).first()
            )

            if sea_booking and "customer" in target_roles:
                customer = sea_booking.user
                if customer and customer.role == "customer":
                    users.append(customer)

            if sea_booking and (
                "cargo_admin" in target_roles or "sourcing_agent" in target_roles
            ):
                container = sea_booking.container
                if container and "cargo_admin" in target_roles:
                    admin = container.admin
                    if admin:
                        users.append(admin)

                if (
                    "sourcing_agent" in target_roles
                    and sea_booking.user
                    and sea_booking.user.role == "sourcing_agent"
                ):
                    users.append(sea_booking.user)

        elif entity_type == "booking":
            booking = (
                db.query(ExpressAirCargoBooking)
                .filter(ExpressAirCargoBooking.id == entity_id)
                .first()
            )

            if booking:
                if "customer" in target_roles and booking.customer:
                    users.append(booking.customer)

                if "sourcing_agent" in target_roles and booking.sourcing_agent:
                    users.append(booking.sourcing_agent)

                if "cargo_admin" in target_roles:
                    if booking.cargo_admin:
                        users.append(booking.cargo_admin)
                    else:
                        from app.models.user import User

                        cargo_admins = (
                            db.query(User).filter(User.role == "cargo_admin").all()
                        )
                        users.extend(cargo_admins)

        elif entity_type == "container":
            from app.models.container import Container

            container = db.query(Container).filter(Container.id == entity_id).first()

            if container and "cargo_admin" in target_roles:
                admin = container.admin
                if admin:
                    users.append(admin)

            # Add all customers with sea_bookings in this container
            if "customer" in target_roles:
                sea_bookings = (
                    db.query(SeaBooking)
                    .filter(SeaBooking.container_id == entity_id)
                    .all()
                )

                for sea_booking in sea_bookings:
                    if sea_booking.user:
                        users.append(sea_booking.user)

        elif entity_type == "shipment_order":
            from app.models.shipment_orders import ShipmentOrder

            shipment_order = (
                db.query(ShipmentOrder).filter(ShipmentOrder.id == entity_id).first()
            )

            if shipment_order and "customer" in target_roles:
                customer = shipment_order.created_by_user
                if customer:
                    users.append(customer)

            # Check if shipment order is linked to a sea_booking
            # from a sourcing agent's batch.
            if shipment_order and "sourcing_agent" in target_roles:
                if shipment_order.sea_booking_id:
                    # Get the sea_booking
                    sea_booking = (
                        db.query(SeaBooking)
                        .filter(SeaBooking.id == shipment_order.sea_booking_id)
                        .first()
                    )
                    if (
                        sea_booking
                        and sea_booking.source_type == "batch"
                        and sea_booking.source_id
                    ):
                        # Get the batch
                        from app.models.sourcing import SourcingBatch

                        batch = (
                            db.query(SourcingBatch)
                            .filter(SourcingBatch.id == sea_booking.source_id)
                            .first()
                        )
                        if (
                            batch
                            and batch.agent
                            and batch.agent.role == "sourcing_agent"
                        ):
                            users.append(batch.agent)

            if shipment_order and "cargo_admin" in target_roles:
                from app.models.user import User

                cargo_admin_ids = set()
                if shipment_order.air_booking_id:
                    booking = (
                        db.query(ExpressAirCargoBooking)
                        .filter(
                            ExpressAirCargoBooking.id == shipment_order.air_booking_id
                        )
                        .first()
                    )
                    if booking and booking.cargo_admin:
                        cargo_admin_ids.add(booking.cargo_admin.id)
                if shipment_order.sea_booking_id:
                    sea_booking = (
                        db.query(SeaBooking)
                        .filter(SeaBooking.id == shipment_order.sea_booking_id)
                        .first()
                    )
                    if (
                        sea_booking
                        and sea_booking.container
                        and sea_booking.container.admin
                    ):
                        cargo_admin_ids.add(sea_booking.container.admin.id)
                if cargo_admin_ids:
                    users.extend(
                        db.query(User).filter(User.id.in_(cargo_admin_ids)).all()
                    )
                else:
                    users.extend(
                        db.query(User).filter(User.role == "cargo_admin").all()
                    )

        elif entity_type == "batch":
            from app.models.sourcing import SourcingBatch

            batch = (
                db.query(SourcingBatch).filter(SourcingBatch.id == entity_id).first()
            )
            if (
                batch
                and "sourcing_agent" in target_roles
                and batch.agent
                and batch.agent.role == "sourcing_agent"
            ):
                users.append(batch.agent)
            if batch and "cargo_admin" in target_roles:
                from app.models.user import User

                users.extend(db.query(User).filter(User.role == "cargo_admin").all())

        unique = {}
        for user in users:
            unique[str(user.id)] = user
        return list(unique.values())

    @staticmethod
    def create_notification(
        db: Session,
        user_id: str,
        notification_type: str,
        message: str,
        priority: str = "info",
        target_type: str | None = None,
        target_id: str | None = None,
    ) -> Notification:
        """Create a new notification for a user."""
        notification = create_notification(
            db=db,
            user_id=user_id,
            notification_type=notification_type,
            message=message,
            priority=priority,
            target_type=target_type,
            target_id=target_id,
        )

        return notification

    @staticmethod
    def create_notifications_for_role(
        db: Session,
        role: str,
        notification_type: str,
        message: str,
        priority: str = "info",
        exclude_user_id: Optional[str] = None,
        target_type: Optional[str] = None,
        target_id: Optional[str] = None,
    ):
        """Create notifications for all users with a specific role."""
        from app.models.user import User

        query = db.query(User).filter(User.role == role)
        if exclude_user_id:
            query = query.filter(User.id != exclude_user_id)

        users = query.all()

        notifications = []
        for user in users:
            notification = create_notification(
                db=db,
                user_id=user.id,
                notification_type=notification_type,
                message=message,
                priority=priority,
                target_type=target_type,
                target_id=target_id,
            )
            notifications.append(notification)
        return notifications

    @staticmethod
    def send_whatsapp_notification(db: Session, user_id: str, message: str):
        """WhatsApp notifications are intentionally disabled."""
        return False

    @staticmethod
    def _role_label(role: Optional[str]) -> str:
        labels = {
            "customer": "Customer",
            "sourcing_agent": "Sourcing Agent",
            "cargo_admin": "Cargo Admin",
            "super_admin": "Super Admin",
        }
        if not role:
            return "User"
        return labels.get(role, str(role).replace("_", " ").title())

    @classmethod
    def _resolve_actor_context(
        cls, db: Session, triggered_by: Optional[str]
    ) -> Dict[str, str]:
        if not triggered_by:
            return {
                "actor_id": "",
                "actor_name": "System",
                "actor_role": "system",
                "actor_role_label": "System",
            }

        from app.models.user import User

        actor = db.query(User).filter(User.id == triggered_by).first()
        if not actor:
            return {
                "actor_id": str(triggered_by),
                "actor_name": "System",
                "actor_role": "system",
                "actor_role_label": "System",
            }

        actor_name = (actor.name or "").strip() or "Unknown User"
        actor_role = (actor.role or "").strip() or "user"
        return {
            "actor_id": str(actor.id),
            "actor_name": actor_name,
            "actor_role": actor_role,
            "actor_role_label": cls._role_label(actor_role),
        }

    @staticmethod
    def _render_message(template: str, context: Dict) -> str:
        message = template
        for key, value in context.items():
            message = message.replace(f"{{{key}}}", "" if value is None else str(value))
        return message
