import enum
import uuid
from datetime import datetime

from app.core.reference_ids import build_display_reference
from app.database import Base  # Fixed import to use same Base as other models
from sqlalchemy import Boolean, CheckConstraint, Column, DateTime
from sqlalchemy import Enum as SQLEnum
from sqlalchemy import ForeignKey, Index, Numeric, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship


class ShipmentOrderStatus(str, enum.Enum):
    pending = "pending"
    supplier_contacted = "supplier_contacted"
    confirmed = "confirmed"
    shipped = "shipped"
    received_at_warehouse = "received_at_warehouse"


class ShipmentOrder(Base):
    __tablename__ = "shipment_orders"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    created_by_user_id = Column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    supplier_name = Column(String, nullable=True)
    supplier_contact = Column(String, nullable=True)
    supplier_reference = Column(String, nullable=True)
    order_description = Column(Text, nullable=True)
    order_value = Column(
        Numeric(20, 2), nullable=True
    )  # Changed from String to Numeric for proper currency handling
    currency = Column(
        String(3), nullable=True, default="TZS"
    )  # Currency code: TZS, RMB, or USD
    status = Column(
        SQLEnum(ShipmentOrderStatus),
        default=ShipmentOrderStatus.pending,
        nullable=False,
    )
    tracking_number = Column(String, nullable=True)
    notes = Column(Text, nullable=True)
    has_attachments = Column(Boolean, default=False, nullable=True)

    # Foreign keys to connect to either container or air cargo booking
    sea_booking_id = Column(
        UUID(as_uuid=True), ForeignKey("sea_bookings.id"), nullable=True
    )
    air_booking_id = Column(
        UUID(as_uuid=True), ForeignKey("express_air_cargo_bookings.id"), nullable=True
    )

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    @property
    def display_reference(self):
        return build_display_reference("shipment_order", self.id, self.created_at)

    @property
    def reference_id(self):
        return self.display_reference

    # ================= RELATIONSHIPS =================

    # User who created this shipment order (customer)
    created_by_user = relationship(
        "User",
        back_populates="shipment_orders_created",
        foreign_keys=[created_by_user_id],
    )
    sea_booking = relationship("SeaBooking")
    air_booking = relationship("ExpressAirCargoBooking")

    @property
    def customer_display_name(self) -> str:
        name = (
            self.created_by_user.name.strip()
            if self.created_by_user and self.created_by_user.name
            else ""
        )
        return name or "Customer name not available"

    @property
    def customer_phone(self) -> str | None:
        if self.created_by_user and self.created_by_user.phone_number:
            return self.created_by_user.phone_number
        return None

    @property
    def cargo_mode(self) -> str:
        return "air" if self.air_booking_id and not self.sea_booking_id else "sea"

    @property
    def destination_region(self) -> str | None:
        if self.air_booking and self.air_booking.shipping_mark:
            return self.air_booking.shipping_mark.destination_region
        if self.sea_booking and self.sea_booking.shipping_mark:
            return self.sea_booking.shipping_mark.destination_region
        if self.air_booking and self.air_booking.route_label:
            parts = [part.strip() for part in self.air_booking.route_label.split("→")]
            if len(parts) >= 2:
                return parts[1]
        if (
            self.sea_booking
            and self.sea_booking.container
            and self.sea_booking.container.route
        ):
            return self.sea_booking.container.route.destination
        return None

    @property
    def origin_region(self) -> str | None:
        if self.air_booking and self.air_booking.route_label:
            parts = [part.strip() for part in self.air_booking.route_label.split("→")]
            if parts and parts[0]:
                return parts[0]
        if self.sea_booking and self.sea_booking.container:
            container = self.sea_booking.container
            if container.route and container.route.origin:
                return container.route.origin
            if container.origin_warehouse:
                return (
                    container.origin_warehouse.city
                    or container.origin_warehouse.location
                    or container.origin_warehouse.name
                )
        return None

    @property
    def service_reference(self) -> str | None:
        if self.air_booking:
            return build_display_reference(
                "air_booking", self.air_booking.id, self.air_booking.created_at
            )
        if self.sea_booking and self.sea_booking.container:
            container = self.sea_booking.container
            return build_display_reference(
                "container", container.id, container.created_at
            )
        return None

    @property
    def service_label(self) -> str | None:
        if self.air_booking:
            return self.air_booking.service_label or "Express Air Cargo"
        if self.sea_booking and self.sea_booking.container:
            size = self.sea_booking.container.container_size or "Sea"
            return f"{size} container"
        return None

    @property
    def payment_status(self) -> str | None:
        if self.sea_booking:
            return self.sea_booking.payment_status
        return None

    @property
    def cargo_type_name(self) -> str:
        if self.air_booking and self.air_booking.cargo_type:
            return self.air_booking.cargo_type.name
        return "Sea Cargo" if self.cargo_mode == "sea" else "Air Cargo"

    @property
    def cbm_booked(self) -> float | None:
        if self.sea_booking and self.sea_booking.cbm_booked is not None:
            return float(self.sea_booking.cbm_booked)
        return None

    @property
    def carton_count(self) -> int | None:
        if self.air_booking and self.air_booking.shipping_mark:
            return self.air_booking.shipping_mark.carton_count
        if self.sea_booking and self.sea_booking.shipping_mark:
            return self.sea_booking.shipping_mark.carton_count
        return None

    @property
    def shipping_mark_code(self) -> str | None:
        if self.air_booking and self.air_booking.shipping_mark:
            return self.air_booking.shipping_mark.shipping_mark_code
        if self.sea_booking and self.sea_booking.shipping_mark:
            return self.sea_booking.shipping_mark.shipping_mark_code
        return None

    @property
    def shipping_label_available(self) -> bool:
        return self.shipping_mark_code is not None

    @property
    def shipping_label_path(self) -> str | None:
        if self.air_booking_id:
            return f"/label/air/{self.air_booking_id}"
        if self.sea_booking_id:
            return f"/label/sea/{self.sea_booking_id}"
        return None

    __table_args__ = (
        CheckConstraint(
            "currency IN ('TZS', 'RMB', 'USD')", name="chk_shipment_order_currency"
        ),
        Index(
            "uq_shipment_orders_tracking_number",
            "tracking_number",
            unique=True,
            postgresql_where=tracking_number.isnot(None),
        ),
        Index(
            "uq_shipment_orders_sea_booking",
            "sea_booking_id",
            unique=True,
            postgresql_where=sea_booking_id.isnot(None),
        ),
        Index(
            "uq_shipment_orders_air_booking",
            "air_booking_id",
            unique=True,
            postgresql_where=air_booking_id.isnot(None),
        ),
    )
