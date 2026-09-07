"""Authoritative financial analytics for cargo workspaces and platform finance."""

import csv
import io
from datetime import date, datetime, timedelta
from decimal import ROUND_HALF_UP, Decimal
from typing import Literal
from uuid import UUID, uuid4

from app.core.audit import log_action
from app.core.dependencies import get_super_admin
from app.core.workspace_security import WorkspaceContext, require_permission
from app.database import get_db
from app.models.cargo_customs import CargoCustomer
from app.models.cargo_workspace import CargoBranch, CargoCompany
from app.models.financial_analytics import (
    CargoProfitabilitySnapshot,
    FinanceCategory,
    FinancialReceivable,
    FinancialTransaction,
)
from app.models.user import User
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field, model_validator
from sqlalchemy import func
from sqlalchemy.orm import Session

cargo_router = APIRouter(prefix="/cargo/finance", tags=["Cargo Financial Analytics"])
platform_router = APIRouter(
    prefix="/super_admin/platform-finance", tags=["Platform Financial Analytics"]
)
MONEY = Decimal("0.000001")


def _q(value):
    return Decimal(value or 0).quantize(MONEY, rounding=ROUND_HALF_UP)


def _branch(db, ctx, branch_id=None):
    selected = branch_id or ctx.branch_id
    if not selected:
        raise HTTPException(422, "Select a branch for this financial action.")
    row = (
        db.query(CargoBranch)
        .filter(
            CargoBranch.id == selected,
            CargoBranch.company_id == ctx.company_id,
            CargoBranch.status == "active",
        )
        .first()
    )
    if not row:
        raise HTTPException(404, "Branch is not available in this company.")
    if ctx.membership.role.scope != "company" and row.id != ctx.branch_id:
        raise HTTPException(403, "You cannot access another branch's finance data.")
    return row


def _range(period, start, end):
    today = date.today()
    if period == "today":
        return today, today
    if period == "week":
        return today - timedelta(days=today.weekday()), today
    if period == "month":
        return today.replace(day=1), today
    if period == "quarter":
        return date(today.year, ((today.month - 1) // 3) * 3 + 1, 1), today
    if period == "year":
        return date(today.year, 1, 1), today
    if not start or not end or start > end:
        raise HTTPException(422, "Provide a valid custom date range.")
    return start, end


def _scope(
    query,
    ctx,
    start,
    end,
    branch_id=None,
    service=None,
    currency=None,
    customer_id=None,
    route=None,
):
    query = query.filter(
        FinancialTransaction.company_id == ctx.company_id,
        FinancialTransaction.scope == "company",
        FinancialTransaction.status == "posted",
        FinancialTransaction.transaction_date.between(start, end),
    )
    selected = branch_id or (
        ctx.branch_id if ctx.membership.role.scope != "company" else None
    )
    if selected:
        _branch(query.session, ctx, selected)
        query = query.filter(FinancialTransaction.branch_id == selected)
    if service:
        query = query.filter(FinancialTransaction.service_type == service)
    if currency:
        query = query.filter(FinancialTransaction.original_currency == currency.upper())
    if customer_id:
        query = query.filter(FinancialTransaction.customer_id == customer_id)
    if route:
        sources = query.session.query(CargoProfitabilitySnapshot.source_id).filter(
            CargoProfitabilitySnapshot.company_id == ctx.company_id,
            CargoProfitabilitySnapshot.route.ilike(f"%{route.strip()}%"),
        )
        query = query.filter(FinancialTransaction.source_id.in_(sources))
    return query


class CategoryInput(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    kind: Literal["revenue", "direct_cost", "operating_expense", "other_income"]


class MoneyInput(BaseModel):
    amount: Decimal = Field(gt=0)
    currency: str = Field(min_length=3, max_length=3)
    exchange_rate: Decimal = Field(gt=0)
    exchange_rate_date: date


class ExpenseInput(MoneyInput):
    branch_id: UUID | None = None
    category_id: UUID | None = None
    description: str = Field(min_length=2, max_length=300)
    vendor: str | None = Field(None, max_length=180)
    expense_date: date
    service_type: Literal[
        "air", "mco", "cbm", "fcl", "sourcing", "subscription", "platform_fee", "other"
    ] = "other"
    source_type: str = "expense"
    source_id: UUID | None = None
    document_url: str | None = None
    notes: str | None = Field(None, max_length=2000)


class ProfitabilityInput(MoneyInput):
    branch_id: UUID | None = None
    customer_id: UUID
    service_type: Literal["air", "mco", "cbm", "fcl", "sourcing", "other"]
    source_type: str = Field(min_length=2, max_length=40)
    source_id: UUID
    route: str | None = Field(None, max_length=200)
    provider: str | None = Field(None, max_length=180)
    quantity: Decimal = Field(gt=0)
    quantity_unit: Literal["kg", "cbm", "container", "order"]
    selling_rate: Decimal = Field(ge=0)
    cost_rate: Decimal = Field(ge=0)
    other_direct_cost: Decimal = Field(Decimal("0"), ge=0)
    transaction_date: date
    due_date: date
    invoice_number: str = Field(min_length=2, max_length=60)

    @model_validator(mode="after")
    def due_after_invoice(self):
        if self.due_date < self.transaction_date:
            raise ValueError("Due date cannot precede transaction date")
        return self


class PaymentInput(MoneyInput):
    payment_date: date
    reference: str = Field(min_length=2, max_length=100)


class CashEventInput(MoneyInput):
    branch_id: UUID | None = None
    transaction_type: Literal["cash_in", "cash_out", "refund"]
    service_type: Literal[
        "air", "mco", "cbm", "fcl", "sourcing", "subscription", "platform_fee", "other"
    ] = "other"
    description: str = Field(min_length=2, max_length=300)
    transaction_date: date
    source_type: str = Field(default="manual_cash_event", min_length=2, max_length=40)
    source_id: UUID | None = None
    vendor: str | None = Field(None, max_length=180)


class ReverseInput(BaseModel):
    reason: str = Field(min_length=3, max_length=300)
    reversal_date: date = Field(default_factory=date.today)


class PlatformEventInput(MoneyInput):
    transaction_type: Literal[
        "gmv",
        "commission",
        "revenue",
        "cash_in",
        "cash_out",
        "refund",
        "operating_expense",
    ]
    service_type: Literal[
        "air", "mco", "cbm", "fcl", "sourcing", "subscription", "platform_fee", "other"
    ]
    source_type: str = Field(min_length=2, max_length=40)
    source_id: UUID
    description: str = Field(min_length=2, max_length=300)
    transaction_date: date
    base_currency: str = Field(min_length=3, max_length=3)


def _transaction(
    ctx,
    branch_id,
    kind,
    service,
    source_type,
    source_id,
    description,
    money,
    tx_date,
    direction,
    status="posted",
    **extra,
):
    currency = money.currency.upper()
    base = _q(money.amount * money.exchange_rate)
    return FinancialTransaction(
        scope="company",
        company_id=ctx.company_id,
        branch_id=branch_id,
        transaction_type=kind,
        service_type=service,
        source_type=source_type,
        source_id=source_id,
        description=description,
        original_amount=_q(money.amount),
        original_currency=currency,
        exchange_rate=money.exchange_rate,
        exchange_rate_date=money.exchange_rate_date,
        base_amount=base,
        base_currency=extra.pop("base_currency"),
        direction=direction,
        status=status,
        transaction_date=tx_date,
        created_by_id=ctx.user.id,
        **extra,
    )


@cargo_router.get("/settings")
def finance_settings(
    db: Session = Depends(get_db),
    ctx: WorkspaceContext = Depends(require_permission("finance.dashboard.view")),
):
    company = db.query(CargoCompany).filter(CargoCompany.id == ctx.company_id).one()
    return {
        "company_id": str(company.id),
        "base_currency": company.base_currency,
        "permissions": sorted(ctx.permissions),
    }


@cargo_router.post("/categories", status_code=201)
def create_category(
    body: CategoryInput,
    db: Session = Depends(get_db),
    ctx: WorkspaceContext = Depends(require_permission("finance.expense.create")),
):
    row = FinanceCategory(
        company_id=ctx.company_id,
        name=body.name.strip(),
        kind=body.kind,
        created_by_id=ctx.user.id,
    )
    db.add(row)
    try:
        db.commit()
        db.refresh(row)
    except Exception as exc:
        db.rollback()
        raise HTTPException(409, "This finance category already exists.") from exc
    return {"id": str(row.id), "name": row.name, "kind": row.kind}


@cargo_router.get("/categories")
def categories(
    db: Session = Depends(get_db),
    ctx: WorkspaceContext = Depends(require_permission("finance.expense.view")),
):
    return [
        {"id": str(r.id), "name": r.name, "kind": r.kind}
        for r in db.query(FinanceCategory)
        .filter(
            FinanceCategory.company_id == ctx.company_id,
            FinanceCategory.active == "active",
        )
        .order_by(FinanceCategory.kind, FinanceCategory.name)
        .all()
    ]


@cargo_router.post("/expenses", status_code=201)
def create_expense(
    body: ExpenseInput,
    db: Session = Depends(get_db),
    ctx: WorkspaceContext = Depends(require_permission("finance.expense.create")),
):
    branch = _branch(db, ctx, body.branch_id)
    company = db.query(CargoCompany).filter_by(id=ctx.company_id).one()
    if (
        body.category_id
        and not db.query(FinanceCategory)
        .filter_by(id=body.category_id, company_id=ctx.company_id)
        .first()
    ):
        raise HTTPException(404, "Expense category not found.")
    source_id = body.source_id or uuid4()
    row = _transaction(
        ctx,
        branch.id,
        "operating_expense",
        body.service_type,
        body.source_type,
        source_id,
        body.description,
        body,
        body.expense_date,
        "debit",
        status="pending",
        base_currency=company.base_currency,
        category_id=body.category_id,
        vendor=body.vendor,
        document_url=body.document_url,
        metadata_json={"notes": body.notes},
    )
    db.add(row)
    log_action(
        db,
        "finance_expense_created",
        ctx.user.id,
        "financial_transaction",
        row.id,
        {
            "company_id": str(ctx.company_id),
            "branch_id": str(branch.id),
            "amount": str(body.amount),
            "currency": body.currency,
        },
    )
    db.commit()
    db.refresh(row)
    return {
        "id": str(row.id),
        "status": row.status,
        "base_amount": str(row.base_amount),
        "base_currency": row.base_currency,
    }


@cargo_router.post("/expenses/{transaction_id}/approve")
def approve_expense(
    transaction_id: UUID,
    db: Session = Depends(get_db),
    ctx: WorkspaceContext = Depends(require_permission("finance.expense.approve")),
):
    row = (
        db.query(FinancialTransaction)
        .filter_by(
            id=transaction_id,
            company_id=ctx.company_id,
            transaction_type="operating_expense",
        )
        .with_for_update()
        .first()
    )
    if not row:
        raise HTTPException(404, "Expense not found.")
    if row.status == "posted":
        return {"id": str(row.id), "status": "posted"}
    if row.status != "pending":
        raise HTTPException(409, "Only pending expenses can be approved.")
    before = row.status
    row.status = "posted"
    row.approved_by_id = ctx.user.id
    row.approved_at = datetime.utcnow()
    log_action(
        db,
        "finance_expense_approved",
        ctx.user.id,
        "financial_transaction",
        row.id,
        {
            "previous_status": before,
            "new_status": "posted",
            "amount": str(row.original_amount),
            "currency": row.original_currency,
        },
    )
    db.commit()
    return {"id": str(row.id), "status": row.status}


@cargo_router.post("/profitability", status_code=201)
def record_profitability(
    body: ProfitabilityInput,
    db: Session = Depends(get_db),
    ctx: WorkspaceContext = Depends(require_permission("finance.cost.view")),
):
    if "finance.profit.view" not in ctx.permissions:
        raise HTTPException(403, "Missing permission: finance.profit.view")
    branch = _branch(db, ctx, body.branch_id)
    company = db.query(CargoCompany).filter_by(id=ctx.company_id).one()
    customer = (
        db.query(CargoCustomer)
        .filter_by(id=body.customer_id, cargo_admin_id=company.created_by_user_id)
        .first()
    )
    if not customer:
        raise HTTPException(404, "Customer not found in this company.")
    revenue = _q(body.quantity * body.selling_rate)
    direct = _q(body.quantity * body.cost_rate + body.other_direct_cost)
    profit = _q(revenue - direct)
    margin = _q((profit / revenue * 100) if revenue else 0)
    snap = CargoProfitabilitySnapshot(
        company_id=ctx.company_id,
        branch_id=branch.id,
        customer_id=customer.id,
        service_type=body.service_type,
        source_type=body.source_type,
        source_id=body.source_id,
        route=body.route,
        provider=body.provider,
        quantity=body.quantity,
        quantity_unit=body.quantity_unit,
        selling_rate=body.selling_rate,
        cost_rate=body.cost_rate,
        other_direct_cost=body.other_direct_cost,
        revenue=revenue,
        direct_cost=direct,
        gross_profit=profit,
        margin_percent=margin,
        currency=body.currency.upper(),
        transaction_date=body.transaction_date,
        created_by_id=ctx.user.id,
    )
    revenue_money = body.model_copy(update={"amount": revenue})
    cost_money = body.model_copy(update={"amount": direct})
    db.add(snap)
    db.add(
        _transaction(
            ctx,
            branch.id,
            "revenue",
            body.service_type,
            body.source_type,
            body.source_id,
            f"{body.service_type.upper()} customer revenue",
            revenue_money,
            body.transaction_date,
            "credit",
            base_currency=company.base_currency,
            customer_id=customer.id,
        )
    )
    db.add(
        _transaction(
            ctx,
            branch.id,
            "direct_cost",
            body.service_type,
            body.source_type,
            body.source_id,
            f"{body.service_type.upper()} direct cost",
            cost_money,
            body.transaction_date,
            "debit",
            base_currency=company.base_currency,
            customer_id=customer.id,
        )
    )
    receivable = FinancialReceivable(
        company_id=ctx.company_id,
        branch_id=branch.id,
        customer_id=customer.id,
        source_type=body.source_type,
        source_id=body.source_id,
        service_type=body.service_type,
        invoice_number=body.invoice_number,
        invoiced_amount=revenue,
        paid_amount=0,
        currency=body.currency.upper(),
        exchange_rate=body.exchange_rate,
        base_invoiced_amount=_q(revenue * body.exchange_rate),
        base_paid_amount=0,
        base_currency=company.base_currency,
        invoice_date=body.transaction_date,
        due_date=body.due_date,
        status="unpaid",
    )
    db.add(receivable)
    log_action(
        db,
        "finance_profitability_recorded",
        ctx.user.id,
        "cargo_profitability",
        snap.id,
        {
            "revenue": str(revenue),
            "direct_cost": str(direct),
            "gross_profit": str(profit),
            "margin_percent": str(margin),
        },
    )
    try:
        db.commit()
        db.refresh(snap)
    except Exception as exc:
        db.rollback()
        raise HTTPException(
            409, "Financial events already exist for this operational source."
        ) from exc
    return {
        "id": str(snap.id),
        "revenue": str(revenue),
        "direct_cost": str(direct),
        "gross_profit": str(profit),
        "gross_margin_percent": str(margin),
        "currency": body.currency.upper(),
    }


@cargo_router.post("/receivables/{receivable_id}/payments")
def record_payment(
    receivable_id: UUID,
    body: PaymentInput,
    db: Session = Depends(get_db),
    ctx: WorkspaceContext = Depends(require_permission("finance.payment.confirm")),
):
    row = (
        db.query(FinancialReceivable)
        .filter_by(id=receivable_id, company_id=ctx.company_id)
        .with_for_update()
        .first()
    )
    if not row:
        raise HTTPException(404, "Receivable not found.")
    outstanding = row.invoiced_amount - row.paid_amount
    if body.currency.upper() != row.currency:
        raise HTTPException(422, "Payment currency must match the receivable currency.")
    if body.amount > outstanding:
        raise HTTPException(409, "Payment exceeds the outstanding balance.")
    company = db.query(CargoCompany).filter_by(id=ctx.company_id).one()
    row.paid_amount += body.amount
    row.base_paid_amount += _q(body.amount * body.exchange_rate)
    row.status = "paid" if row.paid_amount == row.invoiced_amount else "partial"
    source_id = uuid4()
    db.add(
        _transaction(
            ctx,
            row.branch_id,
            "cash_in",
            row.service_type,
            "receivable_payment",
            source_id,
            f"Payment {body.reference}",
            body,
            body.payment_date,
            "credit",
            base_currency=company.base_currency,
            customer_id=row.customer_id,
            metadata_json={"receivable_id": str(row.id), "reference": body.reference},
        )
    )
    log_action(
        db,
        "finance_payment_confirmed",
        ctx.user.id,
        "financial_receivable",
        row.id,
        {
            "amount": str(body.amount),
            "currency": body.currency,
            "new_status": row.status,
        },
    )
    db.commit()
    return {
        "status": row.status,
        "outstanding": str(row.invoiced_amount - row.paid_amount),
    }


@cargo_router.post("/transactions/{transaction_id}/reverse")
def reverse_transaction(
    transaction_id: UUID,
    body: ReverseInput,
    db: Session = Depends(get_db),
    ctx: WorkspaceContext = Depends(require_permission("finance.expense.approve")),
):
    row = (
        db.query(FinancialTransaction)
        .filter_by(id=transaction_id, company_id=ctx.company_id)
        .with_for_update()
        .first()
    )
    if not row or row.status != "posted":
        raise HTTPException(409, "Only a posted transaction can be reversed.")
    if db.query(FinancialTransaction).filter_by(reversal_of_id=row.id).first():
        raise HTTPException(409, "Transaction already has a reversal.")
    reversal = FinancialTransaction(
        scope=row.scope,
        company_id=row.company_id,
        branch_id=row.branch_id,
        customer_id=row.customer_id,
        category_id=row.category_id,
        transaction_type="adjustment",
        service_type=row.service_type,
        source_type="reversal",
        source_id=row.id,
        description=f"Reversal: {body.reason}",
        original_amount=row.original_amount,
        original_currency=row.original_currency,
        exchange_rate=row.exchange_rate,
        exchange_rate_date=row.exchange_rate_date,
        base_amount=row.base_amount,
        base_currency=row.base_currency,
        direction="debit" if row.direction == "credit" else "credit",
        status="posted",
        transaction_date=body.reversal_date,
        metadata_json={"reason": body.reason},
        reversal_of_id=row.id,
        created_by_id=ctx.user.id,
        approved_by_id=ctx.user.id,
        approved_at=datetime.utcnow(),
    )
    row.status = "reversed"
    db.add(reversal)
    log_action(
        db,
        "finance_transaction_reversed",
        ctx.user.id,
        "financial_transaction",
        row.id,
        {"reversal_id": str(reversal.id), "reason": body.reason},
    )
    db.commit()
    return {"original_status": row.status, "reversal_id": str(reversal.id)}


@cargo_router.post("/cash-events", status_code=201)
def record_cash_event(
    body: CashEventInput,
    db: Session = Depends(get_db),
    ctx: WorkspaceContext = Depends(require_permission("finance.payment.confirm")),
):
    branch = _branch(db, ctx, body.branch_id)
    company = db.query(CargoCompany).filter_by(id=ctx.company_id).one()
    source_id = body.source_id or uuid4()
    direction = "credit" if body.transaction_type == "cash_in" else "debit"
    row = _transaction(
        ctx,
        branch.id,
        body.transaction_type,
        body.service_type,
        body.source_type,
        source_id,
        body.description,
        body,
        body.transaction_date,
        direction,
        base_currency=company.base_currency,
        vendor=body.vendor,
    )
    db.add(row)
    log_action(
        db,
        "finance_cash_event_recorded",
        ctx.user.id,
        "financial_transaction",
        row.id,
        {
            "type": body.transaction_type,
            "amount": str(body.amount),
            "currency": body.currency,
        },
    )
    db.commit()
    db.refresh(row)
    return {
        "id": str(row.id),
        "type": row.transaction_type,
        "base_amount": str(row.base_amount),
    }


def _metrics(rows):
    totals = {
        k: Decimal("0")
        for k in (
            "gmv",
            "revenue",
            "direct_cost",
            "operating_expense",
            "cash_in",
            "cash_out",
            "commission",
            "refund",
        )
    }
    for kind, amount, direction in rows:
        value = Decimal(amount or 0)
        totals[kind] = totals.get(kind, Decimal("0")) + value
    gross = totals["revenue"] - totals["direct_cost"] - totals["refund"]
    margin = (gross / totals["revenue"] * 100) if totals["revenue"] else Decimal("0")
    return {
        **{k: _q(v) for k, v in totals.items()},
        "gross_profit": _q(gross),
        "gross_margin": _q(margin),
        "net_cash_flow": _q(totals["cash_in"] - totals["cash_out"]),
        "operating_profit": _q(gross - totals["operating_expense"]),
    }


@cargo_router.get("/dashboard")
def dashboard(
    period: Literal["today", "week", "month", "quarter", "year", "custom"] = "month",
    start: date | None = None,
    end: date | None = None,
    branch_id: UUID | None = None,
    service: str | None = None,
    currency: str | None = None,
    customer_id: UUID | None = None,
    route: str | None = None,
    payment_status: Literal["unpaid", "partial", "paid", "overdue"] | None = None,
    db: Session = Depends(get_db),
    ctx: WorkspaceContext = Depends(require_permission("finance.dashboard.view")),
):
    start, end = _range(period, start, end)
    q = _scope(
        db.query(
            FinancialTransaction.transaction_type,
            func.sum(FinancialTransaction.base_amount),
            FinancialTransaction.direction,
        ),
        ctx,
        start,
        end,
        branch_id,
        service,
        currency,
        customer_id,
        route,
    ).group_by(FinancialTransaction.transaction_type, FinancialTransaction.direction)
    metrics = _metrics(q.all())
    rq = db.query(
        func.sum(
            FinancialReceivable.base_invoiced_amount
            - FinancialReceivable.base_paid_amount
        )
    ).filter(
        FinancialReceivable.company_id == ctx.company_id,
        FinancialReceivable.status.in_(["unpaid", "partial", "overdue"]),
    )
    selected = branch_id or (
        ctx.branch_id if ctx.membership.role.scope != "company" else None
    )
    if selected:
        rq = rq.filter(FinancialReceivable.branch_id == selected)
    if customer_id:
        rq = rq.filter(FinancialReceivable.customer_id == customer_id)
    if service:
        rq = rq.filter(FinancialReceivable.service_type == service)
    if payment_status:
        rq = rq.filter(FinancialReceivable.status == payment_status)
    metrics["outstanding"] = _q(rq.scalar() or 0)
    company = db.query(CargoCompany).filter_by(id=ctx.company_id).one()
    by_service = _scope(
        db.query(
            FinancialTransaction.service_type,
            FinancialTransaction.transaction_type,
            func.sum(FinancialTransaction.base_amount),
        ).group_by(
            FinancialTransaction.service_type, FinancialTransaction.transaction_type
        ),
        ctx,
        start,
        end,
        branch_id,
        service,
        currency,
        customer_id,
        route,
    ).all()
    services = {}
    for name, kind, amount in by_service:
        services.setdefault(name, {})[kind] = str(_q(amount))
    ranked = sorted(
        (
            (
                name,
                Decimal(values.get("revenue", "0"))
                - Decimal(values.get("direct_cost", "0")),
            )
            for name, values in services.items()
        ),
        key=lambda item: item[1],
        reverse=True,
    )
    insights = (
        [f"{ranked[0][0].upper()} generated the highest gross profit in this period."]
        if ranked
        else []
    )
    return {
        "period": {"start": start.isoformat(), "end": end.isoformat()},
        "base_currency": company.base_currency,
        "kpis": {k: str(v) for k, v in metrics.items()},
        "services": services,
        "insights": insights,
    }


@cargo_router.get("/receivables")
def receivables(
    branch_id: UUID | None = None,
    db: Session = Depends(get_db),
    ctx: WorkspaceContext = Depends(require_permission("finance.receivables.view")),
):
    today = date.today()
    query = (
        db.query(FinancialReceivable, CargoCustomer)
        .join(CargoCustomer, CargoCustomer.id == FinancialReceivable.customer_id)
        .filter(
            FinancialReceivable.company_id == ctx.company_id,
            FinancialReceivable.status.in_(["unpaid", "partial", "overdue"]),
        )
    )
    selected = branch_id or (
        ctx.branch_id if ctx.membership.role.scope != "company" else None
    )
    if selected:
        _branch(db, ctx, selected)
        query = query.filter(FinancialReceivable.branch_id == selected)
    buckets = {
        "0-7": Decimal(0),
        "8-30": Decimal(0),
        "31-60": Decimal(0),
        "61-90": Decimal(0),
        "90+": Decimal(0),
    }
    items = []
    for row, customer in query.order_by(FinancialReceivable.due_date).all():
        days = max((today - row.due_date).days, 0)
        bucket = (
            "0-7"
            if days <= 7
            else (
                "8-30"
                if days <= 30
                else "31-60" if days <= 60 else "61-90" if days <= 90 else "90+"
            )
        )
        outstanding = row.base_invoiced_amount - row.base_paid_amount
        buckets[bucket] += outstanding
        items.append(
            {
                "id": str(row.id),
                "invoice_number": row.invoice_number,
                "customer_id": str(customer.id),
                "customer_name": customer.name,
                "service": row.service_type,
                "due_date": row.due_date.isoformat(),
                "days_overdue": days,
                "status": row.status,
                "invoiced": str(row.invoiced_amount),
                "paid": str(row.paid_amount),
                "outstanding": str(row.invoiced_amount - row.paid_amount),
                "currency": row.currency,
                "base_outstanding": str(outstanding),
            }
        )
    return {"aging": {k: str(_q(v)) for k, v in buckets.items()}, "items": items}


@cargo_router.get("/p-and-l")
def profit_and_loss(
    year: int | None = Query(None, ge=2000, le=2200),
    branch_id: UUID | None = None,
    db: Session = Depends(get_db),
    ctx: WorkspaceContext = Depends(require_permission("finance.reports.view")),
):
    year = year or date.today().year
    start, end = date(year, 1, 1), date(year, 12, 31)
    rows = _scope(
        db.query(
            func.date_trunc("month", FinancialTransaction.transaction_date),
            FinancialTransaction.transaction_type,
            func.sum(FinancialTransaction.base_amount),
        )
        .group_by(
            func.date_trunc("month", FinancialTransaction.transaction_date),
            FinancialTransaction.transaction_type,
        )
        .order_by(func.date_trunc("month", FinancialTransaction.transaction_date)),
        ctx,
        start,
        end,
        branch_id,
    ).all()
    months = {}
    for month, kind, amount in rows:
        months.setdefault(month.strftime("%Y-%m"), {})[kind] = _q(amount)
    result = []
    for month, values in months.items():
        revenue = values.get("revenue", 0) + values.get("commission", 0)
        costs = values.get("direct_cost", 0) + values.get("refund", 0)
        expenses = values.get("operating_expense", 0)
        result.append(
            {
                "month": month,
                "revenue": str(_q(revenue)),
                "direct_costs": str(_q(costs)),
                "gross_profit": str(_q(revenue - costs)),
                "operating_expenses": str(_q(expenses)),
                "operating_profit": str(_q(revenue - costs - expenses)),
            }
        )
    return {"year": year, "months": result}


@cargo_router.get("/transactions")
def transactions(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
    ctx: WorkspaceContext = Depends(require_permission("finance.reports.view")),
):
    query = db.query(FinancialTransaction).filter(
        FinancialTransaction.company_id == ctx.company_id
    )
    selected = ctx.branch_id if ctx.membership.role.scope != "company" else None
    if selected:
        query = query.filter(FinancialTransaction.branch_id == selected)
    total = query.count()
    rows = (
        query.order_by(
            FinancialTransaction.transaction_date.desc(),
            FinancialTransaction.created_at.desc(),
        )
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )
    return {
        "total": total,
        "page": page,
        "items": [
            {
                "id": str(r.id),
                "date": r.transaction_date.isoformat(),
                "type": r.transaction_type,
                "service": r.service_type,
                "description": r.description,
                "amount": str(r.original_amount),
                "currency": r.original_currency,
                "base_amount": str(r.base_amount),
                "base_currency": r.base_currency,
                "status": r.status,
                "source_type": r.source_type,
                "source_id": str(r.source_id) if r.source_id else None,
            }
            for r in rows
        ],
    }


@cargo_router.get("/branches")
def branch_performance(
    db: Session = Depends(get_db),
    ctx: WorkspaceContext = Depends(require_permission("finance.reports.view")),
):
    rows = (
        db.query(
            CargoBranch.id,
            CargoBranch.name,
            FinancialTransaction.transaction_type,
            func.sum(FinancialTransaction.base_amount),
        )
        .join(FinancialTransaction, FinancialTransaction.branch_id == CargoBranch.id)
        .filter(
            CargoBranch.company_id == ctx.company_id,
            FinancialTransaction.status == "posted",
        )
        .group_by(
            CargoBranch.id, CargoBranch.name, FinancialTransaction.transaction_type
        )
        .all()
    )
    result = {}
    for branch_id, name, kind, amount in rows:
        result.setdefault(
            str(branch_id), {"branch_id": str(branch_id), "branch_name": name}
        )[kind] = str(_q(amount))
    return list(result.values())


@cargo_router.get("/customers/{customer_id}")
def customer_profile(
    customer_id: UUID,
    db: Session = Depends(get_db),
    ctx: WorkspaceContext = Depends(require_permission("finance.profit.view")),
):
    company = db.query(CargoCompany).filter_by(id=ctx.company_id).one()
    customer = (
        db.query(CargoCustomer)
        .filter_by(id=customer_id, cargo_admin_id=company.created_by_user_id)
        .first()
    )
    if not customer:
        raise HTTPException(404, "Customer not found.")
    snaps = (
        db.query(CargoProfitabilitySnapshot)
        .filter_by(company_id=ctx.company_id, customer_id=customer_id)
        .all()
    )
    recs = (
        db.query(FinancialReceivable)
        .filter_by(company_id=ctx.company_id, customer_id=customer_id)
        .all()
    )
    revenue = sum((r.revenue for r in snaps), Decimal(0))
    profit = sum((r.gross_profit for r in snaps), Decimal(0))
    paid = sum((r.paid_amount for r in recs), Decimal(0))
    outstanding = sum((r.invoiced_amount - r.paid_amount for r in recs), Decimal(0))
    return {
        "customer_id": str(customer.id),
        "customer_name": customer.name,
        "bookings": len(snaps),
        "revenue": str(_q(revenue)),
        "gross_profit": str(_q(profit)),
        "margin_percent": str(_q((profit / revenue * 100) if revenue else 0)),
        "amount_paid": str(_q(paid)),
        "outstanding": str(_q(outstanding)),
        "average_booking_value": str(_q(revenue / len(snaps) if snaps else 0)),
        "kg_shipped": str(
            _q(sum((r.quantity for r in snaps if r.quantity_unit == "kg"), Decimal(0)))
        ),
        "cbm_shipped": str(
            _q(sum((r.quantity for r in snaps if r.quantity_unit == "cbm"), Decimal(0)))
        ),
        "fcl_bookings": sum(1 for r in snaps if r.service_type == "fcl"),
    }


@cargo_router.get("/export.csv")
def export_csv(
    db: Session = Depends(get_db),
    ctx: WorkspaceContext = Depends(require_permission("finance.export")),
):
    rows = (
        db.query(FinancialTransaction)
        .filter(FinancialTransaction.company_id == ctx.company_id)
        .order_by(FinancialTransaction.transaction_date)
        .all()
    )
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(
        [
            "Date",
            "Type",
            "Service",
            "Description",
            "Original Amount",
            "Currency",
            "Exchange Rate",
            "Base Amount",
            "Base Currency",
            "Status",
            "Source",
        ]
    )
    for r in rows:
        writer.writerow(
            [
                r.transaction_date,
                r.transaction_type,
                r.service_type,
                r.description,
                r.original_amount,
                r.original_currency,
                r.exchange_rate,
                r.base_amount,
                r.base_currency,
                r.status,
                f"{r.source_type}:{r.source_id or ''}",
            ]
        )
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={
            "Content-Disposition": f'attachment; filename="sahajomy-finance-{date.today()}.csv"'
        },
    )


@platform_router.get("/dashboard")
def platform_dashboard(
    db: Session = Depends(get_db), _: User = Depends(get_super_admin)
):
    rows = (
        db.query(
            FinancialTransaction.transaction_type,
            func.sum(FinancialTransaction.base_amount),
            FinancialTransaction.direction,
        )
        .filter(
            FinancialTransaction.scope == "platform",
            FinancialTransaction.status == "posted",
        )
        .group_by(FinancialTransaction.transaction_type, FinancialTransaction.direction)
        .all()
    )
    metrics = _metrics(rows)
    return {
        "scope": "platform",
        "note": "Company-private cost and profit records are excluded.",
        "kpis": {k: str(v) for k, v in metrics.items()},
    }


@platform_router.post("/events", status_code=201)
def record_platform_event(
    body: PlatformEventInput,
    db: Session = Depends(get_db),
    admin: User = Depends(get_super_admin),
):
    row = FinancialTransaction(
        scope="platform",
        company_id=None,
        branch_id=None,
        transaction_type=body.transaction_type,
        service_type=body.service_type,
        source_type=body.source_type,
        source_id=body.source_id,
        description=body.description,
        original_amount=_q(body.amount),
        original_currency=body.currency.upper(),
        exchange_rate=body.exchange_rate,
        exchange_rate_date=body.exchange_rate_date,
        base_amount=_q(body.amount * body.exchange_rate),
        base_currency=body.base_currency.upper(),
        direction=(
            "debit"
            if body.transaction_type in {"cash_out", "refund", "operating_expense"}
            else "credit"
        ),
        status="posted",
        transaction_date=body.transaction_date,
        created_by_id=admin.id,
        approved_by_id=admin.id,
        approved_at=datetime.utcnow(),
    )
    db.add(row)
    log_action(
        db,
        "platform_financial_event_recorded",
        admin.id,
        "financial_transaction",
        row.id,
        {
            "type": body.transaction_type,
            "amount": str(body.amount),
            "currency": body.currency,
        },
    )
    db.commit()
    db.refresh(row)
    return {"id": str(row.id), "transaction_type": row.transaction_type}
