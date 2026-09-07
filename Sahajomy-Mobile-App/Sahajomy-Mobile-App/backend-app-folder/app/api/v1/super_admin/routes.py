"""
Super Admin API - Platform governance only.
Can: approve/suspend users, set commission, view all analytics, manage goods
classification, create users.
Cannot: create containers, modify sea_bookings, operate logistics.
"""

import logging
import re
from datetime import datetime
from typing import Dict, List, Literal, Optional

from app.api.v1.cargo_company_registrations import (
    AFRICAN_COUNTRIES,
    SERVICE_TYPES,
    SPECIAL_CAPABILITIES,
    SUPPORTED_CURRENCIES,
    serialize_cargo_company_profile,
    sync_cargo_operator_profile_status,
)
from app.api.v1.sourcing_agent.registration_routes import ensure_sourcing_agent_profile
from app.core.audit import log_action
from app.core.dependencies import get_super_admin
from app.core.encryption import data_encryption
from app.core.validation import validate_and_format_phone, validate_email
from app.database import get_db
from app.models.air_cargo import (
    AirCargoRate,
    AirDepartureSchedule,
    ExpressAirCargoBooking,
)
from app.models.cargo_company import CargoOperatorProfile, OperatorGovernanceCase
from app.models.container import (
    Container,
    GoodsCategory,
    GoodsType,
    GoodsTypeAlias,
    GoodsTypeAttributeTemplate,
    Route,
    SeaBooking,
    Warehouse,
)
from app.models.finance import AuditLog  # NEW: Import notification model
from app.models.finance import CommissionSettings, Notification
from app.models.quote_request import QuoteRequest
from app.models.sourcing import SourcingBatch, SourcingOrder
from app.models.sourcing_agent import SourcingAgent
from app.models.user import AuthProvider, RefreshToken, User
from app.services.goods_standardization import (
    HS_VERSION,
    canonical_key,
    find_catalog_conflict,
    normalize_goods_alias,
    validate_english_catalog_name,
    validate_hs_reference,
)
from app.services.realtime_notifications import create_notification
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import case, cast, func, or_
from sqlalchemy.orm import Session
from sqlalchemy.types import String

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/super_admin", tags=["Super Admin"])

DB_SESSION = Depends(get_db)
SUPER_ADMIN_USER = Depends(get_super_admin)


# ─── Schemas ─────────────────────────────────────────────


class UserStatusUpdate(BaseModel):
    status: str  # active | suspended | pending_approval


class UserCreate(BaseModel):
    """Schema for creating a new user via Super Admin."""

    name: str = Field(
        ..., min_length=2, max_length=150, description="Full name of the user"
    )
    phone_number: str = Field(..., description="Phone number with country code")
    email: Optional[str] = Field(None, description="Email address of the user")
    role: str = Field(
        "customer", description="User role: customer, sourcing_agent, cargo_admin"
    )
    status: str = Field(
        "active", description="Initial status: active, pending_approval, suspended"
    )


class CargoOperatorDecision(BaseModel):
    decision: Literal["approve", "reject", "suspend", "reactivate"]
    reason: Optional[str] = Field(default=None, max_length=2000)


class CargoOperatorProfileUpdate(BaseModel):
    company_name: Optional[str] = Field(default=None, min_length=2, max_length=180)
    registration_number: Optional[str] = Field(default=None, max_length=120)
    website: Optional[str] = Field(default=None, max_length=255)
    headquarters_country: Optional[str] = Field(default=None, max_length=100)
    headquarters_city: Optional[str] = Field(default=None, max_length=120)
    china_origin_cities: Optional[List[str]] = Field(default=None, max_length=20)
    destination_countries: Optional[List[str]] = Field(default=None, max_length=54)
    service_types: Optional[List[str]] = Field(default=None, max_length=8)
    special_capabilities: Optional[List[str]] = Field(default=None, max_length=6)
    preferred_currencies: Optional[List[str]] = Field(default=None, max_length=10)
    years_experience: Optional[str] = Field(default=None, max_length=30)
    operations_summary: Optional[str] = Field(default=None, max_length=1500)
    compliance_status: Optional[
        Literal["not_submitted", "pending", "verified", "rejected", "expired"]
    ] = None
    compliance_documents: Optional[List[str]] = Field(default=None, max_length=30)
    compliance_expires_at: Optional[datetime] = None


class CargoOperatorServiceControlUpdate(BaseModel):
    service_statuses: Dict[str, Literal["pending", "approved", "paused", "rejected"]]
    booking_paused: bool = False
    reason: Optional[str] = Field(default=None, max_length=2000)


class OperatorCaseCreate(BaseModel):
    category: Literal[
        "compliance",
        "complaint",
        "incident",
        "dispute",
        "fraud",
        "service_quality",
        "finance",
        "other",
    ]
    severity: Literal["low", "medium", "high", "critical"] = "medium"
    title: str = Field(..., min_length=3, max_length=180)
    description: str = Field(..., min_length=3, max_length=5000)


class OperatorCaseUpdate(BaseModel):
    status: Literal["open", "investigating", "resolved", "dismissed"]
    resolution: Optional[str] = Field(default=None, max_length=5000)


class CommissionUpdate(BaseModel):
    commission_percentage: float


class GoodsCategoryCreate(BaseModel):
    name: str
    description: Optional[str] = None


class GoodsTypeCreate(BaseModel):
    category_id: str
    name: str
    description: Optional[str] = None
    hs_reference: Optional[str] = None
    hs_level: Optional[Literal["chapter", "heading", "subheading", "multiple"]] = None
    customs_description: Optional[str] = None
    aliases: List[str] = Field(default_factory=list, max_length=30)
    is_hazardous: bool = False
    requires_special_handling: bool = False


class GoodsTypeUpdate(BaseModel):
    name: Optional[str] = None
    category_id: Optional[str] = None
    description: Optional[str] = None
    hs_reference: Optional[str] = None
    hs_level: Optional[Literal["chapter", "heading", "subheading", "multiple"]] = None
    customs_description: Optional[str] = None
    is_hazardous: Optional[bool] = None
    requires_special_handling: Optional[bool] = None
    is_active: Optional[bool] = None


class GoodsTypeAttributeTemplateCreate(BaseModel):
    key: str = Field(..., min_length=1, max_length=60)
    label: str = Field(..., min_length=1, max_length=100)
    field_type: Literal["text", "number", "select", "multiselect", "boolean"] = "text"
    allowed_values: List[str] = Field(default_factory=list, max_length=30)
    is_required: bool = False
    customer_visible: bool = True
    is_variant_option: bool = False
    sort_order: int = Field(default=0, ge=0, le=1000)


class GoodsTypeAttributeTemplateUpdate(BaseModel):
    label: Optional[str] = Field(default=None, min_length=1, max_length=100)
    field_type: Optional[
        Literal["text", "number", "select", "multiselect", "boolean"]
    ] = None
    allowed_values: Optional[List[str]] = Field(default=None, max_length=30)
    is_required: Optional[bool] = None
    customer_visible: Optional[bool] = None
    is_variant_option: Optional[bool] = None
    sort_order: Optional[int] = Field(default=None, ge=0, le=1000)
    is_active: Optional[bool] = None


class OverrideAction(BaseModel):
    reason: str  # REQUIRED for all override actions


class GoodsCategoryUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    is_active: Optional[bool] = None


def _normalized_catalog_name(value: str) -> str:
    return " ".join((value or "").split()).strip()


def _catalog_conflict_or_none(
    db: Session, name: str, exclude_id: Optional[str] = None
) -> GoodsType | None:
    return find_catalog_conflict(db, name, exclude_id=exclude_id)


def _goods_type_name_exists(
    db: Session, name: str, exclude_id: Optional[str] = None
) -> bool:
    query = db.query(GoodsType).filter(
        func.lower(func.trim(GoodsType.name)) == _normalized_catalog_name(name).lower()
    )
    if exclude_id:
        query = query.filter(GoodsType.id != exclude_id)
    return query.first() is not None


def _goods_category_name_exists(
    db: Session, name: str, exclude_id: Optional[str] = None
) -> bool:
    query = db.query(GoodsCategory).filter(
        func.lower(func.trim(GoodsCategory.name))
        == _normalized_catalog_name(name).lower()
    )
    if exclude_id:
        query = query.filter(GoodsCategory.id != exclude_id)
    return query.first() is not None


# ─── NEW SCHEMAS FOR USER MANAGEMENT ─────────────────────────────────────


class UserNameUpdate(BaseModel):
    name: str = Field(
        ..., min_length=2, max_length=150, description="Updated full name of the user"
    )


class UserPhoneUpdate(BaseModel):
    phone_number: str = Field(..., description="New phone number with country code")


# ─── User Management ─────────────────────────────────────


@router.get("/users")
def list_all_users(
    role: Optional[str] = None,
    status: Optional[str] = None,
    search: Optional[str] = None,
    page: int = 1,
    size: int = 20,
    db: Session = DB_SESSION,
    admin: User = SUPER_ADMIN_USER,
):
    """List all registered users with optional filters."""

    # Create subquery for container count
    container_count_subq = (
        db.query(Container.admin_id, func.count(Container.id).label("container_count"))
        .group_by(Container.admin_id)
        .subquery()
    )

    q = db.query(User, container_count_subq.c.container_count).outerjoin(
        container_count_subq, User.id == container_count_subq.c.admin_id
    )

    if role:
        role_list = role.split(",") if "," in role else [role]
        q = q.filter(User.role.in_(role_list))
    if status:
        q = q.filter(User.status == status)
    if search:
        q = q.filter(
            User.name.ilike(f"%{search}%")
            | User.phone_number.ilike(f"%{search}%")
            | User.email.ilike(f"%{search}%")
        )

    total = q.count()
    users = q.offset((page - 1) * size).limit(size).all()

    return {
        "total": total,
        "page": page,
        "size": size,
        "data": [
            {
                "id": str(u.User.id),
                "phone_number": u.User.phone_number,
                "email": u.User.email,
                "name": u.User.name,
                "role": u.User.role,
                "status": u.User.status,
                "is_verified": u.User.is_verified,
                "created_at": u.User.created_at,
                "container_count": (
                    u.container_count or 0 if u.container_count is not None else 0
                ),
            }
            for u in users
        ],
    }


@router.get("/users/recent")
def get_recent_users(
    limit: int = 5,
    db: Session = DB_SESSION,
    admin: User = SUPER_ADMIN_USER,
):
    """Get most recent user registrations."""
    users = db.query(User).order_by(User.created_at.desc()).limit(limit).all()
    return [
        {
            "id": str(u.id),
            "name": u.name,
            "phone_number": u.phone_number,
            "email": u.email,  # Include email in recent users
            "role": u.role,
            "status": u.status,
            "created_at": u.created_at,
        }
        for u in users
    ]


@router.get("/users/pending")
def get_pending_users(
    limit: int = 5,
    db: Session = DB_SESSION,
    admin: User = SUPER_ADMIN_USER,
):
    """
    Get users pending approval.
    ONLY Cargo Admins and Sourcing Agents need approval.
    Customers are auto-approved.
    """
    users = (
        db.query(User)
        .filter(
            User.status == "pending_approval",
            User.role.in_(["cargo_admin", "sourcing_agent"]),
        )
        .order_by(User.created_at.desc())
        .limit(limit)
        .all()
    )
    return [
        {
            "id": str(u.id),
            "name": u.name,
            "phone_number": u.phone_number,
            "email": u.email,  # Include email in pending users
            "role": u.role,
            "status": u.status,
            "created_at": u.created_at,
        }
        for u in users
    ]


@router.patch("/users/{user_id}/status")
def update_user_status(
    user_id: str,
    body: UserStatusUpdate,
    db: Session = DB_SESSION,
    admin: User = SUPER_ADMIN_USER,
):
    """Update user status."""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Validate status
    valid_statuses = ["active", "suspended", "pending_approval"]
    if body.status not in valid_statuses:
        raise HTTPException(
            status_code=400, detail=f"Invalid status. Valid options: {valid_statuses}"
        )

    # Permission validation: an admin may not suspend their own account
    # (suspended users are blocked at login — this would be an unrecoverable lockout).
    if body.status == "suspended" and str(user.id) == str(admin.id):
        raise HTTPException(
            status_code=403,
            detail="You cannot suspend your own account. Ask another super admin.",
        )

    old_status = user.status
    if old_status == body.status:
        return {"message": f"User status is already {body.status}"}

    user.status = body.status
    if user.role == "cargo_admin":
        sync_cargo_operator_profile_status(
            db, user=user, status=body.status, verified_by=admin.id
        )
    elif user.role == "sourcing_agent":
        sourcing_profile = (
            db.query(SourcingAgent).filter(SourcingAgent.user_id == user.id).first()
        )
        if sourcing_profile:
            if body.status == "active":
                sourcing_profile.status = "verified"
                sourcing_profile.is_verified = True
                sourcing_profile.verified_at = datetime.utcnow()
                sourcing_profile.verified_by = admin.id
                user.is_verified = True
            elif body.status == "pending_approval":
                sourcing_profile.status = "pending"
                sourcing_profile.is_verified = False
                sourcing_profile.verified_at = None
                sourcing_profile.verified_by = None
                user.is_verified = False
            else:
                sourcing_profile.status = "inactive"
                sourcing_profile.is_verified = False
                sourcing_profile.verified_at = None
                sourcing_profile.verified_by = None
                user.is_verified = False
    # Note: is_active is not synchronized with status so suspended users can
    # still receive OTPs when needed.
    # The OTP verification process will handle the suspended status appropriately
    db.commit()

    # Log the action
    log_action(
        db=db,
        action="USER_STATUS_CHANGED",
        user_id=admin.id,
        entity_type="user",
        entity_id=user_id,
        metadata={
            "old_status": old_status,
            "new_status": body.status,
            "changed_by": str(admin.id),
        },
    )

    return {"message": f"User status updated to {body.status}"}


class UserVerificationUpdate(BaseModel):
    is_verified: bool


@router.patch("/users/{user_id}/verification")
def update_user_verification(
    user_id: str,
    body: UserVerificationUpdate,
    db: Session = DB_SESSION,
    admin: User = SUPER_ADMIN_USER,
):
    """Manually set a user's verified status (super-admin override, bypasses OTP)."""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    old_value = bool(user.is_verified)
    if old_value == body.is_verified:
        return {
            "message": "User verification status unchanged",
            "is_verified": old_value,
        }

    if user.role == "cargo_admin" and user.cargo_operator_profile:
        user.status = "active" if body.is_verified else "suspended"
        sync_cargo_operator_profile_status(
            db,
            user=user,
            status=user.status,
            verified_by=admin.id if body.is_verified else None,
        )
    else:
        user.is_verified = body.is_verified
    db.commit()

    # Log the action
    log_action(
        db=db,
        action="USER_VERIFICATION_CHANGED",
        user_id=admin.id,
        entity_type="user",
        entity_id=user_id,
        metadata={
            "old_is_verified": old_value,
            "new_is_verified": body.is_verified,
            "changed_by": str(admin.id),
        },
    )

    return {
        "message": (
            "User marked as verified"
            if body.is_verified
            else "User marked as unverified"
        ),
        "is_verified": body.is_verified,
    }


@router.post("/users/{user_id}/revoke-tokens")
def revoke_user_tokens(
    user_id: str,
    db: Session = DB_SESSION,
    admin: User = SUPER_ADMIN_USER,
):
    """Revoke every refresh token for a user, logging them out of all devices."""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    revoked_count = (
        db.query(RefreshToken)
        .filter(RefreshToken.user_id == user.id, RefreshToken.revoked.is_(False))
        .update({RefreshToken.revoked: True}, synchronize_session=False)
    )
    db.commit()

    # Log the action
    log_action(
        db=db,
        action="USER_TOKENS_REVOKED",
        user_id=admin.id,
        entity_type="user",
        entity_id=user_id,
        metadata={
            "revoked_token_count": revoked_count,
            "changed_by": str(admin.id),
        },
    )

    return {
        "message": "All tokens revoked",
        "revoked_count": revoked_count,
    }


class UserEmailUpdate(BaseModel):
    email: str


@router.patch("/users/{user_id}/email")
def update_user_email(
    user_id: str,
    body: UserEmailUpdate,
    db: Session = DB_SESSION,
    admin: User = SUPER_ADMIN_USER,
):
    """Update user email."""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    email = body.email.strip()

    # Validate email format
    if not validate_email(email):
        raise HTTPException(status_code=400, detail="Invalid email format")

    email_hash = data_encryption.hash_email(email)

    # Check if email already exists for another user
    existing_user = (
        db.query(User)
        .filter(
            User.id != user_id,
            or_(User.email_hash == email_hash, User.email == email),
        )
        .first()
    )
    if existing_user:
        raise HTTPException(
            status_code=400, detail="Email is already registered with another account."
        )

    old_email = user.email or user.secure_email
    user.email = email

    # Keep secure fields in sync (OTP delivery and duplicate checks rely on them)
    user.email_encrypted = data_encryption.encrypt_email(email)
    user.email_hash = email_hash

    db.commit()

    # Log the action
    log_action(
        db=db,
        action="USER_EMAIL_CHANGED",
        user_id=admin.id,
        entity_type="user",
        entity_id=user_id,
        metadata={
            "old_email": data_encryption.mask_email(old_email) if old_email else None,
            "new_email": data_encryption.mask_email(email),
            "changed_by": str(admin.id),
        },
    )

    return {"message": f"User email updated to {email}"}


@router.get("/users/{user_id}")
def get_user_details(
    user_id: str,
    db: Session = DB_SESSION,
    admin: User = SUPER_ADMIN_USER,
):
    """Get detailed user information."""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    response = {
        "id": str(user.id),
        "phone_number": user.phone_number or user.secure_phone,
        "email": user.email or user.secure_email,
        "name": user.name,
        "role": user.role,
        "status": user.status,
        "is_verified": user.is_verified,
        "auth_provider": user.auth_provider.value,
        "created_at": user.created_at,
        "updated_at": user.updated_at,
    }
    if user.role == "cargo_admin" and user.cargo_operator_profile:
        response["cargo_operator_profile"] = serialize_cargo_company_profile(
            user.cargo_operator_profile
        )
        container_ids = db.query(Container.id).filter(Container.admin_id == user.id)
        response["metrics"] = {
            "containers": db.query(func.count(Container.id))
            .filter(Container.admin_id == user.id)
            .scalar()
            or 0,
            "warehouses": db.query(func.count(Warehouse.id))
            .filter(Warehouse.admin_id == user.id)
            .scalar()
            or 0,
            "sea_bookings": db.query(func.count(SeaBooking.id))
            .filter(SeaBooking.container_id.in_(container_ids))
            .scalar()
            or 0,
            "air_bookings": db.query(func.count(ExpressAirCargoBooking.id))
            .filter(ExpressAirCargoBooking.cargo_admin_id == user.id)
            .scalar()
            or 0,
            "air_booking_value": float(
                db.query(
                    func.coalesce(func.sum(ExpressAirCargoBooking.quoted_total), 0)
                )
                .filter(ExpressAirCargoBooking.cargo_admin_id == user.id)
                .scalar()
                or 0
            ),
        }
    elif user.role == "sourcing_agent":
        batch_ids = db.query(SourcingBatch.id).filter(SourcingBatch.agent_id == user.id)
        response["metrics"] = {
            "batches": db.query(func.count(SourcingBatch.id))
            .filter(SourcingBatch.agent_id == user.id)
            .scalar()
            or 0,
            "orders": db.query(func.count(SourcingOrder.id))
            .filter(SourcingOrder.batch_id.in_(batch_ids))
            .scalar()
            or 0,
            "earned_commission": float(
                db.query(func.coalesce(func.sum(SourcingOrder.commission_amount), 0))
                .filter(
                    SourcingOrder.batch_id.in_(batch_ids),
                    SourcingOrder.commission_status == "earned",
                )
                .scalar()
                or 0
            ),
        }
    elif user.role == "customer":
        response["metrics"] = {
            "sea_bookings": db.query(func.count(SeaBooking.id))
            .filter(SeaBooking.user_id == user.id)
            .scalar()
            or 0,
            "air_bookings": db.query(func.count(ExpressAirCargoBooking.id))
            .filter(ExpressAirCargoBooking.customer_id == user.id)
            .scalar()
            or 0,
            "active_sea_bookings": db.query(func.count(SeaBooking.id))
            .filter(
                SeaBooking.user_id == user.id,
                SeaBooking.goods_status != "collected",
            )
            .scalar()
            or 0,
        }
    return response


# ─── UPDATE USER NAME ─────────────────────────────────────


@router.patch("/users/{user_id}/name")
def update_user_name(
    user_id: str,
    body: UserNameUpdate,
    db: Session = DB_SESSION,
    admin: User = SUPER_ADMIN_USER,
):
    """Update user name."""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    old_name = user.name
    user.name = body.name.strip()
    db.commit()

    # Log the action
    log_action(
        db=db,
        action="USER_NAME_CHANGED",
        user_id=admin.id,
        entity_type="user",
        entity_id=user_id,
        metadata={
            "old_name": old_name,
            "new_name": body.name,
            "changed_by": str(admin.id),
        },
    )

    return {"message": f"User name updated to {body.name}"}


# ─── DELETE USER ACCOUNT ─────────────────────────────────────


@router.delete("/users/{user_id}")
def delete_user_account(
    user_id: str,
    db: Session = DB_SESSION,
    admin: User = SUPER_ADMIN_USER,
):
    """Delete user account permanently."""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Prevent deletion of other super admins
    if user.role == "super_admin" and user.id != admin.id:
        raise HTTPException(
            status_code=403, detail="Cannot delete other super admin accounts"
        )

    # Prevent self-deletion
    if user.id == admin.id:
        raise HTTPException(status_code=403, detail="Cannot delete your own account")

    user_name = user.name
    user_phone = user.phone_number

    # Delete the user
    db.delete(user)
    db.commit()

    # Log the action
    log_action(
        db=db,
        action="USER_ACCOUNT_DELETED",
        user_id=admin.id,
        entity_type="user",
        entity_id=user_id,
        metadata={
            "deleted_user_name": user_name,
            "deleted_user_phone": user_phone,
            "deleted_by": str(admin.id),
        },
    )

    return {"message": f"User account '{user_name}' deleted successfully"}


# ─── CHANGE USER PHONE NUMBER ─────────────────────────────────────


@router.patch("/users/{user_id}/phone")
def change_user_phone_number(
    user_id: str,
    body: UserPhoneUpdate,
    db: Session = DB_SESSION,
    admin: User = SUPER_ADMIN_USER,
):
    """Change user phone number."""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Normalize phone number to E.164 — must match the OTP login lookup format
    is_valid_phone, formatted_phone = validate_and_format_phone(body.phone_number)
    if not is_valid_phone:
        raise HTTPException(status_code=400, detail="Invalid phone number format")

    phone_hash = data_encryption.hash_phone(formatted_phone)

    # Check if phone number already exists for another user
    existing_user = (
        db.query(User)
        .filter(
            User.id != user_id,
            or_(User.phone_hash == phone_hash, User.phone_number == formatted_phone),
        )
        .first()
    )
    if existing_user:
        raise HTTPException(
            status_code=400,
            detail="Phone number is already registered with another account.",
        )

    old_phone = user.phone_number or user.secure_phone
    user.phone_number = formatted_phone

    # Keep secure fields in sync with the normalized phone number
    user.phone_encrypted = data_encryption.encrypt_phone(formatted_phone)
    user.phone_hash = phone_hash

    db.commit()

    # Log the action
    log_action(
        db=db,
        action="USER_PHONE_CHANGED",
        user_id=admin.id,
        entity_type="user",
        entity_id=user_id,
        metadata={
            "old_phone": data_encryption.mask_phone(old_phone) if old_phone else None,
            "new_phone": data_encryption.mask_phone(formatted_phone),
            "changed_by": str(admin.id),
        },
    )

    return {"message": f"User phone number updated to {formatted_phone}"}


# ─── CREATE USER (ADD NEW USER) ───────────────────────────


@router.post("/users/create")
def create_user(
    body: UserCreate,
    db: Session = DB_SESSION,
    admin: User = SUPER_ADMIN_USER,
):
    """
    Create a new user manually (Super Admin only).

    - Customers are automatically activated
    - Cargo Admins and Sourcing Agents go to pending approval

    The phone number is normalized to E.164 and stored together with its
    secure hash/encrypted fields, exactly like the self-registration flow,
    so the created user can sign in through the standard OTP login.
    """

    # Validate role
    valid_roles = ["customer", "sourcing_agent", "cargo_admin", "super_admin"]
    if body.role not in valid_roles:
        raise HTTPException(
            status_code=400, detail=f"Invalid role. Valid options: {valid_roles}"
        )

    # Validate status
    valid_statuses = ["active", "suspended", "pending_approval"]
    if body.status not in valid_statuses:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid status. Valid options: {valid_statuses}",
        )

    # Normalize phone number to E.164 — must match the OTP login lookup format
    is_valid_phone, formatted_phone = validate_and_format_phone(body.phone_number)
    if not is_valid_phone:
        raise HTTPException(
            status_code=400,
            detail=(
                "Invalid phone number format. Please provide a valid phone "
                "number with country code."
            ),
        )

    # Email is required: OTP sign-in codes are delivered by email only,
    # so a user without an email address can never log in.
    if not body.email or not body.email.strip():
        raise HTTPException(
            status_code=400,
            detail=(
                "Email is required. OTP sign-in codes are sent by email, so "
                "the user needs an email address to log in."
            ),
        )

    email = body.email.strip()
    if not validate_email(email):
        raise HTTPException(
            status_code=400,
            detail=(
                "Invalid email format or disposable email address. Please "
                "provide a valid email address."
            ),
        )

    phone_hash = data_encryption.hash_phone(formatted_phone)
    email_hash = data_encryption.hash_email(email)

    # Check if phone already exists (secure hash or plain text)
    existing = (
        db.query(User)
        .filter(
            or_(User.phone_hash == phone_hash, User.phone_number == formatted_phone)
        )
        .first()
    )
    if existing:
        raise HTTPException(
            status_code=400, detail="User with this phone already exists"
        )

    # Check if email already exists (secure hash or plain text)
    existing_email = (
        db.query(User)
        .filter(or_(User.email_hash == email_hash, User.email == email))
        .first()
    )
    if existing_email:
        raise HTTPException(
            status_code=400, detail="User with this email already exists"
        )

    # Determine initial status based on role
    status = body.status

    # Force pending approval for operators if trying to set as active
    if body.role in ["cargo_admin", "sourcing_agent"]:
        if status == "active":
            status = "pending_approval"
        elif status == "pending_approval":
            status = "pending_approval"

    # Determine verification status
    is_verified = False
    if body.role == "customer" and status == "active":
        is_verified = True

    # Create user with secure identifier fields so OTP login can find them
    user = User(
        phone_number=formatted_phone,
        phone_encrypted=data_encryption.encrypt_phone(formatted_phone),
        phone_hash=phone_hash,
        email=email,
        email_encrypted=data_encryption.encrypt_email(email),
        email_hash=email_hash,
        name=body.name.strip(),
        auth_provider=AuthProvider.OTP,
        is_active=True,
        role=body.role,
        status=status,
        is_verified=is_verified,
    )

    db.add(user)
    db.commit()
    db.refresh(user)

    # Log the action
    log_action(
        db=db,
        action="USER_CREATED_BY_ADMIN",
        user_id=admin.id,
        entity_type="user",
        entity_id=user.id,
        metadata={
            "created_user": str(user.id),
            "role": user.role,
            "status": user.status,
            "phone": data_encryption.mask_phone(formatted_phone),
            "email": data_encryption.mask_email(email),
        },
    )

    # Admin-created sourcing agents must appear in the Sourcing Agents
    # review section, exactly like self-registered agents do.
    if user.role == "sourcing_agent":
        if ensure_sourcing_agent_profile(db, user):
            db.commit()

    # Return response
    return {
        "id": str(user.id),
        "name": user.name,
        "phone_number": user.phone_number or user.secure_phone,
        "email": user.email or user.secure_email,
        "role": user.role,
        "status": user.status,
        "is_verified": user.is_verified,
        "message": f"User created successfully. Status: {status}",
    }


# ─── Commission Settings ──────────────────────────────────


@router.get("/commission")
def get_commission(db: Session = DB_SESSION, admin: User = SUPER_ADMIN_USER):
    """Get current marketplace commission rate."""
    setting = (
        db.query(CommissionSettings)
        .order_by(CommissionSettings.effective_from.desc())
        .first()
    )
    if not setting:
        return {"commission_percentage": 1.00}
    return {
        "id": str(setting.id),
        "commission_percentage": float(setting.commission_percentage),
        "effective_from": setting.effective_from,
    }


@router.post("/commission")
def set_commission(
    body: CommissionUpdate,
    db: Session = DB_SESSION,
    admin: User = SUPER_ADMIN_USER,
):
    """Update the global marketplace commission percentage."""
    if not (0 < body.commission_percentage <= 100):
        raise HTTPException(
            status_code=400, detail="Commission must be between 0 and 100"
        )

    setting = CommissionSettings(commission_percentage=body.commission_percentage)
    db.add(setting)

    log_action(
        db=db,
        action="COMMISSION_RATE_UPDATED",
        user_id=admin.id,
        entity_type="commission_settings",
        metadata={"new_rate": body.commission_percentage},
    )

    db.commit()
    return {
        "message": "Commission updated",
        "commission_percentage": body.commission_percentage,
    }


@router.get("/commission/history")
def get_commission_history(
    db: Session = DB_SESSION,
    admin: User = SUPER_ADMIN_USER,
):
    """Get historical commission rate changes."""
    history = (
        db.query(CommissionSettings)
        .order_by(CommissionSettings.effective_from.desc())
        .all()
    )

    return [
        {
            "id": str(record.id),
            "commission_percentage": float(record.commission_percentage),
            "effective_from": record.effective_from,
        }
        for record in history
    ]


# ─── Goods Classification Governance ─────────────────────


@router.get("/goods/categories")
def list_goods_categories(db: Session = DB_SESSION, admin: User = SUPER_ADMIN_USER):
    categories = (
        db.query(GoodsCategory)
        .filter(GoodsCategory.is_standard.is_(True))
        .order_by(GoodsCategory.name.asc())
        .all()
    )

    return [
        {
            "id": str(cat.id),
            "name": cat.name,
            "description": cat.description,
            "canonical_key": cat.canonical_key,
            "standard_version": cat.standard_version,
            "is_active": cat.is_active,
            "goods_types": [
                {
                    "id": str(gt.id),
                    "name": gt.name,
                    "canonical_key": gt.canonical_key,
                    "hs_reference": gt.hs_reference,
                    "hs_level": gt.hs_level,
                    "hs_version": gt.hs_version,
                    "customs_description": gt.customs_description,
                    "is_active": gt.is_active,
                    "is_hazardous": gt.is_hazardous,
                    "requires_special_handling": gt.requires_special_handling,
                }
                for gt in cat.goods_types
                if gt.is_customs_standard
            ],
        }
        for cat in categories
    ]


@router.post("/goods/categories")
def create_goods_category(
    body: GoodsCategoryCreate,
    db: Session = DB_SESSION,
    admin: User = SUPER_ADMIN_USER,
):
    name = validate_english_catalog_name(body.name, label="Goods Category")
    if _goods_category_name_exists(db, name):
        raise HTTPException(
            status_code=409, detail="A Goods Category with this name already exists"
        )
    cat = GoodsCategory(
        name=name,
        description=body.description,
        canonical_key=canonical_key(name),
        standard_version=HS_VERSION,
        is_standard=True,
    )
    db.add(cat)
    db.commit()
    db.refresh(cat)
    return {"id": str(cat.id), "name": cat.name}


@router.patch("/goods/categories/{category_id}")
def update_goods_category(
    category_id: str,
    body: GoodsCategoryUpdate,
    db: Session = DB_SESSION,
    admin: User = SUPER_ADMIN_USER,
):
    cat = db.query(GoodsCategory).filter(GoodsCategory.id == category_id).first()
    if not cat:
        raise HTTPException(status_code=404, detail="Category not found")

    if body.name is not None:
        name = validate_english_catalog_name(body.name, label="Goods Category")
        if _goods_category_name_exists(db, name, category_id):
            raise HTTPException(
                status_code=409, detail="A Goods Category with this name already exists"
            )
        cat.name = name
        cat.canonical_key = canonical_key(name)
    if body.description is not None:
        cat.description = body.description
    if body.is_active is not None:
        cat.is_active = body.is_active

    db.commit()
    return {"message": "Category updated"}


@router.get("/goods/types")
def list_goods_types(db: Session = DB_SESSION, admin: User = SUPER_ADMIN_USER):
    types = (
        db.query(GoodsType)
        .filter(GoodsType.is_customs_standard.is_(True))
        .order_by(GoodsType.name.asc())
        .all()
    )
    return [
        {
            "id": str(t.id),
            "name": t.name,
            "category_id": str(t.category_id) if t.category_id else None,
            "canonical_key": t.canonical_key,
            "hs_reference": t.hs_reference,
            "hs_level": t.hs_level,
            "hs_version": t.hs_version,
            "customs_description": t.customs_description,
            "is_hazardous": t.is_hazardous,
            "requires_special_handling": t.requires_special_handling,
            "is_active": t.is_active,
        }
        for t in types
    ]


@router.post("/goods/types")
def create_goods_type(
    body: GoodsTypeCreate,
    db: Session = DB_SESSION,
    admin: User = SUPER_ADMIN_USER,
):
    name = validate_english_catalog_name(body.name)
    conflict = _catalog_conflict_or_none(db, name)
    if conflict:
        raise HTTPException(
            status_code=409,
            detail=f"Use the existing standardized Goods Type '{conflict.name}'.",
        )
    category = (
        db.query(GoodsCategory)
        .filter(
            GoodsCategory.id == body.category_id,
            GoodsCategory.is_standard.is_(True),
            GoodsCategory.is_active.is_(True),
        )
        .first()
    )
    if not category:
        raise HTTPException(
            status_code=422, detail="Choose an active standard category."
        )
    if not body.hs_reference or not body.hs_level:
        raise HTTPException(
            status_code=422,
            detail="Every Goods Type requires an HS 2022 classification reference.",
        )
    hs_reference, hs_level = validate_hs_reference(body.hs_reference, body.hs_level)
    prepared_aliases = []
    seen_aliases = set()
    for alias_value in [name, *body.aliases]:
        alias_name = validate_english_catalog_name(alias_value, label="Goods alias")
        normalized_alias = normalize_goods_alias(alias_name)
        if normalized_alias in seen_aliases:
            continue
        seen_aliases.add(normalized_alias)
        alias_conflict = _catalog_conflict_or_none(db, alias_name)
        if alias_conflict:
            raise HTTPException(
                status_code=409,
                detail=f"Alias '{alias_name}' already maps to '{alias_conflict.name}'.",
            )
        prepared_aliases.append((alias_name, normalized_alias))

    gt = GoodsType(
        category_id=category.id,
        name=name,
        description=body.description,
        canonical_key=canonical_key(name),
        hs_reference=hs_reference,
        hs_level=hs_level,
        hs_version=HS_VERSION,
        customs_description=(body.customs_description or body.description or name),
        is_customs_standard=True,
        is_hazardous=body.is_hazardous,
        requires_special_handling=body.requires_special_handling,
    )
    db.add(gt)
    db.flush()
    for alias_name, normalized_alias in prepared_aliases:
        db.add(
            GoodsTypeAlias(
                goods_type_id=gt.id,
                alias=alias_name,
                normalized_alias=normalized_alias,
                language="en",
            )
        )
    db.commit()
    db.refresh(gt)
    return {"id": str(gt.id), "name": gt.name}


@router.patch("/goods/types/{type_id}")
def update_goods_type(
    type_id: str,
    body: GoodsTypeUpdate,
    db: Session = DB_SESSION,
    admin: User = SUPER_ADMIN_USER,
):
    gt = (
        db.query(GoodsType)
        .filter(
            GoodsType.id == type_id,
            GoodsType.is_customs_standard.is_(True),
        )
        .first()
    )
    if not gt:
        raise HTTPException(status_code=404, detail="Goods type not found")

    if body.name is not None:
        old_normalized_name = normalize_goods_alias(gt.name)
        name = validate_english_catalog_name(body.name)
        conflict = _catalog_conflict_or_none(db, name, type_id)
        if conflict:
            raise HTTPException(
                status_code=409,
                detail=f"Use the existing standardized Goods Type '{conflict.name}'.",
            )
        gt.name = name
        gt.canonical_key = canonical_key(name)
        canonical_alias = (
            db.query(GoodsTypeAlias)
            .filter(
                GoodsTypeAlias.goods_type_id == gt.id,
                GoodsTypeAlias.normalized_alias == old_normalized_name,
            )
            .first()
        )
        if canonical_alias:
            canonical_alias.alias = name
            canonical_alias.normalized_alias = normalize_goods_alias(name)
    if body.category_id is not None:
        category = (
            db.query(GoodsCategory)
            .filter(
                GoodsCategory.id == body.category_id,
                GoodsCategory.is_standard.is_(True),
            )
            .first()
        )
        if not category:
            raise HTTPException(status_code=422, detail="Choose a standard category.")
        gt.category_id = category.id
    if body.description is not None:
        gt.description = body.description
    if body.hs_reference is not None or body.hs_level is not None:
        hs_reference, hs_level = validate_hs_reference(
            body.hs_reference or gt.hs_reference,
            body.hs_level or gt.hs_level,
        )
        gt.hs_reference = hs_reference
        gt.hs_level = hs_level
        gt.hs_version = HS_VERSION
    if body.customs_description is not None:
        gt.customs_description = body.customs_description
    if body.is_hazardous is not None:
        gt.is_hazardous = body.is_hazardous
    if body.requires_special_handling is not None:
        gt.requires_special_handling = body.requires_special_handling
    if body.is_active is not None:
        gt.is_active = body.is_active

    db.commit()
    return {"message": "Goods type updated", "id": type_id}


def _template_response(template: GoodsTypeAttributeTemplate) -> dict:
    return {
        "id": str(template.id),
        "goods_type_id": str(template.goods_type_id),
        "key": template.key,
        "label": template.label,
        "field_type": template.field_type,
        "allowed_values": template.allowed_values or [],
        "is_required": bool(template.is_required),
        "customer_visible": bool(template.customer_visible),
        "is_variant_option": bool(template.is_variant_option),
        "sort_order": template.sort_order,
        "is_active": bool(template.is_active),
    }


def _validate_template_values(
    key: str, field_type: str, allowed_values: List[str], is_variant_option: bool
) -> tuple[str, list[str]]:
    normalized_key = key.strip().lower().replace(" ", "_")
    if not re.fullmatch(r"[a-z][a-z0-9_]{0,59}", normalized_key):
        raise HTTPException(
            status_code=422,
            detail="Template key must use lowercase letters, numbers, and underscores.",
        )
    normalized_values = []
    for item in allowed_values or []:
        value = str(item or "").strip()
        if not value or len(value) > 100:
            raise HTTPException(
                status_code=422, detail="Template option values must be plain text."
            )
        if value not in normalized_values:
            normalized_values.append(value)
    if (
        field_type in {"select", "multiselect"} or is_variant_option
    ) and not normalized_values:
        raise HTTPException(
            status_code=422, detail="Select and variant fields require allowed values."
        )
    if is_variant_option and field_type not in {"select", "multiselect"}:
        raise HTTPException(
            status_code=422,
            detail="Variant options must use select or multiselect fields.",
        )
    return normalized_key, normalized_values


@router.get("/goods/types/{type_id}/attribute-templates")
def list_goods_type_attribute_templates(
    type_id: str,
    db: Session = DB_SESSION,
    admin: User = SUPER_ADMIN_USER,
):
    rows = (
        db.query(GoodsTypeAttributeTemplate)
        .filter(GoodsTypeAttributeTemplate.goods_type_id == type_id)
        .order_by(
            GoodsTypeAttributeTemplate.sort_order, GoodsTypeAttributeTemplate.created_at
        )
        .all()
    )
    return [_template_response(row) for row in rows]


@router.post("/goods/types/{type_id}/attribute-templates")
def create_goods_type_attribute_template(
    type_id: str,
    body: GoodsTypeAttributeTemplateCreate,
    db: Session = DB_SESSION,
    admin: User = SUPER_ADMIN_USER,
):
    goods_type = db.query(GoodsType).filter(GoodsType.id == type_id).first()
    if not goods_type:
        raise HTTPException(status_code=404, detail="Goods type not found")
    key, allowed_values = _validate_template_values(
        body.key, body.field_type, body.allowed_values, body.is_variant_option
    )
    if (
        db.query(GoodsTypeAttributeTemplate)
        .filter(
            GoodsTypeAttributeTemplate.goods_type_id == goods_type.id,
            GoodsTypeAttributeTemplate.key == key,
        )
        .first()
    ):
        raise HTTPException(
            status_code=409, detail="This Goods Type already has that template key."
        )
    template = GoodsTypeAttributeTemplate(
        goods_type_id=goods_type.id,
        key=key,
        label=body.label.strip(),
        field_type=body.field_type,
        allowed_values=allowed_values,
        is_required=body.is_required,
        customer_visible=body.customer_visible,
        is_variant_option=body.is_variant_option,
        sort_order=body.sort_order,
    )
    db.add(template)
    db.commit()
    db.refresh(template)
    return _template_response(template)


@router.patch("/goods/types/{type_id}/attribute-templates/{template_id}")
def update_goods_type_attribute_template(
    type_id: str,
    template_id: str,
    body: GoodsTypeAttributeTemplateUpdate,
    db: Session = DB_SESSION,
    admin: User = SUPER_ADMIN_USER,
):
    template = (
        db.query(GoodsTypeAttributeTemplate)
        .filter(
            GoodsTypeAttributeTemplate.id == template_id,
            GoodsTypeAttributeTemplate.goods_type_id == type_id,
        )
        .first()
    )
    if not template:
        raise HTTPException(status_code=404, detail="Attribute template not found")
    updates = body.model_dump(exclude_unset=True)
    field_type = updates.get("field_type", template.field_type)
    values = updates.get("allowed_values", template.allowed_values or [])
    is_variant = updates.get("is_variant_option", template.is_variant_option)
    _, normalized_values = _validate_template_values(
        template.key, field_type, values, is_variant
    )
    for field, value in updates.items():
        setattr(
            template, field, normalized_values if field == "allowed_values" else value
        )
    db.commit()
    db.refresh(template)
    return _template_response(template)


@router.delete("/goods/types/{type_id}/attribute-templates/{template_id}")
def delete_goods_type_attribute_template(
    type_id: str,
    template_id: str,
    db: Session = DB_SESSION,
    admin: User = SUPER_ADMIN_USER,
):
    template = (
        db.query(GoodsTypeAttributeTemplate)
        .filter(
            GoodsTypeAttributeTemplate.id == template_id,
            GoodsTypeAttributeTemplate.goods_type_id == type_id,
        )
        .first()
    )
    if not template:
        raise HTTPException(status_code=404, detail="Attribute template not found")
    db.delete(template)
    db.commit()
    return {"message": "Attribute template deleted"}


@router.delete("/goods/categories/{category_id}")
def delete_goods_category(
    category_id: str,
    db: Session = DB_SESSION,
    admin: User = SUPER_ADMIN_USER,
):
    cat = db.query(GoodsCategory).filter(GoodsCategory.id == category_id).first()
    if not cat:
        raise HTTPException(status_code=404, detail="Category not found")

    # Prevent delete if goods types exist
    types_count = (
        db.query(GoodsType).filter(GoodsType.category_id == category_id).count()
    )
    if types_count > 0:
        raise HTTPException(
            status_code=400, detail="Cannot delete category with existing goods types"
        )

    db.delete(cat)
    db.commit()

    return {"message": "Category deleted"}


# ─── SeaBookings Oversight ──────────────────────────────


@router.get("/sea-bookings")
def list_all_sea_bookings(
    payment_status: Optional[str] = None,
    goods_status: Optional[str] = None,
    search: Optional[str] = None,
    page: int = 1,
    size: int = 20,
    db: Session = DB_SESSION,
    admin: User = SUPER_ADMIN_USER,
):
    """
    List all sea bookings across the platform for oversight.
    Super admins can monitor sea_booking patterns for fraud detection.
    """
    q = (
        db.query(
            SeaBooking,
            User.name.label("user_name"),
            Container.id.label("container_id"),
            Container.admin_id.label("container_admin_id"),
            Route.origin,
            Route.destination,
        )
        .join(User, SeaBooking.user_id == User.id, isouter=True)
        .join(Container, SeaBooking.container_id == Container.id)
        .join(Route, Container.route_id == Route.id, isouter=True)
    )

    if payment_status:
        q = q.filter(SeaBooking.payment_status == payment_status)
    if goods_status:
        q = q.filter(SeaBooking.goods_status == goods_status)
    if search:
        # Search in sea_booking ID or user name
        q = q.filter(
            SeaBooking.id.cast(String).ilike(f"%{search}%")
            | User.name.ilike(f"%{search}%")
        )

    total = q.count()

    sea_bookings = (
        q.order_by(SeaBooking.created_at.desc())
        .offset((page - 1) * size)
        .limit(size)
        .all()
    )

    return {
        "total": total,
        "page": page,
        "size": size,
        "data": [
            {
                "id": str(r.SeaBooking.id),
                "user_id": (
                    str(r.SeaBooking.user_id) if r.SeaBooking.user_id else None
                ),
                "user_name": r.user_name,
                "container_id": str(r.container_id),
                "container_admin_id": str(r.container_admin_id),
                "container_route": (
                    f"{r.origin} → {r.destination}"
                    if r.origin and r.destination
                    else "N/A"
                ),
                "cbm_booked": float(r.SeaBooking.cbm_booked),
                "logistics_charge": float(r.SeaBooking.logistics_charge),
                "payment_status": r.SeaBooking.payment_status,
                "goods_status": r.SeaBooking.goods_status,
                "created_at": r.SeaBooking.created_at.isoformat(),
            }
            for r in sea_bookings
        ],
    }


@router.get("/air-bookings")
def list_all_air_bookings(
    status: Optional[str] = None,
    operator_id: Optional[str] = None,
    search: Optional[str] = None,
    page: int = 1,
    size: int = 20,
    db: Session = DB_SESSION,
    admin: User = SUPER_ADMIN_USER,
):
    del admin
    q = db.query(ExpressAirCargoBooking).outerjoin(
        User, User.id == ExpressAirCargoBooking.customer_id
    )
    if status:
        q = q.filter(ExpressAirCargoBooking.status == status)
    if operator_id:
        q = q.filter(ExpressAirCargoBooking.cargo_admin_id == operator_id)
    if search:
        token = f"%{search.strip()}%"
        q = q.filter(
            cast(ExpressAirCargoBooking.id, String).ilike(token)
            | ExpressAirCargoBooking.tracking_number.ilike(token)
            | User.name.ilike(token)
            | User.email.ilike(token)
        )
    total = q.count()
    page_size = min(max(size, 1), 100)
    rows = (
        q.order_by(ExpressAirCargoBooking.created_at.desc())
        .offset((max(page, 1) - 1) * page_size)
        .limit(page_size)
        .all()
    )
    operator_ids = {row.cargo_admin_id for row in rows if row.cargo_admin_id}
    operators = {
        row.id: row.name
        for row in db.query(User).filter(User.id.in_(operator_ids or [None])).all()
    }
    customer_ids = {row.customer_id for row in rows if row.customer_id}
    customers = {
        row.id: row.name
        for row in db.query(User).filter(User.id.in_(customer_ids or [None])).all()
    }
    return {
        "total": total,
        "page": page,
        "size": page_size,
        "data": [
            {
                "id": str(row.id),
                "booking_type": "air",
                "operator_id": str(row.cargo_admin_id) if row.cargo_admin_id else None,
                "operator_name": operators.get(row.cargo_admin_id),
                "customer_id": str(row.customer_id) if row.customer_id else None,
                "customer_name": customers.get(row.customer_id),
                "status": row.status,
                "route": row.route_label,
                "service": row.service_label,
                "weight_kg": float(row.weight_kg or 0),
                "quoted_total": float(row.quoted_total or 0),
                "currency": row.rate_currency,
                "tracking_number": row.tracking_number,
                "created_at": row.created_at,
            }
            for row in rows
        ],
    }


@router.get("/fcl-requests")
def list_all_fcl_requests(
    status: Optional[str] = None,
    operator_id: Optional[str] = None,
    search: Optional[str] = None,
    page: int = 1,
    size: int = 20,
    db: Session = DB_SESSION,
    admin: User = SUPER_ADMIN_USER,
):
    del admin
    q = db.query(QuoteRequest).filter(QuoteRequest.request_type == "FCL")
    if status:
        q = q.filter(QuoteRequest.status == status)
    if operator_id:
        q = q.filter(QuoteRequest.assigned_cargo_admin_id == operator_id)
    if search:
        token = f"%{search.strip()}%"
        q = q.filter(
            QuoteRequest.company_name.ilike(token)
            | QuoteRequest.product.ilike(token)
            | QuoteRequest.destination.ilike(token)
            | QuoteRequest.email.ilike(token)
        )
    total = q.count()
    page_size = min(max(size, 1), 100)
    rows = (
        q.order_by(QuoteRequest.created_at.desc())
        .offset((max(page, 1) - 1) * page_size)
        .limit(page_size)
        .all()
    )
    operator_ids = {
        row.assigned_cargo_admin_id for row in rows if row.assigned_cargo_admin_id
    }
    operators = {
        row.id: row.name
        for row in db.query(User).filter(User.id.in_(operator_ids or [None])).all()
    }
    return {
        "total": total,
        "page": page,
        "size": page_size,
        "data": [
            {
                "id": str(row.id),
                "booking_type": "fcl",
                "operator_id": (
                    str(row.assigned_cargo_admin_id)
                    if row.assigned_cargo_admin_id
                    else None
                ),
                "operator_name": operators.get(row.assigned_cargo_admin_id),
                "customer_name": row.company_name,
                "customer_email": row.email,
                "status": row.status,
                "product": row.product,
                "destination": row.destination,
                "incoterm": row.incoterm,
                "created_at": row.created_at,
            }
            for row in rows
        ],
    }


# ─── Analytics & Oversight ───────────────────────────────


@router.get("/analytics/overview")
def platform_overview(db: Session = DB_SESSION, admin: User = SUPER_ADMIN_USER):
    """System-wide analytics: containers, users, revenue."""
    from app.models.container import Container, SeaBooking
    from app.models.sourcing import SourcingOrder

    total_users = db.query(User).count()
    total_containers = db.query(Container).count()
    total_sea_bookings = db.query(SeaBooking).count()

    # Pending approvals count (ONLY Cargo Admins and Sourcing Agents)
    pending_approvals = (
        db.query(User)
        .filter(
            User.status == "pending_approval",
            User.role.in_(["cargo_admin", "sourcing_agent"]),
        )
        .count()
    )

    # Active operators count (Cargo Admins and Sourcing Agents)
    active_operators = (
        db.query(User)
        .filter(
            User.status == "active", User.role.in_(["cargo_admin", "sourcing_agent"])
        )
        .count()
    )

    commission_setting = (
        db.query(CommissionSettings)
        .order_by(CommissionSettings.effective_from.desc())
        .first()
    )
    current_commission = (
        float(commission_setting.commission_percentage) if commission_setting else 1.0
    )

    total_commission = (
        db.query(func.sum(SourcingOrder.commission_amount))
        .filter(SourcingOrder.commission_status == "earned")
        .scalar()
        or 0
    )

    containers_by_status = (
        db.query(Container.status, func.count(Container.id))
        .group_by(Container.status)
        .all()
    )

    # Container breakdown by operator (cargo admins only)
    containers_by_operator = (
        db.query(
            User.id,
            User.name,
            User.phone_number,
            func.count(Container.id).label("container_count"),
        )
        .join(Container, User.id == Container.admin_id)
        .filter(User.role == "cargo_admin")
        .group_by(User.id, User.name, User.phone_number)
        .order_by(func.count(Container.id).desc())
        .all()
    )

    return {
        "total_users": total_users,
        "pending_approvals": pending_approvals,
        "active_operators": active_operators,
        "total_containers": total_containers,
        "total_sea_bookings": total_sea_bookings,
        "current_commission_rate": current_commission,
        "total_commission_earned": float(total_commission),
        "containers_by_status": {row[0]: row[1] for row in containers_by_status},
        "containers_by_operator": [
            {
                "operator_id": str(row[0]),
                "operator_name": row[1],
                "operator_phone": row[2],
                "container_count": row[3],
            }
            for row in containers_by_operator
        ],
    }


# ─── Audit Logs ───────────────────────────────────────────


@router.get("/audit-logs")
def get_audit_logs(
    page: int = 1,
    size: int = 50,
    action: Optional[str] = None,
    user_id: Optional[str] = None,
    entity_type: Optional[str] = None,
    entity_id: Optional[str] = None,
    db: Session = DB_SESSION,
    admin: User = SUPER_ADMIN_USER,
):
    q = db.query(AuditLog)
    if action:
        q = q.filter(AuditLog.action.ilike(f"%{action}%"))
    if user_id:
        q = q.filter(cast(AuditLog.user_id, String).ilike(f"%{user_id}%"))
    if entity_type:
        q = q.filter(AuditLog.entity_type == entity_type)
    if entity_id:
        q = q.filter(cast(AuditLog.entity_id, String).ilike(f"%{entity_id}%"))

    total = q.count()
    logs = (
        q.order_by(AuditLog.created_at.desc())
        .offset((page - 1) * size)
        .limit(size)
        .all()
    )

    return {
        "total": total,
        "page": page,
        "size": size,
        "data": [
            {
                "id": str(log.id),
                "action": log.action,
                "user_id": str(log.user_id) if log.user_id else None,
                "entity_type": log.entity_type,
                "entity_id": str(log.entity_id) if log.entity_id else None,
                "reason": log.reason,
                "extra_data": log.extra_data,
                "created_at": log.created_at,
            }
            for log in logs
        ],
    }


@router.get("/notifications")
def get_super_admin_notifications(
    db: Session = DB_SESSION,
    current_user: User = SUPER_ADMIN_USER,
):
    """Get all notifications for the super admin user."""
    notifications = (
        db.query(Notification)
        .filter(Notification.user_id == current_user.id)
        .order_by(Notification.created_at.desc())
        .limit(50)
        .all()
    )

    unread_count = (
        db.query(Notification)
        .filter(
            Notification.user_id == current_user.id, Notification.is_read.is_(False)
        )
        .count()
    )

    return {
        "notifications": [
            {
                "id": str(n.id),
                "type": n.type,
                "message": n.message,
                "is_read": n.is_read,
                "target_type": n.target_type,
                "target_id": str(n.target_id) if n.target_id else None,
                "created_at": n.created_at.isoformat(),
            }
            for n in notifications
        ],
        "unread_count": unread_count,
    }


# ─── Unified Operators Endpoint ─────────────────────────────────────────────


@router.get("/operators")
def list_all_operators(
    status: Optional[str] = None,
    role: Optional[Literal["cargo_admin", "sourcing_agent"]] = None,
    service: Optional[str] = None,
    country: Optional[str] = None,
    search: Optional[str] = None,
    page: int = 1,
    size: int = 20,
    db: Session = DB_SESSION,
    admin: User = SUPER_ADMIN_USER,
):
    """
    Paginated platform operator directory with operational and governance signals.
    """
    # Subquery for container count (for cargo admins)
    container_count_subq = (
        db.query(Container.admin_id, func.count(Container.id).label("container_count"))
        .group_by(Container.admin_id)
        .subquery()
    )

    warehouse_count_subq = (
        db.query(Warehouse.admin_id, func.count(Warehouse.id).label("warehouse_count"))
        .group_by(Warehouse.admin_id)
        .subquery()
    )

    sea_booking_subq = (
        db.query(
            Container.admin_id,
            func.count(SeaBooking.id).label("sea_booking_count"),
            func.coalesce(func.sum(SeaBooking.logistics_charge), 0).label(
                "sea_booking_value"
            ),
        )
        .join(SeaBooking, SeaBooking.container_id == Container.id)
        .group_by(Container.admin_id)
        .subquery()
    )

    air_booking_subq = (
        db.query(
            ExpressAirCargoBooking.cargo_admin_id,
            func.count(ExpressAirCargoBooking.id).label("air_booking_count"),
            func.coalesce(func.sum(ExpressAirCargoBooking.quoted_total), 0).label(
                "air_booking_value"
            ),
            func.sum(
                case((ExpressAirCargoBooking.status == "delivered", 1), else_=0)
            ).label("air_delivered_count"),
            func.sum(
                case((ExpressAirCargoBooking.status == "cancelled", 1), else_=0)
            ).label("air_cancelled_count"),
        )
        .group_by(ExpressAirCargoBooking.cargo_admin_id)
        .subquery()
    )

    open_case_subq = (
        db.query(
            OperatorGovernanceCase.operator_id,
            func.count(OperatorGovernanceCase.id).label("open_case_count"),
        )
        .filter(OperatorGovernanceCase.status.in_(["open", "investigating"]))
        .group_by(OperatorGovernanceCase.operator_id)
        .subquery()
    )

    # Subquery for sourcing batches count (for sourcing agents)
    batches_count_subq = (
        db.query(
            SourcingBatch.agent_id, func.count(SourcingBatch.id).label("batchesCreated")
        )
        .group_by(SourcingBatch.agent_id)
        .subquery()
    )

    # Subquery for sourcing orders count (for sourcing agents)
    # Count orders where the batch's agent is the user
    orders_count_subq = (
        db.query(
            SourcingBatch.agent_id,
            func.count(SourcingOrder.id).label("ordersCollected"),
        )
        .join(SourcingOrder, SourcingBatch.id == SourcingOrder.batch_id)
        .group_by(SourcingBatch.agent_id)
        .subquery()
    )

    # Query users who are either cargo_admin or sourcing_agent
    q = (
        db.query(
            User,
            container_count_subq.c.container_count,
            batches_count_subq.c.batchesCreated,
            orders_count_subq.c.ordersCollected,
            warehouse_count_subq.c.warehouse_count,
            sea_booking_subq.c.sea_booking_count,
            sea_booking_subq.c.sea_booking_value,
            air_booking_subq.c.air_booking_count,
            air_booking_subq.c.air_booking_value,
            air_booking_subq.c.air_delivered_count,
            air_booking_subq.c.air_cancelled_count,
            open_case_subq.c.open_case_count,
            CargoOperatorProfile,
        )
        .filter(User.role.in_(["cargo_admin", "sourcing_agent"]))
        .outerjoin(container_count_subq, User.id == container_count_subq.c.admin_id)
        .outerjoin(batches_count_subq, User.id == batches_count_subq.c.agent_id)
        .outerjoin(orders_count_subq, User.id == orders_count_subq.c.agent_id)
        .outerjoin(warehouse_count_subq, User.id == warehouse_count_subq.c.admin_id)
        .outerjoin(sea_booking_subq, User.id == sea_booking_subq.c.admin_id)
        .outerjoin(air_booking_subq, User.id == air_booking_subq.c.cargo_admin_id)
        .outerjoin(open_case_subq, User.id == open_case_subq.c.operator_id)
        .outerjoin(CargoOperatorProfile, User.id == CargoOperatorProfile.user_id)
    )

    if role:
        q = q.filter(User.role == role)
    if status:
        q = q.filter(User.status == status)
    if service:
        q = q.filter(CargoOperatorProfile.service_types.contains([service]))
    if country:
        q = q.filter(CargoOperatorProfile.destination_countries.contains([country]))
    if search:
        q = q.filter(
            User.name.ilike(f"%{search}%")
            | User.phone_number.ilike(f"%{search}%")
            | User.email.ilike(f"%{search}%")
            | CargoOperatorProfile.company_name.ilike(f"%{search}%")
            | CargoOperatorProfile.registration_number.ilike(f"%{search}%")
        )

    total = q.count()
    size = min(max(size, 1), 100)
    operators = (
        q.order_by(User.created_at.desc())
        .offset((max(page, 1) - 1) * size)
        .limit(size)
        .all()
    )

    return {
        "total": total,
        "page": page,
        "size": size,
        "data": [
            {
                "id": str(op.User.id),
                "phone_number": op.User.phone_number,
                "email": op.User.email,
                "name": op.User.name,
                "role": op.User.role,
                "status": op.User.status,
                "is_verified": op.User.is_verified,
                "created_at": op.User.created_at,
                "type": op.User.role,  # For frontend compatibility
                "container_count": int(op.container_count or 0),
                "warehouse_count": int(op.warehouse_count or 0),
                "sea_booking_count": int(op.sea_booking_count or 0),
                "air_booking_count": int(op.air_booking_count or 0),
                "booking_count": int(op.sea_booking_count or 0)
                + int(op.air_booking_count or 0),
                "booking_value": float(op.sea_booking_value or 0)
                + float(op.air_booking_value or 0),
                "air_delivered_count": int(op.air_delivered_count or 0),
                "air_cancelled_count": int(op.air_cancelled_count or 0),
                "open_case_count": int(op.open_case_count or 0),
                "batchesCreated": int(op.batchesCreated or 0),
                "ordersCollected": int(op.ordersCollected or 0),
                "profile": (
                    serialize_cargo_company_profile(op.CargoOperatorProfile)
                    if op.CargoOperatorProfile
                    else None
                ),
            }
            for op in operators
        ],
    }


def _cargo_operator_or_404(db: Session, user_id: str):
    row = (
        db.query(User, CargoOperatorProfile)
        .outerjoin(CargoOperatorProfile, CargoOperatorProfile.user_id == User.id)
        .filter(User.id == user_id, User.role == "cargo_admin")
        .first()
    )
    if not row:
        raise HTTPException(status_code=404, detail="Cargo company not found")
    if not row.CargoOperatorProfile:
        raise HTTPException(
            status_code=409,
            detail=(
                "Cargo company profile is missing. "
                "Ask the company to complete registration."
            ),
        )
    return row.User, row.CargoOperatorProfile


def _serialize_governance_case(row: OperatorGovernanceCase) -> dict:
    return {
        "id": str(row.id),
        "operator_id": str(row.operator_id),
        "category": row.category,
        "severity": row.severity,
        "status": row.status,
        "title": row.title,
        "description": row.description,
        "resolution": row.resolution,
        "created_by": str(row.created_by) if row.created_by else None,
        "resolved_by": str(row.resolved_by) if row.resolved_by else None,
        "resolved_at": row.resolved_at.isoformat() if row.resolved_at else None,
        "created_at": row.created_at.isoformat() if row.created_at else None,
        "updated_at": row.updated_at.isoformat() if row.updated_at else None,
    }


@router.get("/operators/{user_id}/overview")
def get_cargo_operator_overview(
    user_id: str,
    db: Session = DB_SESSION,
    admin: User = SUPER_ADMIN_USER,
):
    del admin
    user, profile = _cargo_operator_or_404(db, user_id)
    container_count = (
        db.query(func.count(Container.id))
        .filter(Container.admin_id == user.id)
        .scalar()
        or 0
    )
    active_container_count = (
        db.query(func.count(Container.id))
        .filter(
            Container.admin_id == user.id,
            Container.status.in_(["open", "nearly_full", "full", "in_transit"]),
        )
        .scalar()
        or 0
    )
    containers = (
        db.query(Container)
        .filter(Container.admin_id == user.id)
        .order_by(Container.created_at.desc())
        .limit(20)
        .all()
    )
    warehouse_count = (
        db.query(func.count(Warehouse.id))
        .filter(Warehouse.admin_id == user.id)
        .scalar()
        or 0
    )
    warehouses = (
        db.query(Warehouse)
        .filter(Warehouse.admin_id == user.id)
        .order_by(Warehouse.created_at.desc())
        .limit(20)
        .all()
    )
    active_air_rate_count = (
        db.query(func.count(AirCargoRate.id))
        .filter(
            AirCargoRate.cargo_admin_id == user.id,
            AirCargoRate.is_active.is_(True),
        )
        .scalar()
        or 0
    )
    air_rates = (
        db.query(AirCargoRate)
        .filter(AirCargoRate.cargo_admin_id == user.id)
        .order_by(AirCargoRate.created_at.desc())
        .limit(20)
        .all()
    )
    departure_count = (
        db.query(func.count(AirDepartureSchedule.id))
        .filter(AirDepartureSchedule.cargo_admin_id == user.id)
        .scalar()
        or 0
    )
    departures = (
        db.query(AirDepartureSchedule)
        .filter(AirDepartureSchedule.cargo_admin_id == user.id)
        .order_by(AirDepartureSchedule.departure_at.desc())
        .limit(20)
        .all()
    )
    sea_summary = (
        db.query(
            func.count(SeaBooking.id),
            func.coalesce(func.sum(SeaBooking.logistics_charge), 0),
        )
        .join(Container, SeaBooking.container_id == Container.id)
        .filter(Container.admin_id == user.id)
        .first()
    )
    air_summary = (
        db.query(
            func.count(ExpressAirCargoBooking.id),
            func.coalesce(func.sum(ExpressAirCargoBooking.quoted_total), 0),
            func.sum(case((ExpressAirCargoBooking.status == "delivered", 1), else_=0)),
            func.sum(case((ExpressAirCargoBooking.status == "cancelled", 1), else_=0)),
        )
        .filter(ExpressAirCargoBooking.cargo_admin_id == user.id)
        .first()
    )
    cases = (
        db.query(OperatorGovernanceCase)
        .filter(OperatorGovernanceCase.operator_id == user.id)
        .order_by(OperatorGovernanceCase.created_at.desc())
        .limit(50)
        .all()
    )
    open_case_count = (
        db.query(func.count(OperatorGovernanceCase.id))
        .filter(
            OperatorGovernanceCase.operator_id == user.id,
            OperatorGovernanceCase.status.in_(["open", "investigating"]),
        )
        .scalar()
        or 0
    )
    total_air = int(air_summary[0] or 0)
    delivered_air = int(air_summary[2] or 0)
    cancelled_air = int(air_summary[3] or 0)
    return {
        "user": {
            "id": str(user.id),
            "name": user.name,
            "email": user.email or user.secure_email,
            "phone_number": user.phone_number or user.secure_phone,
            "status": user.status,
            "is_verified": bool(user.is_verified),
            "created_at": user.created_at,
        },
        "profile": serialize_cargo_company_profile(profile),
        "metrics": {
            "containers": int(container_count),
            "active_containers": int(active_container_count),
            "warehouses": int(warehouse_count),
            "active_air_rates": int(active_air_rate_count),
            "departure_schedules": int(departure_count),
            "sea_bookings": int(sea_summary[0] or 0),
            "air_bookings": total_air,
            "delivered_air_bookings": delivered_air,
            "cancelled_air_bookings": cancelled_air,
            "air_delivery_rate": (
                round(delivered_air / max(total_air - cancelled_air, 1) * 100, 1)
                if total_air
                else 0
            ),
            "booking_value": float(sea_summary[1] or 0) + float(air_summary[1] or 0),
            "open_cases": int(open_case_count),
        },
        "assets": {
            "containers": [
                {
                    "id": str(item.id),
                    "status": item.status,
                    "max_cbm": float(item.max_cbm or 0),
                    "booked_cbm": float(item.booked_cbm or 0),
                    "departure_date": item.departure_date,
                }
                for item in containers
            ],
            "warehouses": [
                {
                    "id": str(item.id),
                    "name": item.name,
                    "city": item.city,
                    "country": item.country,
                    "warehouse_type": item.warehouse_type,
                }
                for item in warehouses
            ],
            "air_rates": [
                {
                    "id": str(item.id),
                    "route": item.route,
                    "shipping_method": item.shipping_method,
                    "price": float(item.price),
                    "currency": item.currency,
                    "is_active": item.is_active,
                }
                for item in air_rates
            ],
            "departures": [
                {
                    "id": str(item.id),
                    "route_label": item.route_label,
                    "departure_at": item.departure_at,
                    "status": item.status,
                    "capacity_kg": (
                        float(item.capacity_kg)
                        if item.capacity_kg is not None
                        else None
                    ),
                }
                for item in departures
            ],
        },
        "cases": [_serialize_governance_case(item) for item in cases],
    }


@router.patch("/operators/{user_id}/decision")
def decide_cargo_operator_application(
    user_id: str,
    body: CargoOperatorDecision,
    db: Session = DB_SESSION,
    admin: User = SUPER_ADMIN_USER,
):
    user, profile = _cargo_operator_or_404(db, user_id)
    reason = (body.reason or "").strip() or None
    if body.decision in {"reject", "suspend"} and not reason:
        raise HTTPException(
            status_code=422,
            detail="A reason is required when rejecting or suspending a company.",
        )

    old_status = profile.status
    if body.decision in {"approve", "reactivate"}:
        user.status = "active"
        sync_cargo_operator_profile_status(
            db, user=user, status="active", verified_by=admin.id
        )
    elif body.decision == "reject":
        user.status = "suspended"
        user.is_verified = False
        profile.status = "rejected"
        profile.is_verified = False
        profile.verified_at = None
        profile.verified_by = None
        profile.booking_paused = True
        profile.paused_at = datetime.utcnow()
        profile.paused_by = admin.id
    else:
        user.status = "suspended"
        user.is_verified = False
        profile.status = "inactive"
        profile.is_verified = False
        profile.verified_at = None
        profile.verified_by = None
        profile.booking_paused = True
        profile.paused_at = datetime.utcnow()
        profile.paused_by = admin.id
    profile.status_reason = reason
    create_notification(
        db=db,
        user_id=user.id,
        notification_type="cargo_operator_decision",
        message=f"Your cargo company account is now {profile.status}.",
        priority="info",
        target_type="cargo_operator_profile",
        target_id=profile.id,
    )
    log_action(
        db,
        "CARGO_COMPANY_DECISION",
        admin.id,
        "cargo_operator_profile",
        profile.id,
        {
            "decision": body.decision,
            "old_status": old_status,
            "new_status": profile.status,
            "reason": reason,
        },
    )
    db.commit()
    db.refresh(profile)
    return serialize_cargo_company_profile(profile)


@router.patch("/operators/{user_id}/profile")
def update_cargo_operator_profile(
    user_id: str,
    body: CargoOperatorProfileUpdate,
    db: Session = DB_SESSION,
    admin: User = SUPER_ADMIN_USER,
):
    user, profile = _cargo_operator_or_404(db, user_id)
    del user
    fields = body.model_dump(exclude_unset=True)
    for key in (
        "company_name",
        "registration_number",
        "website",
        "headquarters_country",
        "headquarters_city",
        "years_experience",
        "operations_summary",
    ):
        if key in fields and isinstance(fields[key], str):
            fields[key] = " ".join(fields[key].split()).strip() or None
    if fields.get("headquarters_country") not in (None, *AFRICAN_COUNTRIES):
        raise HTTPException(status_code=422, detail="Unsupported headquarters country")
    if "destination_countries" in fields:
        unknown = set(fields["destination_countries"] or []) - set(AFRICAN_COUNTRIES)
        if unknown:
            raise HTTPException(
                status_code=422, detail=f"Unsupported country: {sorted(unknown)[0]}"
            )
    if "service_types" in fields:
        unknown = set(fields["service_types"] or []) - set(SERVICE_TYPES)
        if unknown:
            raise HTTPException(
                status_code=422, detail=f"Unsupported service: {sorted(unknown)[0]}"
            )
    if "special_capabilities" in fields:
        unknown = set(fields["special_capabilities"] or []) - set(SPECIAL_CAPABILITIES)
        if unknown:
            raise HTTPException(
                status_code=422, detail=f"Unsupported capability: {sorted(unknown)[0]}"
            )
    if "preferred_currencies" in fields:
        currencies = [str(item).upper() for item in fields["preferred_currencies"]]
        unknown = set(currencies) - set(SUPPORTED_CURRENCIES)
        if unknown:
            raise HTTPException(
                status_code=422, detail=f"Unsupported currency: {sorted(unknown)[0]}"
            )
        fields["preferred_currencies"] = currencies
    for key, value in fields.items():
        setattr(profile, key, value)
    log_action(
        db,
        "CARGO_OPERATOR_PROFILE_UPDATED",
        admin.id,
        "cargo_operator_profile",
        profile.id,
        {"fields": sorted(fields)},
    )
    db.commit()
    db.refresh(profile)
    return serialize_cargo_company_profile(profile)


@router.patch("/operators/{user_id}/services")
def update_cargo_operator_service_controls(
    user_id: str,
    body: CargoOperatorServiceControlUpdate,
    db: Session = DB_SESSION,
    admin: User = SUPER_ADMIN_USER,
):
    user, profile = _cargo_operator_or_404(db, user_id)
    requested = set(profile.service_types or [])
    unknown = set(body.service_statuses) - requested
    if unknown:
        raise HTTPException(
            status_code=422,
            detail=f"Service was not requested by this company: {sorted(unknown)[0]}",
        )
    reason = (body.reason or "").strip() or None
    if (
        body.booking_paused
        or any(
            value in {"paused", "rejected"} for value in body.service_statuses.values()
        )
    ) and not reason:
        raise HTTPException(
            status_code=422,
            detail="A reason is required when pausing or rejecting a service.",
        )
    statuses = {
        service: body.service_statuses.get(service, "pending")
        for service in (profile.service_types or [])
    }
    profile.service_statuses = statuses
    profile.approved_service_types = [
        service
        for service, service_status in statuses.items()
        if service_status == "approved"
    ]
    profile.booking_paused = body.booking_paused
    profile.status_reason = reason
    profile.paused_at = datetime.utcnow() if body.booking_paused else None
    profile.paused_by = admin.id if body.booking_paused else None
    create_notification(
        db=db,
        user_id=user.id,
        notification_type="cargo_operator_service_controls",
        message="Your approved cargo services were updated by Sahajomy.",
        priority="info",
        target_type="cargo_operator_profile",
        target_id=profile.id,
    )
    log_action(
        db,
        "CARGO_COMPANY_SERVICES_UPDATED",
        admin.id,
        "cargo_operator_profile",
        profile.id,
        {
            "service_statuses": statuses,
            "booking_paused": body.booking_paused,
            "reason": reason,
        },
    )
    db.commit()
    db.refresh(profile)
    return serialize_cargo_company_profile(profile)


@router.post("/operators/{user_id}/cases", status_code=201)
def create_operator_governance_case(
    user_id: str,
    body: OperatorCaseCreate,
    db: Session = DB_SESSION,
    admin: User = SUPER_ADMIN_USER,
):
    user, profile = _cargo_operator_or_404(db, user_id)
    row = OperatorGovernanceCase(
        operator_id=user.id,
        category=body.category,
        severity=body.severity,
        title=body.title.strip(),
        description=body.description.strip(),
        created_by=admin.id,
    )
    db.add(row)
    db.flush()
    create_notification(
        db=db,
        user_id=user.id,
        notification_type="cargo_operator_governance_case",
        message=(
            f"Sahajomy opened a {body.category.replace('_', ' ')} "
            "review for your account."
        ),
        priority="warning" if body.severity in {"high", "critical"} else "info",
        target_type="operator_governance_case",
        target_id=row.id,
    )
    log_action(
        db,
        "GOVERNANCE_CASE_CREATED",
        admin.id,
        "operator_governance_case",
        row.id,
        {
            "operator_id": str(user.id),
            "category": row.category,
            "severity": row.severity,
        },
    )
    db.commit()
    db.refresh(row)
    return _serialize_governance_case(row)


@router.patch("/operators/{user_id}/cases/{case_id}")
def update_operator_governance_case(
    user_id: str,
    case_id: str,
    body: OperatorCaseUpdate,
    db: Session = DB_SESSION,
    admin: User = SUPER_ADMIN_USER,
):
    _cargo_operator_or_404(db, user_id)
    row = (
        db.query(OperatorGovernanceCase)
        .filter(
            OperatorGovernanceCase.id == case_id,
            OperatorGovernanceCase.operator_id == user_id,
        )
        .first()
    )
    if not row:
        raise HTTPException(status_code=404, detail="Governance case not found")
    if body.status in {"resolved", "dismissed"} and not (body.resolution or "").strip():
        raise HTTPException(
            status_code=422,
            detail="A resolution is required when closing a governance case.",
        )
    row.status = body.status
    row.resolution = (body.resolution or "").strip() or None
    row.resolved_at = (
        datetime.utcnow() if body.status in {"resolved", "dismissed"} else None
    )
    row.resolved_by = admin.id if body.status in {"resolved", "dismissed"} else None
    log_action(
        db,
        "GOVERNANCE_CASE_UPDATED",
        admin.id,
        "operator_governance_case",
        row.id,
        {"status": row.status},
    )
    db.commit()
    db.refresh(row)
    return _serialize_governance_case(row)
