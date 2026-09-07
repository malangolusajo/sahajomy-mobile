"""Optional warehouse-automation records built on top of manual cargo intake."""

import uuid
from datetime import datetime

from app.database import Base
from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Column,
    DateTime,
    ForeignKey,
    String,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship


class CargoAdminFeatureEntitlement(Base):
    """Future-billing-ready feature flags for a Cargo Admin account."""

    __tablename__ = "cargo_admin_feature_entitlements"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    cargo_admin_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    warehouse_automation_enabled = Column(
        Boolean, nullable=False, default=False, server_default="false"
    )
    updated_by_id = Column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(
        DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    __table_args__ = (
        UniqueConstraint(
            "cargo_admin_id", name="uq_cargo_admin_feature_entitlement_admin"
        ),
    )


class WarehouseCollectionRequest(Base):
    """Short-lived, single-use handover authorization; never stores a raw code."""

    __tablename__ = "warehouse_collection_requests"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    cargo_admin_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    customer_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    warehouse_id = Column(
        UUID(as_uuid=True),
        ForeignKey("warehouses.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    token_hash = Column(String(64), nullable=False)
    # PINs are unique only among currently active requests for one operator.
    # They must be reusable after expiry; a global unique constraint would
    # permanently exhaust the six-digit PIN space.
    pin_hash = Column(String(64), nullable=False, index=True)
    status = Column(String(16), nullable=False, default="requested", index=True)
    expires_at = Column(DateTime, nullable=False, index=True)
    used_at = Column(DateTime, nullable=True)
    used_by_id = Column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    __table_args__ = (
        UniqueConstraint("token_hash", name="uq_warehouse_collection_request_token"),
        CheckConstraint(
            "status IN ('requested','used','expired','cancelled')",
            name="chk_warehouse_collection_request_status",
        ),
    )

    items = relationship(
        "WarehouseCollectionRequestItem",
        back_populates="request",
        cascade="all, delete-orphan",
    )


class WarehouseCollectionRequestItem(Base):
    __tablename__ = "warehouse_collection_request_items"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    collection_request_id = Column(
        UUID(as_uuid=True),
        ForeignKey("warehouse_collection_requests.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    intake_id = Column(
        UUID(as_uuid=True),
        ForeignKey("manual_cargo_intakes.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )

    __table_args__ = (
        UniqueConstraint(
            "collection_request_id", "intake_id", name="uq_collection_request_intake"
        ),
    )

    request = relationship("WarehouseCollectionRequest", back_populates="items")
    intake = relationship("ManualCargoIntake")
