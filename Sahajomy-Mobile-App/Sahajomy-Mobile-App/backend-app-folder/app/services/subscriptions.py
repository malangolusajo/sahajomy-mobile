"""Company subscription, entitlement, quota, and usage enforcement."""

from __future__ import annotations

import math
import uuid
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Any
from uuid import UUID

from app.models.cargo_workspace import (
    CargoBranch,
    CargoCompany,
    CargoCompanyMembership,
    CargoStaffInvitation,
)
from app.models.subscription import (
    CompanyStorageAsset,
    CompanySubscription,
    CompanyUsageCounter,
    PlanEntitlement,
    SubscriptionPlan,
    SubscriptionUsageEvent,
)
from fastapi import HTTPException
from sqlalchemy import func
from sqlalchemy.orm import Session, joinedload


GIB = 1024**3
ACTIVE_SUBSCRIPTION_STATUSES = ("trialing", "active", "past_due", "grace")
BUILTIN_PLANS = {
    "starter": {
        "name": "Starter",
        "description": "Manual cargo operations for a small company.",
        "monthly_price": Decimal("39.00"),
        "annual_price": Decimal("390.00"),
        "display_order": 1,
        "entitlements": {
            "staff_users": (True, 3, "count"),
            "branches": (True, 1, "count"),
            "storage_bytes": (True, 2 * GIB, "bytes"),
            "cloudinary_credits_milli": (True, 10_000, "milli_credits"),
            "warehouse_automation": (False, None, "feature"),
            "automation_events": (False, 0, "count"),
        },
    },
    "growth": {
        "name": "Growth",
        "description": "Automation and multi-branch operations for a growing cargo company.",
        "monthly_price": Decimal("119.00"),
        "annual_price": Decimal("1190.00"),
        "display_order": 2,
        "entitlements": {
            "staff_users": (True, 10, "count"),
            "branches": (True, 3, "count"),
            "storage_bytes": (True, 10 * GIB, "bytes"),
            "cloudinary_credits_milli": (True, 50_000, "milli_credits"),
            "warehouse_automation": (True, None, "feature"),
            "automation_events": (True, 2_500, "count"),
        },
    },
    "scale": {
        "name": "Scale",
        "description": "High-volume automation and larger company capacity.",
        "monthly_price": Decimal("299.00"),
        "annual_price": Decimal("2990.00"),
        "display_order": 3,
        "entitlements": {
            "staff_users": (True, 30, "count"),
            "branches": (True, 10, "count"),
            "storage_bytes": (True, 30 * GIB, "bytes"),
            "cloudinary_credits_milli": (True, 150_000, "milli_credits"),
            "warehouse_automation": (True, None, "feature"),
            "automation_events": (True, 15_000, "count"),
        },
    },
}


def ensure_builtin_plans(db: Session) -> dict[str, SubscriptionPlan]:
    plans = {row.code: row for row in db.query(SubscriptionPlan).all()}
    for code, definition in BUILTIN_PLANS.items():
        plan = plans.get(code)
        if not plan:
            plan = SubscriptionPlan(
                code=code,
                name=definition["name"],
                description=definition["description"],
                monthly_price=definition["monthly_price"],
                annual_price=definition["annual_price"],
                currency="USD",
                display_order=definition["display_order"],
            )
            db.add(plan)
            db.flush()
            plans[code] = plan
        existing = {item.key: item for item in plan.entitlements}
        for key, (enabled, limit_value, unit) in definition["entitlements"].items():
            if key not in existing:
                db.add(
                    PlanEntitlement(
                        plan_id=plan.id,
                        key=key,
                        enabled=enabled,
                        limit_value=limit_value,
                        unit=unit,
                    )
                )
    db.flush()
    return plans


def create_default_subscription(
    db: Session,
    company_id: UUID,
    *,
    created_by_id: UUID | None = None,
    plan_code: str = "starter",
) -> CompanySubscription:
    existing = get_current_subscription(db, company_id)
    if existing:
        return existing
    plans = ensure_builtin_plans(db)
    plan = plans[plan_code]
    now = datetime.utcnow()
    subscription = CompanySubscription(
        company_id=company_id,
        plan_id=plan.id,
        status="active",
        billing_cycle="monthly",
        price_amount=plan.monthly_price,
        currency=plan.currency,
        current_period_start=now,
        current_period_end=now + timedelta(days=30),
        created_by_id=created_by_id,
    )
    db.add(subscription)
    db.flush()
    return subscription


def get_current_subscription(
    db: Session, company_id: UUID
) -> CompanySubscription | None:
    """Return the newest assignment, including an inactive one.

    Inactive assignments must remain visible so they cannot accidentally fall
    through the legacy-company compatibility path and regain access.
    """
    return (
        db.query(CompanySubscription)
        .options(
            joinedload(CompanySubscription.plan).joinedload(
                SubscriptionPlan.entitlements
            )
        )
        .filter(CompanySubscription.company_id == company_id)
        .order_by(
            CompanySubscription.created_at.desc(),
            CompanySubscription.current_period_start.desc(),
        )
        .first()
    )


def company_for_operator(db: Session, operator_id: UUID) -> CargoCompany | None:
    owned = (
        db.query(CargoCompany)
        .filter(CargoCompany.created_by_user_id == operator_id)
        .order_by(CargoCompany.created_at.asc())
        .first()
    )
    if owned:
        return owned
    membership = (
        db.query(CargoCompanyMembership)
        .options(joinedload(CargoCompanyMembership.company))
        .filter(
            CargoCompanyMembership.user_id == operator_id,
            CargoCompanyMembership.status == "active",
        )
        .order_by(CargoCompanyMembership.joined_at.asc())
        .first()
    )
    return membership.company if membership else None


def subscription_is_usable(subscription: CompanySubscription) -> bool:
    now = datetime.utcnow()
    if subscription.status in ("active", "trialing"):
        return subscription.current_period_end >= now
    if subscription.status in ("past_due", "grace"):
        return bool(subscription.grace_until and subscription.grace_until >= now)
    return False


def require_usable_subscription(
    db: Session, company_id: UUID
) -> CompanySubscription | None:
    subscription = get_current_subscription(db, company_id)
    if not subscription:
        # Legacy/test companies created outside the production onboarding path
        # remain operable until Super Admin assigns their first subscription.
        return None
    if not subscription_is_usable(subscription):
        raise HTTPException(
            status_code=402,
            detail="This company subscription is inactive or past its paid period. Contact the company owner or Sahajomy support.",
        )
    return subscription


def entitlement_map(
    subscription: CompanySubscription | None,
) -> dict[str, PlanEntitlement]:
    if not subscription or not subscription.plan:
        return {}
    return {item.key: item for item in subscription.plan.entitlements}


def require_feature(
    db: Session, company_id: UUID, key: str
) -> CompanySubscription | None:
    subscription = require_usable_subscription(db, company_id)
    if not subscription:
        return None
    entitlement = entitlement_map(subscription).get(key)
    if not entitlement or not entitlement.enabled:
        raise HTTPException(
            status_code=403,
            detail=f"{subscription.plan.name} does not include {key.replace('_', ' ')}. Upgrade the company subscription to continue.",
        )
    return subscription


def entitlement_limit(subscription: CompanySubscription | None, key: str) -> int | None:
    entitlement = entitlement_map(subscription).get(key)
    if not entitlement or not entitlement.enabled:
        return 0 if subscription else None
    return int(entitlement.limit_value) if entitlement.limit_value is not None else None


def enforce_resource_limit(
    db: Session,
    company_id: UUID,
    key: str,
    current_value: int,
    requested: int = 1,
) -> None:
    subscription = require_usable_subscription(db, company_id)
    if not subscription:
        return
    limit = entitlement_limit(subscription, key)
    if limit == -1 or limit is None:
        return
    if current_value + requested > limit:
        raise HTTPException(
            status_code=402,
            detail=(
                f"The {subscription.plan.name} plan allows {limit:,} {key.replace('_', ' ')}. "
                "Upgrade the company subscription or reduce current usage."
            ),
        )


def company_staff_seats(db: Session, company_id: UUID) -> int:
    members = (
        db.query(func.count(CargoCompanyMembership.id))
        .filter(
            CargoCompanyMembership.company_id == company_id,
            CargoCompanyMembership.status.in_(("active", "pending")),
        )
        .scalar()
        or 0
    )
    pending_invites = (
        db.query(func.count(CargoStaffInvitation.id))
        .filter(
            CargoStaffInvitation.company_id == company_id,
            CargoStaffInvitation.status == "pending",
            CargoStaffInvitation.expires_at > datetime.utcnow(),
        )
        .scalar()
        or 0
    )
    return int(members) + int(pending_invites)


def company_branch_count(db: Session, company_id: UUID) -> int:
    return int(
        db.query(func.count(CargoBranch.id))
        .filter(CargoBranch.company_id == company_id, CargoBranch.status == "active")
        .scalar()
        or 0
    )


def _monthly_period(now: datetime | None = None) -> tuple[datetime, datetime]:
    value = now or datetime.utcnow()
    start = value.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    end = (
        start.replace(year=start.year + 1, month=1)
        if start.month == 12
        else start.replace(month=start.month + 1)
    )
    return start, end


def _counter_period(metric: str) -> tuple[datetime, datetime]:
    if metric == "storage_bytes":
        return datetime(2020, 1, 1), datetime(2100, 1, 1)
    return _monthly_period()


def _usage_counter(
    db: Session, company_id: UUID, metric: str, *, lock: bool = False
) -> CompanyUsageCounter:
    start, end = _counter_period(metric)
    query = db.query(CompanyUsageCounter).filter(
        CompanyUsageCounter.company_id == company_id,
        CompanyUsageCounter.metric == metric,
        CompanyUsageCounter.period_start == start,
    )
    if lock:
        query = query.with_for_update()
    counter = query.first()
    if not counter:
        counter = CompanyUsageCounter(
            company_id=company_id,
            metric=metric,
            period_start=start,
            period_end=end,
        )
        db.add(counter)
        db.flush()
    return counter


def consume_usage(
    db: Session,
    company_id: UUID,
    metric: str,
    quantity: int = 1,
    *,
    action: str,
    created_by_id: UUID | None = None,
    resource_type: str | None = None,
    resource_id: str | None = None,
    idempotency_key: str | None = None,
    details: dict[str, Any] | None = None,
) -> CompanyUsageCounter | None:
    if quantity <= 0:
        raise ValueError("Usage quantity must be positive")
    if idempotency_key:
        existing = (
            db.query(SubscriptionUsageEvent)
            .filter(SubscriptionUsageEvent.idempotency_key == idempotency_key)
            .first()
        )
        if existing:
            return _usage_counter(db, company_id, metric)
    subscription = require_usable_subscription(db, company_id)
    if not subscription:
        return None
    limit = entitlement_limit(subscription, metric)
    if limit == 0:
        raise HTTPException(
            status_code=403,
            detail=f"{subscription.plan.name} does not include {metric.replace('_', ' ')}.",
        )
    counter = _usage_counter(db, company_id, metric, lock=True)
    if (
        limit not in (None, -1)
        and counter.used_amount + counter.pending_amount + quantity > limit
    ):
        raise HTTPException(
            status_code=402,
            detail=(
                f"The company has reached its monthly {metric.replace('_', ' ')} limit "
                f"of {limit:,}. Upgrade the subscription or add an overage pack."
            ),
        )
    counter.used_amount += quantity
    db.add(
        SubscriptionUsageEvent(
            company_id=company_id,
            metric=metric,
            quantity=quantity,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            idempotency_key=idempotency_key,
            details_json=details or {},
            created_by_id=created_by_id,
        )
    )
    db.flush()
    return counter


def hold_storage(db: Session, company_id: UUID, byte_count: int) -> None:
    if byte_count < 0:
        raise ValueError("Storage hold cannot be negative")
    subscription = require_usable_subscription(db, company_id)
    if not subscription:
        return
    limit = entitlement_limit(subscription, "storage_bytes")
    counter = _usage_counter(db, company_id, "storage_bytes", lock=True)
    if (
        limit not in (None, -1)
        and counter.used_amount + counter.pending_amount + byte_count > limit
    ):
        raise HTTPException(
            status_code=402,
            detail=(
                f"This upload exceeds the {subscription.plan.name} storage limit. "
                "Delete unused files or upgrade the company subscription."
            ),
        )
    counter.pending_amount += byte_count
    db.flush()


def release_storage_hold(db: Session, company_id: UUID, byte_count: int) -> None:
    subscription = get_current_subscription(db, company_id)
    if not subscription:
        return
    counter = _usage_counter(db, company_id, "storage_bytes", lock=True)
    counter.pending_amount = max(0, counter.pending_amount - max(byte_count, 0))
    db.flush()


def finalize_storage_asset(
    db: Session,
    company_id: UUID,
    *,
    public_id: str,
    secure_url: str,
    byte_count: int,
    held_bytes: int,
    resource_type: str,
    asset_kind: str,
    uploaded_by_id: UUID | None = None,
) -> CompanyStorageAsset | None:
    subscription = get_current_subscription(db, company_id)
    if not subscription:
        return None
    counter = _usage_counter(db, company_id, "storage_bytes", lock=True)
    counter.pending_amount = max(0, counter.pending_amount - max(held_bytes, 0))
    existing = (
        db.query(CompanyStorageAsset)
        .filter(CompanyStorageAsset.public_id == public_id)
        .with_for_update()
        .first()
    )
    previous_bytes = existing.bytes if existing and existing.status == "active" else 0
    delta = max(byte_count, 0) - previous_bytes
    limit = entitlement_limit(subscription, "storage_bytes")
    if limit not in (None, -1) and counter.used_amount + delta > limit:
        raise HTTPException(402, "The uploaded file exceeds the company storage limit.")
    counter.used_amount = max(0, counter.used_amount + delta)
    if existing:
        asset = existing
        asset.company_id = company_id
        asset.secure_url = secure_url
        asset.bytes = max(byte_count, 0)
        asset.resource_type = resource_type
        asset.asset_kind = asset_kind
        asset.status = "active"
        asset.deleted_at = None
        asset.uploaded_by_id = uploaded_by_id
    else:
        asset = CompanyStorageAsset(
            company_id=company_id,
            public_id=public_id,
            secure_url=secure_url,
            bytes=max(byte_count, 0),
            resource_type=resource_type,
            asset_kind=asset_kind,
            uploaded_by_id=uploaded_by_id,
        )
        db.add(asset)
    # Storage is one component of Cloudinary credits. Record its approximate
    # milli-credit contribution; bandwidth and transformations are reconciled
    # separately by Super Admin from the provider invoice/usage export.
    if delta > 0:
        milli_credits = max(1, math.ceil(delta * 1000 / GIB))
        consume_usage(
            db,
            company_id,
            "cloudinary_credits_milli",
            milli_credits,
            action="cloudinary_storage_added",
            created_by_id=uploaded_by_id,
            resource_type=resource_type,
            resource_id=public_id,
            idempotency_key=f"cloudinary-storage:{public_id}:{byte_count}",
        )
    db.flush()
    return asset


def set_usage_amount(
    db: Session, company_id: UUID, metric: str, used_amount: int
) -> CompanyUsageCounter:
    if used_amount < 0:
        raise HTTPException(422, "Usage cannot be negative.")
    counter = _usage_counter(db, company_id, metric, lock=True)
    counter.used_amount = used_amount
    db.flush()
    return counter


def usage_payload(db: Session, company_id: UUID) -> dict[str, Any]:
    subscription = get_current_subscription(db, company_id)
    if not subscription:
        return {
            "subscription": None,
            "usage": [],
            "requires_assignment": True,
        }
    entitlements = entitlement_map(subscription)
    staff = company_staff_seats(db, company_id)
    branches = company_branch_count(db, company_id)
    metrics = {
        "staff_users": staff,
        "branches": branches,
        "storage_bytes": _usage_counter(db, company_id, "storage_bytes").used_amount,
        "cloudinary_credits_milli": _usage_counter(
            db, company_id, "cloudinary_credits_milli"
        ).used_amount,
        "automation_events": _usage_counter(
            db, company_id, "automation_events"
        ).used_amount,
    }
    usage = []
    for key, used in metrics.items():
        entitlement = entitlements.get(key)
        limit = (
            int(entitlement.limit_value)
            if entitlement and entitlement.limit_value is not None
            else None
        )
        percentage = None
        if limit and limit > 0:
            percentage = round(min(used / limit * 100, 999.99), 2)
        usage.append(
            {
                "metric": key,
                "used": int(used),
                "limit": limit,
                "unit": entitlement.unit if entitlement else None,
                "percentage": percentage,
            }
        )
    return {
        "subscription": subscription_payload(subscription),
        "usage": usage,
        "requires_assignment": False,
    }


def plan_payload(plan: SubscriptionPlan) -> dict[str, Any]:
    return {
        "id": str(plan.id),
        "code": plan.code,
        "name": plan.name,
        "description": plan.description,
        "monthly_price": float(plan.monthly_price or 0),
        "annual_price": float(plan.annual_price or 0),
        "currency": plan.currency,
        "display_order": int(plan.display_order or 0),
        "is_active": bool(plan.is_active),
        "is_custom": bool(plan.is_custom),
        "entitlements": {
            item.key: {
                "enabled": bool(item.enabled),
                "limit": (
                    int(item.limit_value) if item.limit_value is not None else None
                ),
                "unit": item.unit,
                "overage_unit_price": (
                    float(item.overage_unit_price)
                    if item.overage_unit_price is not None
                    else None
                ),
            }
            for item in plan.entitlements
        },
    }


def subscription_payload(subscription: CompanySubscription) -> dict[str, Any]:
    return {
        "id": str(subscription.id),
        "company_id": str(subscription.company_id),
        "status": subscription.status,
        "billing_cycle": subscription.billing_cycle,
        "price_amount": float(subscription.price_amount or 0),
        "currency": subscription.currency,
        "current_period_start": subscription.current_period_start.isoformat(),
        "current_period_end": subscription.current_period_end.isoformat(),
        "grace_until": (
            subscription.grace_until.isoformat() if subscription.grace_until else None
        ),
        "auto_renew": bool(subscription.auto_renew),
        "usable": subscription_is_usable(subscription),
        "plan": plan_payload(subscription.plan),
    }


def assign_company_subscription(
    db: Session,
    *,
    company_id: UUID,
    plan: SubscriptionPlan,
    status: str,
    billing_cycle: str,
    period_start: datetime,
    period_end: datetime,
    grace_until: datetime | None,
    auto_renew: bool,
    created_by_id: UUID | None,
    price_amount: Decimal | None = None,
) -> CompanySubscription:
    db.query(CompanySubscription).filter(
        CompanySubscription.company_id == company_id,
        CompanySubscription.status.in_(ACTIVE_SUBSCRIPTION_STATUSES),
    ).update({CompanySubscription.status: "cancelled"}, synchronize_session=False)
    price = price_amount
    if price is None:
        price = plan.annual_price if billing_cycle == "annual" else plan.monthly_price
    row = CompanySubscription(
        id=uuid.uuid4(),
        company_id=company_id,
        plan_id=plan.id,
        status=status,
        billing_cycle=billing_cycle,
        price_amount=price,
        currency=plan.currency,
        current_period_start=period_start,
        current_period_end=period_end,
        grace_until=grace_until,
        auto_renew=auto_renew,
        created_by_id=created_by_id,
    )
    db.add(row)
    db.flush()
    return row
