"""Express air cargo booking models."""

import uuid
from datetime import datetime

from app.database import Base
from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Column,
    DateTime,
    ForeignKey,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship


class ExpressAirCargoBooking(Base):
    """Air cargo booking supporting both customers and sourcing agents."""

    __tablename__ = "express_air_cargo_bookings"

    # ─── Primary ─────────────────────────────
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # ─── Ownership (Flexible) ────────────────
    customer_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=True,  # ✅ allow sourcing agent bookings
        index=True,
    )

    sourcing_agent_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    # ─── Cargo Admin Assignment ──────────────
    cargo_admin_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    # Optional for legacy bookings. It records the forwarding warehouse/address
    # chosen after the cargo operator has been assigned.
    warehouse_id = Column(
        UUID(as_uuid=True),
        ForeignKey("warehouses.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    customer_china_address_id = Column(
        UUID(as_uuid=True),
        ForeignKey("customer_china_addresses.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    # ─── Link to Batch (NEW) ─────────────────
    batch_id = Column(
        UUID(as_uuid=True),
        ForeignKey("sourcing_batches.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    # ─── Cargo Info ─────────────────────────
    cargo_type_id = Column(
        UUID(as_uuid=True), ForeignKey("goods_types.id"), nullable=False
    )

    # The selected operational rate is retained separately from its financial
    # snapshot so future rate changes do not rewrite a submitted booking.
    air_cargo_rate_id = Column(
        UUID(as_uuid=True),
        ForeignKey("air_cargo_rates.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    pricing_type = Column(String(12), nullable=True)
    rate_amount = Column(Numeric(12, 2), nullable=True)
    rate_currency = Column(String(3), nullable=True)
    quantity = Column(Numeric(10, 2), nullable=True)
    quoted_total = Column(Numeric(14, 2), nullable=True)

    cargo_description = Column(Text, nullable=True)

    weight_kg = Column(Numeric(10, 2), nullable=False)

    shipment_date = Column(DateTime, nullable=False)

    photo_urls = Column(Text, nullable=True)  # JSON list

    # ─── Shipping Labels (NEW FEATURE) ───────
    tracking_number = Column(String(100), unique=True, index=True, nullable=True)

    airway_bill_number = Column(String(100), unique=True, index=True, nullable=True)

    shipping_label_url = Column(Text, nullable=True)  # PDF or image

    # ─── Service Info ───────────────────────
    route_label = Column(String(120), nullable=False, default="China → Africa")

    service_label = Column(String(150), nullable=False, default="24 Hour Air Delivery")

    status = Column(String(20), nullable=False, default="pending", index=True)

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # ─── Constraints ────────────────────────
    __table_args__ = (
        CheckConstraint("weight_kg > 0", name="chk_express_booking_weight_positive"),
        CheckConstraint(
            "status IN ('pending','confirmed','label_created','in_transit','delivered','cancelled')",
            name="chk_express_booking_status",
        ),
    )

    # ─── Relationships with EXPLICIT foreign_keys ──────────────────────

    # Customer relationship - explicit foreign key
    customer = relationship(
        "User",
        foreign_keys=[customer_id],
        back_populates="express_air_bookings_as_customer",
    )

    # Sourcing agent relationship - explicit foreign key
    sourcing_agent = relationship(
        "User",
        foreign_keys=[sourcing_agent_id],
        back_populates="express_air_bookings_as_agent",
    )

    # Cargo admin relationship - explicit foreign key
    cargo_admin = relationship(
        "User",
        foreign_keys=[cargo_admin_id],
        back_populates="express_air_bookings_as_admin",
    )
    warehouse = relationship("Warehouse", foreign_keys=[warehouse_id])
    customer_china_address = relationship("CustomerChinaAddress")

    cargo_type = relationship("GoodsType", back_populates="express_air_bookings")

    air_cargo_rate = relationship("AirCargoRate", back_populates="bookings")

    batch = relationship("SourcingBatch", back_populates="air_bookings")

    shipping_mark = relationship(
        "ShippingMark", back_populates="air_booking", uselist=False
    )


class AirDepartureSchedule(Base):
    """A cargo-admin published departure, independent of customer booking requests."""

    __tablename__ = "air_departure_schedules"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    cargo_admin_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    route_label = Column(String(120), nullable=False, default="China → Africa")
    service_label = Column(String(150), nullable=False, default="Express Air Cargo")
    departure_at = Column(DateTime, nullable=False, index=True)
    booking_cutoff_at = Column(DateTime, nullable=True)
    # A one-time schedule has no frequency. Recurring schedules reuse the
    # departure date/time as their template and publish future occurrences.
    recurrence_frequency = Column(String(10), nullable=True)
    recurrence_weekdays = Column(String(20), nullable=True)
    recurrence_until = Column(DateTime, nullable=True)
    capacity_kg = Column(Numeric(12, 2), nullable=True)
    available_capacity_kg = Column(Numeric(12, 2), nullable=True)
    status = Column(String(20), nullable=False, default="open", index=True)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )

    __table_args__ = (
        CheckConstraint(
            "status IN ('open','filling_fast','closed','cancelled','departed')",
            name="chk_air_departure_schedule_status",
        ),
        CheckConstraint(
            "capacity_kg IS NULL OR capacity_kg > 0",
            name="chk_air_departure_schedule_capacity_positive",
        ),
        CheckConstraint(
            "available_capacity_kg IS NULL OR available_capacity_kg >= 0",
            name="chk_air_departure_schedule_available_nonnegative",
        ),
        CheckConstraint(
            "capacity_kg IS NULL OR available_capacity_kg IS NULL OR available_capacity_kg <= capacity_kg",
            name="chk_air_departure_schedule_available_within_capacity",
        ),
        CheckConstraint(
            "booking_cutoff_at IS NULL OR booking_cutoff_at <= departure_at",
            name="chk_air_departure_schedule_cutoff_before_departure",
        ),
        CheckConstraint(
            "recurrence_frequency IS NULL OR recurrence_frequency IN ('weekly','monthly','yearly')",
            name="chk_air_departure_schedule_recurrence_frequency",
        ),
    )


class AirCargoRate(Base):
    """Operational air-cargo price for one existing master GoodsType."""

    __tablename__ = "air_cargo_rates"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    cargo_admin_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    goods_type_id = Column(
        UUID(as_uuid=True),
        ForeignKey("goods_types.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    route = Column(String(120), nullable=False, default="China → Africa")
    shipping_method = Column(String(50), nullable=False)
    pricing_type = Column(String(12), nullable=False)  # per_kg | per_unit
    price = Column(Numeric(12, 2), nullable=False)
    currency = Column(String(3), nullable=False, default="USD")
    transit_time = Column(String(80), nullable=False)
    restrictions = Column(Text, nullable=True)
    condition_label = Column(String(150), nullable=False, default="", server_default="")
    minimum_weight_kg = Column(Numeric(10, 2), nullable=True)
    maximum_weight_kg = Column(Numeric(10, 2), nullable=True)
    is_active = Column(Boolean, nullable=False, default=True, index=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )

    __table_args__ = (
        UniqueConstraint(
            "cargo_admin_id",
            "goods_type_id",
            "route",
            "shipping_method",
            "pricing_type",
            "condition_label",
            name="uq_air_cargo_rate_provider_goods_route_method_condition",
        ),
        CheckConstraint("price > 0", name="chk_air_cargo_rate_price_positive"),
        CheckConstraint(
            "pricing_type IN ('per_kg','per_unit')",
            name="chk_air_cargo_rate_pricing_type",
        ),
        CheckConstraint(
            "currency IN ('USD','TZS','RMB')", name="chk_air_cargo_rate_currency"
        ),
        CheckConstraint(
            "minimum_weight_kg IS NULL OR minimum_weight_kg > 0",
            name="chk_air_cargo_rate_min_weight_positive",
        ),
        CheckConstraint(
            "maximum_weight_kg IS NULL OR maximum_weight_kg > 0",
            name="chk_air_cargo_rate_max_weight_positive",
        ),
        CheckConstraint(
            "minimum_weight_kg IS NULL OR maximum_weight_kg IS NULL OR minimum_weight_kg <= maximum_weight_kg",
            name="chk_air_cargo_rate_weight_range",
        ),
    )

    goods_type = relationship("GoodsType", back_populates="air_cargo_rates")
    cargo_admin = relationship("User", foreign_keys=[cargo_admin_id])
    bookings = relationship("ExpressAirCargoBooking", back_populates="air_cargo_rate")


class AirCargoGoodsTypeRequest(Base):
    """A rate-card item requiring Super Admin mapping to a master GoodsType."""

    __tablename__ = "air_cargo_goods_type_requests"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    requested_name = Column(String(150), nullable=False)
    normalized_name = Column(String(150), nullable=False, index=True)
    source = Column(String(100), nullable=False, default="Air Cargo Rate Setup")
    status = Column(String(20), nullable=False, default="pending", index=True)
    suggested_goods_type_id = Column(
        UUID(as_uuid=True),
        ForeignKey("goods_types.id", ondelete="SET NULL"),
        nullable=True,
    )
    resolved_goods_type_id = Column(
        UUID(as_uuid=True),
        ForeignKey("goods_types.id", ondelete="SET NULL"),
        nullable=True,
    )
    reviewed_by_id = Column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    review_note = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    reviewed_at = Column(DateTime, nullable=True)

    __table_args__ = (
        CheckConstraint(
            "status IN ('pending','approved','rejected')",
            name="chk_air_cargo_goods_request_status",
        ),
    )

    suggested_goods_type = relationship(
        "GoodsType", foreign_keys=[suggested_goods_type_id]
    )
    resolved_goods_type = relationship(
        "GoodsType", foreign_keys=[resolved_goods_type_id]
    )
    reviewed_by = relationship("User", foreign_keys=[reviewed_by_id])
