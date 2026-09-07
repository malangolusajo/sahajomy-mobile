"""Company billing/usage APIs and Super Admin subscription controls."""

from datetime import date, datetime, timedelta
from decimal import Decimal
from typing import Literal
from uuid import UUID

from app.core.audit import log_action
from app.core.dependencies import get_super_admin
from app.core.workspace_security import WorkspaceContext, get_workspace_context
from app.database import get_db
from app.models.cargo_workspace import CargoCompany
from app.models.subscription import (
    CompanySubscription,
    PlanEntitlement,
    ProviderCostSnapshot,
    SubscriptionPlan,
)
from app.models.user import User
from app.services.subscriptions import (
    assign_company_subscription,
    ensure_builtin_plans,
    get_current_subscription,
    plan_payload,
    set_usage_amount,
    subscription_payload,
    usage_payload,
)
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import func
from sqlalchemy.orm import Session, joinedload


company_router = APIRouter(prefix="/subscriptions", tags=["Company Subscription"])
super_admin_router = APIRouter(
    prefix="/super_admin/subscriptions", tags=["Super Admin Subscriptions"]
)


def _require_billing_view(
    context: WorkspaceContext = Depends(get_workspace_context),
) -> WorkspaceContext:
    if (
        "company.billing.view" not in context.permissions
        and context.membership.role.scope != "company"
    ):
        raise HTTPException(403, "Missing permission: company.billing.view")
    return context


@company_router.get("/current")
def current_company_subscription(
    ctx: WorkspaceContext = Depends(_require_billing_view),
    db: Session = Depends(get_db),
):
    payload = usage_payload(db, ctx.company_id)
    db.commit()
    return payload


class EntitlementUpdate(BaseModel):
    enabled: bool
    limit: int | None = Field(default=None, ge=-1)
    unit: str | None = Field(default=None, max_length=40)
    overage_unit_price: Decimal | None = Field(default=None, ge=0)


class PlanUpdate(BaseModel):
    name: str = Field(min_length=2, max_length=100)
    description: str | None = Field(default=None, max_length=2000)
    monthly_price: Decimal = Field(ge=0)
    annual_price: Decimal = Field(ge=0)
    currency: str = Field(default="USD", min_length=3, max_length=3)
    is_active: bool = True
    entitlements: dict[str, EntitlementUpdate] = Field(default_factory=dict)


@super_admin_router.get("/plans")
def list_plans(db: Session = Depends(get_db), _: User = Depends(get_super_admin)):
    ensure_builtin_plans(db)
    db.commit()
    rows = (
        db.query(SubscriptionPlan)
        .options(joinedload(SubscriptionPlan.entitlements))
        .order_by(SubscriptionPlan.display_order, SubscriptionPlan.monthly_price)
        .all()
    )
    return {"plans": [plan_payload(row) for row in rows]}


@super_admin_router.put("/plans/{plan_id}")
def update_plan(
    plan_id: UUID,
    body: PlanUpdate,
    db: Session = Depends(get_db),
    super_admin: User = Depends(get_super_admin),
):
    plan = (
        db.query(SubscriptionPlan)
        .options(joinedload(SubscriptionPlan.entitlements))
        .filter(SubscriptionPlan.id == plan_id)
        .first()
    )
    if not plan:
        raise HTTPException(404, "Subscription plan not found.")
    plan.name = body.name.strip()
    plan.description = body.description.strip() if body.description else None
    plan.monthly_price = body.monthly_price
    plan.annual_price = body.annual_price
    plan.currency = body.currency.upper()
    plan.is_active = body.is_active
    current = {item.key: item for item in plan.entitlements}
    for key, value in body.entitlements.items():
        if len(key) > 80:
            raise HTTPException(422, "Entitlement keys may not exceed 80 characters.")
        entitlement = current.get(key)
        if not entitlement:
            entitlement = PlanEntitlement(plan_id=plan.id, key=key)
            db.add(entitlement)
        entitlement.enabled = value.enabled
        entitlement.limit_value = value.limit
        entitlement.unit = value.unit
        entitlement.overage_unit_price = value.overage_unit_price
    log_action(
        db,
        "SUBSCRIPTION_PLAN_UPDATED",
        super_admin.id,
        "subscription_plan",
        plan.id,
        {"code": plan.code, "entitlements": sorted(body.entitlements)},
    )
    db.commit()
    db.refresh(plan)
    return plan_payload(plan)


def _company_row(db: Session, company: CargoCompany) -> dict:
    payload = usage_payload(db, company.id)
    return {
        "id": str(company.id),
        "name": company.name,
        "status": company.status,
        "created_at": company.created_at.isoformat(),
        "owner_user_id": (
            str(company.created_by_user_id) if company.created_by_user_id else None
        ),
        **payload,
    }


@super_admin_router.get("/companies")
def list_company_subscriptions(
    search: str | None = Query(default=None, max_length=120),
    db: Session = Depends(get_db),
    _: User = Depends(get_super_admin),
):
    ensure_builtin_plans(db)
    query = db.query(CargoCompany).order_by(CargoCompany.name)
    if search and search.strip():
        query = query.filter(CargoCompany.name.ilike(f"%{search.strip()}%"))
    companies = query.limit(500).all()
    rows = [_company_row(db, company) for company in companies]
    db.commit()
    return {"companies": rows}


class CompanySubscriptionUpdate(BaseModel):
    plan_id: UUID
    status: Literal[
        "trialing", "active", "past_due", "grace", "suspended", "cancelled", "expired"
    ] = "active"
    billing_cycle: Literal["monthly", "annual", "custom"] = "monthly"
    price_amount: Decimal | None = Field(default=None, ge=0)
    current_period_start: datetime | None = None
    current_period_end: datetime | None = None
    grace_until: datetime | None = None
    auto_renew: bool = True


@super_admin_router.put("/companies/{company_id}")
def update_company_subscription(
    company_id: UUID,
    body: CompanySubscriptionUpdate,
    db: Session = Depends(get_db),
    super_admin: User = Depends(get_super_admin),
):
    company = db.query(CargoCompany).filter(CargoCompany.id == company_id).first()
    if not company:
        raise HTTPException(404, "Cargo company not found.")
    plan = (
        db.query(SubscriptionPlan)
        .options(joinedload(SubscriptionPlan.entitlements))
        .filter(SubscriptionPlan.id == body.plan_id)
        .first()
    )
    if not plan:
        raise HTTPException(404, "Subscription plan not found.")
    start = body.current_period_start or datetime.utcnow()
    end = body.current_period_end or (
        start + timedelta(days=365 if body.billing_cycle == "annual" else 30)
    )
    if end <= start:
        raise HTTPException(422, "Subscription period end must be after its start.")
    subscription = assign_company_subscription(
        db,
        company_id=company.id,
        plan=plan,
        status=body.status,
        billing_cycle=body.billing_cycle,
        period_start=start,
        period_end=end,
        grace_until=body.grace_until,
        auto_renew=body.auto_renew,
        created_by_id=super_admin.id,
        price_amount=body.price_amount,
    )
    log_action(
        db,
        "COMPANY_SUBSCRIPTION_ASSIGNED",
        super_admin.id,
        "cargo_company",
        company.id,
        {
            "plan": plan.code,
            "status": body.status,
            "billing_cycle": body.billing_cycle,
            "period_end": end.isoformat(),
        },
    )
    db.commit()
    db.refresh(subscription)
    response = {
        "company": _company_row(db, company),
        "subscription": subscription_payload(subscription),
    }
    db.commit()
    return response


class UsageAdjustment(BaseModel):
    used: int = Field(ge=0)


@super_admin_router.put("/companies/{company_id}/usage/{metric}")
def reconcile_company_usage(
    company_id: UUID,
    metric: Literal["storage_bytes", "cloudinary_credits_milli", "automation_events"],
    body: UsageAdjustment,
    db: Session = Depends(get_db),
    super_admin: User = Depends(get_super_admin),
):
    company = db.query(CargoCompany).filter(CargoCompany.id == company_id).first()
    if not company:
        raise HTTPException(404, "Cargo company not found.")
    counter = set_usage_amount(db, company_id, metric, body.used)
    log_action(
        db,
        "COMPANY_USAGE_RECONCILED",
        super_admin.id,
        "cargo_company",
        company.id,
        {"metric": metric, "used": body.used},
    )
    db.commit()
    return {
        "metric": counter.metric,
        "used": int(counter.used_amount),
        "period_start": counter.period_start.isoformat(),
        "period_end": counter.period_end.isoformat(),
    }


class ProviderCostInput(BaseModel):
    provider: str = Field(min_length=2, max_length=80)
    category: str = Field(min_length=2, max_length=80)
    billing_month: date
    amount: Decimal = Field(ge=0)
    currency: str = Field(default="USD", min_length=3, max_length=3)
    invoice_reference: str | None = Field(default=None, max_length=180)
    notes: str | None = Field(default=None, max_length=4000)


def _cost_payload(row: ProviderCostSnapshot) -> dict:
    return {
        "id": str(row.id),
        "provider": row.provider,
        "category": row.category,
        "billing_month": row.billing_month.isoformat(),
        "amount": float(row.amount),
        "currency": row.currency,
        "invoice_reference": row.invoice_reference,
        "notes": row.notes,
    }


@super_admin_router.get("/provider-costs")
def list_provider_costs(
    db: Session = Depends(get_db), _: User = Depends(get_super_admin)
):
    rows = (
        db.query(ProviderCostSnapshot)
        .order_by(
            ProviderCostSnapshot.billing_month.desc(), ProviderCostSnapshot.provider
        )
        .limit(240)
        .all()
    )
    return {"costs": [_cost_payload(row) for row in rows]}


@super_admin_router.post("/provider-costs", status_code=201)
def upsert_provider_cost(
    body: ProviderCostInput,
    db: Session = Depends(get_db),
    super_admin: User = Depends(get_super_admin),
):
    provider = body.provider.strip()
    category = body.category.strip()
    row = (
        db.query(ProviderCostSnapshot)
        .filter(
            func.lower(ProviderCostSnapshot.provider) == provider.lower(),
            func.lower(ProviderCostSnapshot.category) == category.lower(),
            ProviderCostSnapshot.billing_month == body.billing_month,
        )
        .first()
    )
    if not row:
        row = ProviderCostSnapshot(
            provider=provider,
            category=category,
            billing_month=body.billing_month,
            created_by_id=super_admin.id,
        )
        db.add(row)
    row.amount = body.amount
    row.currency = body.currency.upper()
    row.invoice_reference = (
        body.invoice_reference.strip() if body.invoice_reference else None
    )
    row.notes = body.notes.strip() if body.notes else None
    db.flush()
    log_action(
        db,
        "PROVIDER_COST_RECORDED",
        super_admin.id,
        "provider_cost_snapshot",
        row.id,
        {
            "provider": provider,
            "category": category,
            "month": body.billing_month.isoformat(),
        },
    )
    db.commit()
    db.refresh(row)
    return _cost_payload(row)


@super_admin_router.get("/overview")
def subscription_overview(
    db: Session = Depends(get_db), _: User = Depends(get_super_admin)
):
    subscriptions = (
        db.query(CompanySubscription)
        .filter(
            CompanySubscription.status.in_(("trialing", "active", "past_due", "grace"))
        )
        .all()
    )
    mrr = sum(
        Decimal(row.price_amount or 0)
        / (Decimal("12") if row.billing_cycle == "annual" else Decimal("1"))
        for row in subscriptions
    )
    latest_month = db.query(func.max(ProviderCostSnapshot.billing_month)).scalar()
    latest_cost = Decimal("0")
    if latest_month:
        latest_cost = Decimal(
            db.query(func.coalesce(func.sum(ProviderCostSnapshot.amount), 0))
            .filter(
                ProviderCostSnapshot.billing_month == latest_month,
                ProviderCostSnapshot.currency == "USD",
            )
            .scalar()
            or 0
        )
    provider_margin = float((mrr - latest_cost) / mrr * 100) if mrr > 0 else None
    return {
        "active_companies": len(subscriptions),
        "monthly_recurring_revenue_usd": float(mrr),
        "latest_provider_cost_month": (
            latest_month.isoformat() if latest_month else None
        ),
        "latest_provider_cost_usd": float(latest_cost),
        "provider_margin_percent": (
            round(provider_margin, 2) if provider_margin is not None else None
        ),
        "target_gross_margin_percent": 70,
    }
