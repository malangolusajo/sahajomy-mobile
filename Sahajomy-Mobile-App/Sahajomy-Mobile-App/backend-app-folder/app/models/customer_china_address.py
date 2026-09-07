"""Persistent customer-specific China delivery addresses."""

import uuid
from datetime import datetime

from app.database import Base
from sqlalchemy import (
    CheckConstraint,
    Column,
    DateTime,
    ForeignKey,
    String,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship


class CustomerChinaAddress(Base):
    __tablename__ = "customer_china_addresses"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    customer_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    cargo_admin_id = Column(
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
    cargo_mode = Column(String(8), nullable=False)
    shipping_mark = Column(String(16), nullable=False)
    destination_country = Column(String(100), nullable=False)
    destination_city = Column(String(120), nullable=False)
    status = Column(String(16), nullable=False, default="active")
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )

    __table_args__ = (
        UniqueConstraint(
            "shipping_mark", name="uq_customer_china_addresses_shipping_mark"
        ),
        UniqueConstraint(
            "customer_id",
            "warehouse_id",
            "cargo_mode",
            name="uq_customer_china_address_customer_warehouse_mode",
        ),
        CheckConstraint(
            "cargo_mode IN ('sea','air')", name="chk_customer_china_address_mode"
        ),
        CheckConstraint(
            "status IN ('active','inactive')", name="chk_customer_china_address_status"
        ),
    )

    customer = relationship("User", foreign_keys=[customer_id])
    cargo_admin = relationship("User", foreign_keys=[cargo_admin_id])
    warehouse = relationship("Warehouse")
