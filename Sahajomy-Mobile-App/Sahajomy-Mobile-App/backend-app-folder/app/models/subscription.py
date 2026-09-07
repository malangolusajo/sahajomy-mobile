"""Company subscriptions, entitlements, usage, storage, and provider costs."""

import uuid
from datetime import datetime

from app.database import Base
from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    Column,
    Date,
    DateTime,
    ForeignKey,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import relationship


class SubscriptionPlan(Base):
    __tablename__ = "subscription_plans"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    code = Column(String(40), nullable=False, unique=True, index=True)
    name = Column(String(100), nullable=False)
    description = Column(Text)
    monthly_price = Column(Numeric(18, 2), nullable=False, default=0)
    annual_price = Column(Numeric(18, 2), nullable=False, default=0)
    currency = Column(String(3), nullable=False, default="USD", server_default="USD")
    display_order = Column(BigInteger, nullable=False, default=0, server_default="0")
    is_active = Column(Boolean, nullable=False, default=True, server_default="true")
    is_custom = Column(Boolean, nullable=False, default=False, server_default="false")
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(
        DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    entitlements = relationship(
        "PlanEntitlement",
        back_populates="plan",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    subscriptions = relationship("CompanySubscription", back_populates="plan")

    __table_args__ = (
        CheckConstraint("monthly_price >= 0", name="chk_subscription_plan_monthly"),
        CheckConstraint("annual_price >= 0", name="chk_subscription_plan_annual"),
        CheckConstraint(
            "char_length(currency) = 3", name="chk_subscription_plan_currency"
        ),
    )


class PlanEntitlement(Base):
    __tablename__ = "plan_entitlements"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    plan_id = Column(
        UUID(as_uuid=True),
        ForeignKey("subscription_plans.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    key = Column(String(80), nullable=False)
    enabled = Column(Boolean, nullable=False, default=True, server_default="true")
    limit_value = Column(BigInteger)
    unit = Column(String(40))
    overage_unit_price = Column(Numeric(18, 4))
    config_json = Column(JSONB, nullable=False, default=dict, server_default="{}")
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(
        DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    plan = relationship("SubscriptionPlan", back_populates="entitlements")

    __table_args__ = (
        UniqueConstraint("plan_id", "key", name="uq_plan_entitlement_key"),
        CheckConstraint(
            "limit_value IS NULL OR limit_value >= -1",
            name="chk_plan_entitlement_limit",
        ),
        CheckConstraint(
            "overage_unit_price IS NULL OR overage_unit_price >= 0",
            name="chk_plan_entitlement_overage",
        ),
    )


class CompanySubscription(Base):
    __tablename__ = "company_subscriptions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    company_id = Column(
        UUID(as_uuid=True),
        ForeignKey("cargo_companies.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    plan_id = Column(
        UUID(as_uuid=True),
        ForeignKey("subscription_plans.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    status = Column(String(24), nullable=False, default="active", index=True)
    billing_cycle = Column(String(12), nullable=False, default="monthly")
    price_amount = Column(Numeric(18, 2), nullable=False, default=0)
    currency = Column(String(3), nullable=False, default="USD", server_default="USD")
    current_period_start = Column(DateTime, nullable=False, default=datetime.utcnow)
    current_period_end = Column(DateTime, nullable=False)
    grace_until = Column(DateTime)
    auto_renew = Column(Boolean, nullable=False, default=True, server_default="true")
    external_customer_id = Column(String(160))
    external_subscription_id = Column(String(160))
    created_by_id = Column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL")
    )
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(
        DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    company = relationship("CargoCompany")
    plan = relationship(
        "SubscriptionPlan", back_populates="subscriptions", lazy="joined"
    )

    __table_args__ = (
        CheckConstraint(
            "status IN ('trialing','active','past_due','grace','suspended','cancelled','expired')",
            name="chk_company_subscription_status",
        ),
        CheckConstraint(
            "billing_cycle IN ('monthly','annual','custom')",
            name="chk_company_subscription_cycle",
        ),
        CheckConstraint("price_amount >= 0", name="chk_company_subscription_price"),
        CheckConstraint(
            "char_length(currency) = 3", name="chk_company_subscription_currency"
        ),
        CheckConstraint(
            "current_period_end > current_period_start",
            name="chk_company_subscription_period",
        ),
    )


class CompanyUsageCounter(Base):
    __tablename__ = "company_usage_counters"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    company_id = Column(
        UUID(as_uuid=True),
        ForeignKey("cargo_companies.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    metric = Column(String(80), nullable=False, index=True)
    period_start = Column(DateTime, nullable=False, index=True)
    period_end = Column(DateTime, nullable=False)
    used_amount = Column(BigInteger, nullable=False, default=0, server_default="0")
    pending_amount = Column(BigInteger, nullable=False, default=0, server_default="0")
    updated_at = Column(
        DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    __table_args__ = (
        UniqueConstraint(
            "company_id",
            "metric",
            "period_start",
            name="uq_company_usage_metric_period",
        ),
        CheckConstraint("used_amount >= 0", name="chk_company_usage_used"),
        CheckConstraint("pending_amount >= 0", name="chk_company_usage_pending"),
        CheckConstraint("period_end > period_start", name="chk_company_usage_period"),
    )


class CompanyStorageAsset(Base):
    __tablename__ = "company_storage_assets"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    company_id = Column(
        UUID(as_uuid=True),
        ForeignKey("cargo_companies.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    public_id = Column(String(500), nullable=False, unique=True)
    secure_url = Column(Text, nullable=False)
    bytes = Column(BigInteger, nullable=False)
    resource_type = Column(String(40), nullable=False, default="image")
    asset_kind = Column(String(80), nullable=False, default="company_upload")
    status = Column(String(16), nullable=False, default="active", index=True)
    uploaded_by_id = Column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL")
    )
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    deleted_at = Column(DateTime)

    __table_args__ = (
        CheckConstraint("bytes >= 0", name="chk_company_storage_asset_bytes"),
        CheckConstraint(
            "status IN ('active','deleted','orphaned')",
            name="chk_company_storage_asset_status",
        ),
    )


class ProviderCostSnapshot(Base):
    __tablename__ = "provider_cost_snapshots"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    provider = Column(String(80), nullable=False, index=True)
    category = Column(String(80), nullable=False, index=True)
    billing_month = Column(Date, nullable=False, index=True)
    amount = Column(Numeric(18, 2), nullable=False)
    currency = Column(String(3), nullable=False, default="USD", server_default="USD")
    invoice_reference = Column(String(180))
    notes = Column(Text)
    details_json = Column(JSONB, nullable=False, default=dict, server_default="{}")
    created_by_id = Column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL")
    )
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(
        DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    __table_args__ = (
        UniqueConstraint(
            "provider",
            "category",
            "billing_month",
            name="uq_provider_cost_month_category",
        ),
        CheckConstraint("amount >= 0", name="chk_provider_cost_amount"),
        CheckConstraint("char_length(currency) = 3", name="chk_provider_cost_currency"),
    )


class SubscriptionUsageEvent(Base):
    __tablename__ = "subscription_usage_events"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    company_id = Column(
        UUID(as_uuid=True),
        ForeignKey("cargo_companies.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    metric = Column(String(80), nullable=False, index=True)
    quantity = Column(BigInteger, nullable=False)
    action = Column(String(100), nullable=False)
    resource_type = Column(String(80))
    resource_id = Column(String(180))
    idempotency_key = Column(String(180), unique=True)
    details_json = Column(JSONB, nullable=False, default=dict, server_default="{}")
    created_by_id = Column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL")
    )
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow, index=True)

    __table_args__ = (
        CheckConstraint("quantity <> 0", name="chk_subscription_usage_quantity"),
    )
