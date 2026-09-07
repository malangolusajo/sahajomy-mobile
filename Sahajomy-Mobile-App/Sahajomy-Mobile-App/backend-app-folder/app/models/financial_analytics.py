"""Auditable multi-company financial ledger and receivables."""

import uuid
from datetime import datetime

from app.database import Base
from sqlalchemy import (
    CheckConstraint,
    Column,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID


class FinanceCategory(Base):
    __tablename__ = "finance_categories"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    company_id = Column(
        UUID(as_uuid=True),
        ForeignKey("cargo_companies.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    name = Column(String(120), nullable=False)
    kind = Column(String(24), nullable=False)
    active = Column(String(8), nullable=False, default="active")
    created_by_id = Column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL")
    )
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    __table_args__ = (
        UniqueConstraint(
            "company_id", "name", "kind", name="uq_finance_category_company_name_kind"
        ),
        CheckConstraint(
            "kind IN ('revenue','direct_cost','operating_expense','other_income')",
            name="chk_finance_category_kind",
        ),
    )


class FinancialTransaction(Base):
    __tablename__ = "financial_transactions"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    scope = Column(String(16), nullable=False, default="company", index=True)
    company_id = Column(
        UUID(as_uuid=True),
        ForeignKey("cargo_companies.id", ondelete="CASCADE"),
        index=True,
    )
    branch_id = Column(
        UUID(as_uuid=True),
        ForeignKey("cargo_branches.id", ondelete="RESTRICT"),
        index=True,
    )
    customer_id = Column(
        UUID(as_uuid=True),
        ForeignKey("cargo_customers.id", ondelete="SET NULL"),
        index=True,
    )
    category_id = Column(
        UUID(as_uuid=True),
        ForeignKey("finance_categories.id", ondelete="SET NULL"),
        index=True,
    )
    transaction_type = Column(String(24), nullable=False, index=True)
    service_type = Column(String(20), nullable=False, default="other", index=True)
    source_type = Column(String(40), nullable=False, index=True)
    source_id = Column(UUID(as_uuid=True), index=True)
    description = Column(String(300), nullable=False)
    original_amount = Column(Numeric(24, 6), nullable=False)
    original_currency = Column(String(3), nullable=False, index=True)
    exchange_rate = Column(Numeric(24, 10), nullable=False)
    exchange_rate_date = Column(Date, nullable=False)
    base_amount = Column(Numeric(24, 6), nullable=False)
    base_currency = Column(String(3), nullable=False, index=True)
    direction = Column(String(8), nullable=False)
    status = Column(String(16), nullable=False, default="draft", index=True)
    transaction_date = Column(Date, nullable=False, index=True)
    due_date = Column(Date, index=True)
    vendor = Column(String(180))
    document_url = Column(Text)
    metadata_json = Column(JSONB, nullable=False, default=dict, server_default="{}")
    reversal_of_id = Column(
        UUID(as_uuid=True),
        ForeignKey("financial_transactions.id", ondelete="RESTRICT"),
        unique=True,
        index=True,
    )
    created_by_id = Column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL")
    )
    approved_by_id = Column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL")
    )
    approved_at = Column(DateTime)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(
        DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow
    )
    __table_args__ = (
        CheckConstraint(
            "scope IN ('company','platform')", name="chk_financial_transaction_scope"
        ),
        CheckConstraint(
            "transaction_type IN ('gmv','revenue','direct_cost','operating_expense','cash_in','cash_out','commission','refund','adjustment')",
            name="chk_financial_transaction_type",
        ),
        CheckConstraint(
            "service_type IN ('air','mco','cbm','fcl','sourcing','subscription','platform_fee','other')",
            name="chk_financial_service_type",
        ),
        CheckConstraint(
            "direction IN ('debit','credit')", name="chk_financial_direction"
        ),
        CheckConstraint(
            "status IN ('draft','pending','posted','reversed','cancelled')",
            name="chk_financial_transaction_status",
        ),
        CheckConstraint(
            "original_amount >= 0 AND exchange_rate > 0 AND base_amount >= 0",
            name="chk_financial_transaction_amounts",
        ),
        CheckConstraint(
            "(scope='platform' AND company_id IS NULL) OR (scope='company' AND company_id IS NOT NULL)",
            name="chk_financial_transaction_scope_owner",
        ),
        UniqueConstraint(
            "company_id",
            "source_type",
            "source_id",
            "transaction_type",
            name="uq_financial_source_event",
        ),
        Index(
            "ix_financial_company_branch_date",
            "company_id",
            "branch_id",
            "transaction_date",
        ),
    )


class FinancialReceivable(Base):
    __tablename__ = "financial_receivables"
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
    customer_id = Column(
        UUID(as_uuid=True),
        ForeignKey("cargo_customers.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    source_type = Column(String(40), nullable=False)
    source_id = Column(UUID(as_uuid=True), nullable=False)
    service_type = Column(String(20), nullable=False)
    invoice_number = Column(String(60), nullable=False)
    invoiced_amount = Column(Numeric(24, 6), nullable=False)
    paid_amount = Column(Numeric(24, 6), nullable=False, default=0)
    currency = Column(String(3), nullable=False)
    exchange_rate = Column(Numeric(24, 10), nullable=False)
    base_invoiced_amount = Column(Numeric(24, 6), nullable=False)
    base_paid_amount = Column(Numeric(24, 6), nullable=False, default=0)
    base_currency = Column(String(3), nullable=False)
    invoice_date = Column(Date, nullable=False)
    due_date = Column(Date, nullable=False, index=True)
    status = Column(String(16), nullable=False, default="unpaid", index=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(
        DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow
    )
    __table_args__ = (
        UniqueConstraint(
            "company_id", "source_type", "source_id", name="uq_receivable_source"
        ),
        CheckConstraint(
            "status IN ('unpaid','partial','paid','overdue','cancelled')",
            name="chk_receivable_status",
        ),
        CheckConstraint(
            "invoiced_amount >= 0 AND paid_amount >= 0 AND paid_amount <= invoiced_amount",
            name="chk_receivable_amounts",
        ),
        Index("ix_receivable_company_due_status", "company_id", "due_date", "status"),
    )


class CargoProfitabilitySnapshot(Base):
    __tablename__ = "cargo_profitability_snapshots"
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
    customer_id = Column(
        UUID(as_uuid=True),
        ForeignKey("cargo_customers.id", ondelete="SET NULL"),
        index=True,
    )
    service_type = Column(String(20), nullable=False, index=True)
    source_type = Column(String(40), nullable=False)
    source_id = Column(UUID(as_uuid=True), nullable=False)
    route = Column(String(200))
    provider = Column(String(180))
    quantity = Column(Numeric(24, 6), nullable=False)
    quantity_unit = Column(String(12), nullable=False)
    selling_rate = Column(Numeric(24, 6), nullable=False)
    cost_rate = Column(Numeric(24, 6), nullable=False)
    other_direct_cost = Column(Numeric(24, 6), nullable=False, default=0)
    revenue = Column(Numeric(24, 6), nullable=False)
    direct_cost = Column(Numeric(24, 6), nullable=False)
    gross_profit = Column(Numeric(24, 6), nullable=False)
    margin_percent = Column(Numeric(12, 6), nullable=False)
    currency = Column(String(3), nullable=False)
    transaction_date = Column(Date, nullable=False, index=True)
    created_by_id = Column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL")
    )
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    __table_args__ = (
        UniqueConstraint(
            "company_id", "source_type", "source_id", name="uq_profitability_source"
        ),
        CheckConstraint(
            "service_type IN ('air','mco','cbm','fcl','sourcing','other')",
            name="chk_profitability_service",
        ),
        CheckConstraint(
            "quantity >= 0 AND selling_rate >= 0 AND cost_rate >= 0 AND other_direct_cost >= 0",
            name="chk_profitability_amounts",
        ),
    )
