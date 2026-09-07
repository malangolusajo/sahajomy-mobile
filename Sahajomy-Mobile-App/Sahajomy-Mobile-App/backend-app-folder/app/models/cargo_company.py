"""Cargo-company onboarding and service coverage profile."""

import uuid
from datetime import datetime

from app.database import Base
from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Column,
    DateTime,
    ForeignKey,
    Index,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import relationship


class CargoOperatorProfile(Base):
    """Business capabilities supplied when a cargo operator applies.

    Operational resources such as warehouses, rates, and containers remain the
    source of truth for bookable capacity. This profile describes the markets
    and services the operator intends to offer so Sahajomy can review, onboard,
    and guide the operator to the right dashboard modules.
    """

    __tablename__ = "cargo_operator_profiles"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    company_name = Column(String(180), nullable=False, index=True)
    registration_number = Column(String(120), nullable=True)
    website = Column(String(255), nullable=True)
    logo_url = Column(String(500), nullable=True)
    headquarters_country = Column(String(100), nullable=False, index=True)
    headquarters_city = Column(String(120), nullable=False)
    china_origin_cities = Column(
        JSONB, nullable=False, default=list, server_default="[]"
    )
    destination_countries = Column(
        JSONB, nullable=False, default=list, server_default="[]"
    )
    service_types = Column(JSONB, nullable=False, default=list, server_default="[]")
    special_capabilities = Column(
        JSONB, nullable=False, default=list, server_default="[]"
    )
    preferred_currencies = Column(
        JSONB, nullable=False, default=list, server_default="[]"
    )
    years_experience = Column(String(30), nullable=True)
    operations_summary = Column(Text, nullable=True)
    approved_service_types = Column(
        JSONB, nullable=False, default=list, server_default="[]"
    )
    service_statuses = Column(JSONB, nullable=False, default=dict, server_default="{}")
    compliance_status = Column(
        String(24),
        nullable=False,
        default="not_submitted",
        server_default="not_submitted",
    )
    compliance_documents = Column(
        JSONB, nullable=False, default=list, server_default="[]"
    )
    compliance_expires_at = Column(DateTime, nullable=True)
    status_reason = Column(Text, nullable=True)
    booking_paused = Column(
        Boolean, nullable=False, default=False, server_default="false", index=True
    )
    paused_at = Column(DateTime, nullable=True)
    paused_by = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    status = Column(String(20), nullable=False, default="pending", index=True)
    is_verified = Column(Boolean, nullable=False, default=False, index=True)
    verified_at = Column(DateTime, nullable=True)
    verified_by = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(
        DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    __table_args__ = (
        UniqueConstraint("user_id", name="cargo_operator_profiles_user_id_key"),
        Index("ix_cargo_operator_profiles_user_id", "user_id", unique=True),
        CheckConstraint(
            "status IN ('pending','verified','rejected','inactive')",
            name="chk_cargo_operator_profile_status",
        ),
        CheckConstraint(
            "compliance_status IN "
            "('not_submitted','pending','verified','rejected','expired')",
            name="chk_cargo_operator_compliance_status",
        ),
    )

    user = relationship(
        "User", foreign_keys=[user_id], back_populates="cargo_operator_profile"
    )
    verifier = relationship("User", foreign_keys=[verified_by])
    pauser = relationship("User", foreign_keys=[paused_by])


class OperatorGovernanceCase(Base):
    """A reviewable platform-level case attached to one cargo operator."""

    __tablename__ = "operator_governance_cases"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    operator_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    category = Column(String(30), nullable=False, index=True)
    severity = Column(String(16), nullable=False, default="medium", index=True)
    status = Column(String(20), nullable=False, default="open", index=True)
    title = Column(String(180), nullable=False)
    description = Column(Text, nullable=False)
    resolution = Column(Text, nullable=True)
    created_by = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    resolved_by = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    resolved_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow, index=True)
    updated_at = Column(
        DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    __table_args__ = (
        CheckConstraint(
            "category IN "
            "('compliance','complaint','incident','dispute','fraud',"
            "'service_quality','finance','other')",
            name="chk_operator_governance_case_category",
        ),
        CheckConstraint(
            "severity IN ('low','medium','high','critical')",
            name="chk_operator_governance_case_severity",
        ),
        CheckConstraint(
            "status IN ('open','investigating','resolved','dismissed')",
            name="chk_operator_governance_case_status",
        ),
    )
