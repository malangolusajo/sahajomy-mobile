"""Shipping mark model for air and sea bookings."""

import uuid
from datetime import datetime

from app.database import Base
from sqlalchemy import (
    Column,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship


class ShippingMark(Base):
    __tablename__ = "shipping_marks"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    booking_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    shipping_mark_code = Column(String(64), nullable=False, unique=True, index=True)
    cargo_type = Column(String(10), nullable=False, index=True)  # AIR | SEA
    customer_name = Column(String(150), nullable=True)
    customer_phone = Column(String(30), nullable=True)
    destination_region = Column(String(120), nullable=False)
    packing_list_summary = Column(Text, nullable=True)
    carton_count = Column(Integer, nullable=False, default=1)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Optional strict references so both booking modules can link to shipping marks.
    air_booking_id = Column(
        UUID(as_uuid=True),
        ForeignKey("express_air_cargo_bookings.id", ondelete="CASCADE"),
        nullable=True,
        unique=True,
    )
    sea_booking_id = Column(
        UUID(as_uuid=True),
        ForeignKey("sea_bookings.id", ondelete="CASCADE"),
        nullable=True,
        unique=True,
    )

    air_booking = relationship("ExpressAirCargoBooking", back_populates="shipping_mark")
    sea_booking = relationship(
        "SeaBooking", back_populates="shipping_mark"
    )

    __table_args__ = (
        UniqueConstraint(
            "cargo_type", "booking_id", name="uq_shipping_marks_booking_type"
        ),
    )
