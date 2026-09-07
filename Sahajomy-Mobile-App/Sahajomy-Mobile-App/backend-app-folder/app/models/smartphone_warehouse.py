"""Branch-scoped smartphone warehouse automation records."""

import uuid
from datetime import datetime

from app.database import Base
from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import relationship


class WarehouseParcel(Base):
    __tablename__ = "warehouse_parcels"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    company_id = Column(
        UUID(as_uuid=True),
        ForeignKey("cargo_companies.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    branch_id = Column(
        UUID(as_uuid=True),
        ForeignKey("cargo_branches.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    warehouse_id = Column(
        UUID(as_uuid=True),
        ForeignKey("warehouses.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    customer_id = Column(
        UUID(as_uuid=True),
        ForeignKey("cargo_customers.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    intake_id = Column(
        UUID(as_uuid=True),
        ForeignKey("manual_cargo_intakes.id", ondelete="SET NULL"),
        unique=True,
        index=True,
    )
    parcel_code = Column(String(48), nullable=False)
    tracking_number = Column(String(100), index=True)
    shipping_mark = Column(String(100), index=True)
    carrier = Column(String(120))
    condition = Column(String(24), nullable=False, default="good")
    status = Column(String(24), nullable=False, default="received", index=True)
    carton_count = Column(Integer, nullable=False, default=1)
    weight_kg = Column(Numeric(16, 3), nullable=False, default=0)
    length_cm = Column(Numeric(16, 3), nullable=False, default=0)
    width_cm = Column(Numeric(16, 3), nullable=False, default=0)
    height_cm = Column(Numeric(16, 3), nullable=False, default=0)
    cbm = Column(Numeric(16, 6), nullable=False, default=0)
    photo_urls = Column(JSONB, nullable=False, default=list, server_default="[]")
    notes = Column(Text)
    received_by_id = Column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL")
    )
    received_at = Column(DateTime, nullable=False, default=datetime.utcnow, index=True)
    updated_at = Column(
        DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow
    )
    __table_args__ = (
        UniqueConstraint(
            "company_id", "parcel_code", name="uq_warehouse_parcel_company_code"
        ),
        CheckConstraint(
            "condition IN ('good','damaged','wet','opened','unknown')",
            name="chk_warehouse_parcel_condition",
        ),
        CheckConstraint(
            "status IN ('received','booked','loading','loaded','in_transit','arrived','ready','collected','held')",
            name="chk_warehouse_parcel_status",
        ),
    )
    customer = relationship("CargoCustomer")
    warehouse = relationship("Warehouse")


class ParcelScanEvent(Base):
    __tablename__ = "parcel_scan_events"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    company_id = Column(
        UUID(as_uuid=True),
        ForeignKey("cargo_companies.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    branch_id = Column(
        UUID(as_uuid=True),
        ForeignKey("cargo_branches.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    warehouse_id = Column(
        UUID(as_uuid=True),
        ForeignKey("warehouses.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    parcel_id = Column(
        UUID(as_uuid=True),
        ForeignKey("warehouse_parcels.id", ondelete="SET NULL"),
        index=True,
    )
    raw_code = Column(String(4000), nullable=False)
    normalized_code = Column(String(120), nullable=False, index=True)
    result = Column(String(20), nullable=False, index=True)
    confidence = Column(Numeric(5, 2), nullable=False, default=0)
    metadata_json = Column(JSONB, nullable=False, default=dict, server_default="{}")
    idempotency_key = Column(String(80), nullable=False)
    scanned_by_id = Column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL")
    )
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow, index=True)
    __table_args__ = (
        UniqueConstraint(
            "company_id", "idempotency_key", name="uq_parcel_scan_company_idempotency"
        ),
        CheckConstraint(
            "result IN ('matched','unmatched','duplicate','invalid')",
            name="chk_parcel_scan_result",
        ),
    )


class ParcelBookingLink(Base):
    __tablename__ = "parcel_booking_links"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    company_id = Column(
        UUID(as_uuid=True),
        ForeignKey("cargo_companies.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    parcel_id = Column(
        UUID(as_uuid=True),
        ForeignKey("warehouse_parcels.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    booking_type = Column(String(16), nullable=False)
    booking_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    linked_by_id = Column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL")
    )
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    __table_args__ = (
        UniqueConstraint(
            "parcel_id", "booking_type", "booking_id", name="uq_parcel_booking_link"
        ),
        CheckConstraint(
            "booking_type IN ('sea','air','shipment')", name="chk_parcel_booking_type"
        ),
    )


class LoadingSession(Base):
    __tablename__ = "warehouse_loading_sessions"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    company_id = Column(
        UUID(as_uuid=True),
        ForeignKey("cargo_companies.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    branch_id = Column(
        UUID(as_uuid=True),
        ForeignKey("cargo_branches.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    booking_type = Column(String(16), nullable=False)
    booking_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    reference = Column(String(100), nullable=False)
    status = Column(String(16), nullable=False, default="open", index=True)
    started_by_id = Column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL")
    )
    started_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    completed_at = Column(DateTime)
    __table_args__ = (
        CheckConstraint(
            "status IN ('open','completed','cancelled')",
            name="chk_loading_session_status",
        ),
    )


class LoadingScan(Base):
    __tablename__ = "warehouse_loading_scans"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    session_id = Column(
        UUID(as_uuid=True),
        ForeignKey("warehouse_loading_sessions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    parcel_id = Column(
        UUID(as_uuid=True),
        ForeignKey("warehouse_parcels.id", ondelete="SET NULL"),
        index=True,
    )
    scanned_code = Column(String(120), nullable=False)
    result = Column(String(16), nullable=False)
    message = Column(String(300), nullable=False)
    scanned_by_id = Column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL")
    )
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    __table_args__ = (
        CheckConstraint(
            "result IN ('green','red','amber','duplicate')",
            name="chk_loading_scan_result",
        ),
    )


class ShipmentMilestone(Base):
    __tablename__ = "warehouse_shipment_milestones"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    company_id = Column(
        UUID(as_uuid=True),
        ForeignKey("cargo_companies.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    branch_id = Column(
        UUID(as_uuid=True),
        ForeignKey("cargo_branches.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    booking_type = Column(String(16), nullable=False)
    booking_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    milestone = Column(String(40), nullable=False)
    location = Column(String(160))
    note = Column(Text)
    occurred_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    created_by_id = Column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL")
    )
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
