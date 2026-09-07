"""Quote requests submitted from the public Full Container Loading flow."""

import uuid
from datetime import datetime

from app.database import Base
from sqlalchemy import (
    CheckConstraint,
    Column,
    DateTime,
    ForeignKey,
    Index,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship


class QuoteRequest(Base):
    """An FCL quotation request assigned to the cargo-admin work queue."""

    __tablename__ = "quote_requests"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    # Public quote requests can be submitted before a customer account exists.
    customer_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    request_type = Column(String(10), nullable=False, default="FCL")
    product = Column(Text, nullable=False)
    specifications = Column(Text, nullable=False)
    supplier_status = Column(String(40), nullable=False)
    incoterm = Column(String(3), nullable=False)
    destination = Column(String(255), nullable=False)
    company_name = Column(String(255), nullable=False)
    business_license = Column(String(255), nullable=False)
    email = Column(String(255), nullable=False)
    whatsapp_number = Column(String(50), nullable=False)
    status = Column(String(30), nullable=False, default="pending")
    assigned_role = Column(String(30), nullable=False, default="cargo_admin")
    assigned_cargo_admin_id = Column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=True
    )
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    customer = relationship(
        "User", foreign_keys=[customer_id], back_populates="fcl_quote_requests"
    )
    assigned_cargo_admin = relationship(
        "User",
        foreign_keys=[assigned_cargo_admin_id],
        back_populates="fcl_quote_requests_assigned_as_cargo_admin",
    )

    __table_args__ = (
        CheckConstraint("request_type = 'FCL'", name="chk_quote_requests_type"),
        CheckConstraint(
            "supplier_status IN ('has_supplier', 'needs_sourcing')",
            name="chk_quote_requests_supplier_status",
        ),
        CheckConstraint(
            "incoterm IN ('EXW', 'FOB')", name="chk_quote_requests_incoterm"
        ),
        CheckConstraint(
            "status IN ('pending', 'quotations_sent', 'done', 'complete')",
            name="chk_quote_requests_status",
        ),
        CheckConstraint(
            "assigned_role = 'cargo_admin'", name="chk_quote_requests_assigned_role"
        ),
        Index("ix_quote_requests_assigned_role_status", "assigned_role", "status"),
        Index("ix_quote_requests_created_at", "created_at"),
    )
