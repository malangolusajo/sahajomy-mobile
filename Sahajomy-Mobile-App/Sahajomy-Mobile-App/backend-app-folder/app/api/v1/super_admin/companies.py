"""
Super Admin: cargo company lifecycle management.

A cargo company is the legal entity (workspace). Cargo admins are staff
users who belong to a company. Super admins register, review, suspend,
reject, reactivate, and soft-delete companies here.
"""

from datetime import datetime
from typing import List, Literal, Optional

from app.api.v1.cargo_company_registrations import (
    AFRICAN_COUNTRIES,
    CHINA_ORIGIN_CITIES,
    SERVICE_TYPES,
    SPECIAL_CAPABILITIES,
    SUPPORTED_CURRENCIES,
    _clean_list,
)
from app.core.audit import log_action
from app.core.dependencies import get_super_admin
from app.core.encryption import data_encryption
from app.core.validation import validate_and_format_phone, validate_email
from app.database import get_db
from app.models.cargo_company import CargoOperatorProfile
from app.models.cargo_workspace import (
    CargoCompany,
    CargoCompanyMembership,
    CargoPermission,
    CargoRole,
)
from app.models.user import AuthProvider, User
from app.services.realtime_notifications import create_notification
from app.services.subscriptions import create_default_subscription
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import or_
from sqlalchemy.orm import Session

router = APIRouter(prefix="/super_admin/companies", tags=["Super Admin Companies"])

DB_SESSION = Depends(get_db)
SUPER_ADMIN_USER = Depends(get_super_admin)

COMPANY_STATUSES = ("active", "pending_approval", "suspended", "rejected", "deleted")


class CompanyAdminCreate(BaseModel):
    """First admin account created together with a new company."""

    name: str = Field(..., min_length=2, max_length=150)
    phone: str = Field(..., min_length=7, max_length=30)
    email: str = Field(..., min_length=5, max_length=255)
    status: Literal["active", "pending_approval", "suspended"] = "active"


class CompanyCreate(BaseModel):
    company_name: str = Field(..., min_length=2, max_length=180)
    logo_url: Optional[str] = Field(default=None, max_length=500)
    registration_number: Optional[str] = Field(default=None, max_length=120)
    website: Optional[str] = Field(default=None, max_length=255)
    headquarters_country: Optional[str] = Field(default=None, max_length=100)
    headquarters_city: Optional[str] = Field(default=None, max_length=120)
    china_origin_cities: List[str] = Field(default_factory=list, max_length=20)
    destination_countries: List[str] = Field(default_factory=list, max_length=54)
    service_types: List[str] = Field(default_factory=list, max_length=8)
    special_capabilities: List[str] = Field(default_factory=list, max_length=6)
    preferred_currencies: List[str] = Field(
        default_factory=lambda: ["USD"], max_length=10
    )
    years_experience: Optional[str] = Field(default=None, max_length=30)
    operations_summary: Optional[str] = Field(default=None, max_length=1500)
    base_currency: str = Field(default="USD", min_length=3, max_length=3)
    status: Literal["active", "pending_approval"] = "active"
    first_admin: Optional[CompanyAdminCreate] = None


class CompanyUpdate(BaseModel):
    # Company-entity fields only. Registration details (registration number,
    # website, headquarters) live on the owner's operator profile and are
    # managed through the existing operator profile endpoints.
    company_name: Optional[str] = Field(default=None, min_length=2, max_length=180)
    logo_url: Optional[str] = Field(default=None, max_length=500)
    base_currency: Optional[str] = Field(default=None, min_length=3, max_length=3)


class CompanyDecision(BaseModel):
    decision: Literal["approve", "reject", "suspend", "reactivate"]
    reason: Optional[str] = Field(default=None, max_length=2000)


def _company_or_404(db: Session, company_id: str) -> CargoCompany:
    company = db.query(CargoCompany).filter(CargoCompany.id == company_id).first()
    if not company:
        raise HTTPException(status_code=404, detail="Cargo company not found.")
    return company


def serialize_cargo_company(company: CargoCompany) -> dict:
    return {
        "id": str(company.id),
        "name": company.name,
        "status": company.status,
        "logo_url": company.logo_url,
        "base_currency": company.base_currency,
        "created_by_user_id": (
            str(company.created_by_user_id) if company.created_by_user_id else None
        ),
        "created_at": company.created_at.isoformat() if company.created_at else None,
    }


def _active_members(db: Session, company_id) -> List[User]:
    return (
        db.query(User)
        .join(CargoCompanyMembership, CargoCompanyMembership.user_id == User.id)
        .filter(
            CargoCompanyMembership.company_id == company_id,
            CargoCompanyMembership.status == "active",
        )
        .all()
    )


def _sync_members_to_company_status(
    db: Session,
    company: CargoCompany,
    *,
    admin: User,
    reason: Optional[str],
) -> None:
    """Keep member accounts and operator profiles aligned with company status.

    Boundaries: company is the entity on top; its admins inherit the
    company's lifecycle state. Suspending/rejecting a company suspends its
    admins; reactivating restores the company owner to active.
    """
    members = _active_members(db, company.id)
    if company.status in ("suspended", "rejected", "deleted"):
        for member in members:
            member.status = "suspended"
            member.is_verified = False
            profile = (
                db.query(CargoOperatorProfile)
                .filter(CargoOperatorProfile.user_id == member.id)
                .first()
            )
            if profile:
                profile.status = (
                    "rejected" if company.status == "rejected" else "inactive"
                )
                profile.is_verified = False
                profile.verified_at = None
                profile.verified_by = None
                profile.booking_paused = True
                profile.paused_at = datetime.utcnow()
                profile.paused_by = admin.id
                profile.status_reason = reason
            create_notification(
                db=db,
                user_id=member.id,
                notification_type="cargo_operator_decision",
                message=(
                    f"Your cargo company ({company.name}) has been "
                    f"{company.status} by Sahajomy."
                ),
                priority="info",
                target_type="cargo_company",
                target_id=company.id,
            )
    else:  # active / pending_approval
        owner = (
            db.query(User).filter(User.id == company.created_by_user_id).first()
            if company.created_by_user_id
            else None
        )
        for member in members:
            if member.id == company.created_by_user_id:
                member.status = (
                    "active" if company.status == "active" else "pending_approval"
                )
                profile = (
                    db.query(CargoOperatorProfile)
                    .filter(CargoOperatorProfile.user_id == member.id)
                    .first()
                )
                if profile:
                    profile.status = (
                        "verified" if company.status == "active" else "pending"
                    )
                    profile.is_verified = company.status == "active"
                    profile.booking_paused = False
                    profile.paused_at = None
                    profile.paused_by = None
                    profile.status_reason = None
                    if company.status == "active":
                        profile.verified_at = datetime.utcnow()
                        profile.verified_by = admin.id
                        member.is_verified = True
            create_notification(
                db=db,
                user_id=member.id,
                notification_type="cargo_operator_decision",
                message=(
                    f"Your cargo company ({company.name}) is now "
                    f"{company.status.replace('_', ' ')} on Sahajomy."
                ),
                priority="info",
                target_type="cargo_company",
                target_id=company.id,
            )


@router.post("", status_code=201)
def register_cargo_company(
    body: CompanyCreate,
    db: Session = DB_SESSION,
    admin: User = SUPER_ADMIN_USER,
):
    """Register a new cargo company (optionally with its first admin)."""
    company_name = " ".join(body.company_name.split()).strip()
    if not company_name:
        raise HTTPException(status_code=400, detail="Company name is required.")

    base_currency = body.base_currency.strip().upper()
    if len(base_currency) != 3 or not base_currency.isalpha():
        raise HTTPException(
            status_code=400, detail="Base currency must be a 3-letter code."
        )

    website = (body.website or "").strip() or None
    if website and not website.lower().startswith(("https://", "http://")):
        raise HTTPException(
            status_code=400, detail="Website must start with https:// or http://."
        )

    headquarters_country = (body.headquarters_country or "").strip() or "Tanzania"
    if headquarters_country not in AFRICAN_COUNTRIES:
        raise HTTPException(
            status_code=400,
            detail="Headquarters country must be an African country listed by Sahajomy.",
        )
    origins = _clean_list(body.china_origin_cities, maximum=20)
    unknown_origins = [item for item in origins if item not in CHINA_ORIGIN_CITIES]
    if unknown_origins:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported China origin city: {unknown_origins[0]}.",
        )
    destinations = _clean_list(body.destination_countries)
    unknown_destinations = [
        item for item in destinations if item not in AFRICAN_COUNTRIES
    ]
    if unknown_destinations:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported destination country: {unknown_destinations[0]}.",
        )
    services = _clean_list(body.service_types, maximum=len(SERVICE_TYPES))
    unknown_services = [item for item in services if item not in SERVICE_TYPES]
    if unknown_services:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported service type: {unknown_services[0]}.",
        )
    capabilities = _clean_list(
        body.special_capabilities, maximum=len(SPECIAL_CAPABILITIES)
    )
    unknown_capabilities = [
        item for item in capabilities if item not in SPECIAL_CAPABILITIES
    ]
    if unknown_capabilities:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported special capability: {unknown_capabilities[0]}.",
        )
    currencies = [
        item.upper() for item in _clean_list(body.preferred_currencies, maximum=10)
    ]
    if any(item not in SUPPORTED_CURRENCIES for item in currencies):
        raise HTTPException(status_code=400, detail="Unsupported preferred currency.")
    currencies = currencies or [base_currency]

    first_admin = body.first_admin
    owner_user_id = None
    if first_admin:
        valid_phone, formatted_phone = validate_and_format_phone(first_admin.phone)
        if not valid_phone:
            raise HTTPException(status_code=400, detail="Invalid admin phone number.")
        normalized_email = first_admin.email.strip().lower()
        if not validate_email(normalized_email):
            raise HTTPException(status_code=400, detail="Invalid admin email format.")
        phone_hash = data_encryption.hash_phone(formatted_phone)
        email_hash = data_encryption.hash_email(normalized_email)
        existing = (
            db.query(User)
            .filter(
                or_(
                    User.phone_hash == phone_hash,
                    User.phone_number == formatted_phone,
                    User.email_hash == email_hash,
                    User.email == normalized_email,
                )
            )
            .first()
        )
        if existing:
            raise HTTPException(
                status_code=409,
                detail="An account with this phone or email already exists.",
            )

    company = CargoCompany(
        name=company_name,
        status=body.status,
        base_currency=base_currency,
        logo_url=(body.logo_url or "").strip() or None,
        created_by_user_id=None,
    )
    db.add(company)
    db.flush()

    if first_admin:
        admin_status = "active" if body.status == "active" else "pending_approval"
        user = User(
            name=first_admin.name.strip(),
            phone_number=formatted_phone,
            phone_encrypted=data_encryption.encrypt_phone(formatted_phone),
            phone_hash=phone_hash,
            email=normalized_email,
            email_encrypted=data_encryption.encrypt_email(normalized_email),
            email_hash=email_hash,
            auth_provider=AuthProvider.OTP,
            role="cargo_admin",
            status=admin_status,
            is_verified=body.status == "active",
            is_active=True,
        )
        db.add(user)
        db.flush()

        profile = CargoOperatorProfile(
            user_id=user.id,
            company_name=company_name,
            registration_number=(body.registration_number or "").strip() or None,
            website=website,
            logo_url=company.logo_url,
            headquarters_country=(headquarters_country),
            headquarters_city=(
                (body.headquarters_city or "").strip() or "Dar es Salaam"
            ),
            china_origin_cities=origins,
            destination_countries=destinations,
            service_types=services,
            special_capabilities=capabilities,
            preferred_currencies=currencies,
            years_experience=(body.years_experience or "").strip() or None,
            operations_summary=(body.operations_summary or "").strip() or None,
            approved_service_types=services if body.status == "active" else [],
            service_statuses=(
                {service: "approved" for service in services}
                if body.status == "active"
                else {}
            ),
            status="verified" if body.status == "active" else "pending",
            is_verified=body.status == "active",
            verified_at=datetime.utcnow() if body.status == "active" else None,
            verified_by=admin.id if body.status == "active" else None,
        )
        db.add(profile)

        owner_role = CargoRole(
            name="Cargo Company Owner",
            scope="company",
            is_system=True,
            company=company,
        )
        owner_role.permissions = db.query(CargoPermission).all()
        membership = CargoCompanyMembership(
            user_id=user.id,
            company=company,
            role=owner_role,
            status="active",
            created_by_user_id=admin.id,
            joined_at=datetime.utcnow(),
        )
        db.add_all([owner_role, membership])
        db.flush()

        company.created_by_user_id = user.id
        owner_user_id = user.id
        create_default_subscription(
            db, company.id, created_by_id=admin.id, plan_code="starter"
        )
        create_notification(
            db=db,
            user_id=user.id,
            notification_type="cargo_operator_registration",
            message=(
                f"Your cargo company ({company_name}) has been registered on "
                f"Sahajomy by the platform team."
            ),
            priority="info",
            target_type="cargo_company",
            target_id=company.id,
        )

    log_action(
        db=db,
        action="CARGO_COMPANY_REGISTERED",
        user_id=admin.id,
        entity_type="cargo_company",
        entity_id=company.id,
        metadata={
            "company_name": company_name,
            "status": body.status,
            "base_currency": base_currency,
            "first_admin_created": bool(first_admin),
            "owner_user_id": str(owner_user_id) if owner_user_id else None,
        },
    )
    db.commit()
    db.refresh(company)
    return {
        **serialize_cargo_company(company),
        "owner_user_id": str(owner_user_id) if owner_user_id else None,
        "message": f"Cargo company {company_name} registered successfully.",
    }


@router.get("")
def list_cargo_companies(
    status: Optional[str] = None,
    search: Optional[str] = None,
    page: int = 1,
    size: int = 20,
    db: Session = DB_SESSION,
    admin: User = SUPER_ADMIN_USER,
):
    del admin
    q = db.query(CargoCompany)
    if status:
        q = q.filter(CargoCompany.status == status)
    if search:
        pattern = f"%{search.strip()}%"
        q = q.filter(CargoCompany.name.ilike(pattern))
    total = q.count()
    size = min(max(size, 1), 100)
    companies = (
        q.order_by(CargoCompany.created_at.desc())
        .offset((max(page, 1) - 1) * size)
        .limit(size)
        .all()
    )
    data = []
    for company in companies:
        members = _active_members(db, company.id)
        owner = next((m for m in members if m.id == company.created_by_user_id), None)
        data.append(
            {
                **serialize_cargo_company(company),
                "admin_count": len(members),
                "owner": (
                    {
                        "id": str(owner.id),
                        "name": owner.name,
                        "email": owner.email or owner.secure_email,
                        "phone_number": owner.phone_number or owner.secure_phone,
                        "status": owner.status,
                    }
                    if owner
                    else None
                ),
            }
        )
    return {"total": total, "page": page, "size": size, "data": data}


@router.get("/{company_id}")
def get_cargo_company(
    company_id: str,
    db: Session = DB_SESSION,
    admin: User = SUPER_ADMIN_USER,
):
    del admin
    company = _company_or_404(db, company_id)
    memberships = (
        db.query(CargoCompanyMembership)
        .filter(
            CargoCompanyMembership.company_id == company.id,
            CargoCompanyMembership.status == "active",
        )
        .all()
    )
    admins = []
    for membership in memberships:
        member = db.query(User).filter(User.id == membership.user_id).first()
        profile = (
            db.query(CargoOperatorProfile)
            .filter(CargoOperatorProfile.user_id == membership.user_id)
            .first()
        )
        admins.append(
            {
                "id": str(member.id),
                "name": member.name,
                "email": member.email or member.secure_email,
                "phone_number": member.phone_number or member.secure_phone,
                "status": member.status,
                "is_verified": bool(member.is_verified),
                "role": membership.role.name if membership.role else None,
                "profile": (
                    {
                        "registration_number": profile.registration_number,
                        "website": profile.website,
                        "headquarters_country": profile.headquarters_country,
                        "headquarters_city": profile.headquarters_city,
                    }
                    if profile
                    else None
                ),
            }
        )
    return {**serialize_cargo_company(company), "admins": admins}


@router.patch("/{company_id}")
def update_cargo_company(
    company_id: str,
    body: CompanyUpdate,
    db: Session = DB_SESSION,
    admin: User = SUPER_ADMIN_USER,
):
    company = _company_or_404(db, company_id)
    fields = body.model_dump(exclude_unset=True)
    if "company_name" in fields:
        fields["company_name"] = " ".join(fields["company_name"].split()).strip()
        if not fields["company_name"]:
            raise HTTPException(status_code=400, detail="Company name is required.")
    if "base_currency" in fields:
        currency = fields["base_currency"].strip().upper()
        if len(currency) != 3 or not currency.isalpha():
            raise HTTPException(
                status_code=400, detail="Base currency must be a 3-letter code."
            )
        fields["base_currency"] = currency
    if "logo_url" in fields:
        fields["logo_url"] = (fields["logo_url"] or "").strip() or None

    # Map API field names to model column names. Only company-entity
    # columns are included; profile-only fields are excluded so no phantom
    # attributes are set on the company row.
    column_map = {
        "company_name": "name",
        "logo_url": "logo_url",
        "base_currency": "base_currency",
    }
    old_name = company.name
    for key, value in fields.items():
        if key in column_map:
            setattr(company, column_map[key], value)

    # Keep the owner's operator profile company name in sync (display-only;
    # the company entity remains the source of truth).
    if "company_name" in fields and company.created_by_user_id:
        profile = (
            db.query(CargoOperatorProfile)
            .filter(CargoOperatorProfile.user_id == company.created_by_user_id)
            .first()
        )
        if profile:
            profile.company_name = company.name
    if "logo_url" in fields and company.created_by_user_id:
        profile = (
            db.query(CargoOperatorProfile)
            .filter(CargoOperatorProfile.user_id == company.created_by_user_id)
            .first()
        )
        if profile:
            profile.logo_url = company.logo_url

    log_action(
        db=db,
        action="CARGO_COMPANY_UPDATED",
        user_id=admin.id,
        entity_type="cargo_company",
        entity_id=company.id,
        metadata={"old_name": old_name, "fields": list(fields.keys())},
    )
    db.commit()
    db.refresh(company)
    return serialize_cargo_company(company)


@router.patch("/{company_id}/decision")
def decide_cargo_company(
    company_id: str,
    body: CompanyDecision,
    db: Session = DB_SESSION,
    admin: User = SUPER_ADMIN_USER,
):
    company = _company_or_404(db, company_id)
    reason = (body.reason or "").strip() or None
    if body.decision in {"reject", "suspend"} and not reason:
        raise HTTPException(
            status_code=422,
            detail="A reason is required when rejecting or suspending a company.",
        )
    if company.status == "deleted":
        raise HTTPException(
            status_code=400, detail="A deleted company cannot be changed."
        )

    old_status = company.status
    if body.decision == "approve":
        company.status = "active"
    elif body.decision == "reactivate":
        company.status = "active"
    elif body.decision == "reject":
        company.status = "rejected"
    else:
        company.status = "suspended"

    _sync_members_to_company_status(db, company, admin=admin, reason=reason)
    log_action(
        db=db,
        action="CARGO_COMPANY_DECISION",
        user_id=admin.id,
        entity_type="cargo_company",
        entity_id=company.id,
        metadata={
            "decision": body.decision,
            "old_status": old_status,
            "new_status": company.status,
            "reason": reason,
        },
    )
    db.commit()
    db.refresh(company)
    return {**serialize_cargo_company(company), "message": f"Company {company.status}."}


@router.delete("/{company_id}")
def delete_cargo_company(
    company_id: str,
    db: Session = DB_SESSION,
    admin: User = SUPER_ADMIN_USER,
):
    """Soft-delete a company: keep records, suspend admins, disable access."""
    company = _company_or_404(db, company_id)
    if company.status == "deleted":
        raise HTTPException(status_code=400, detail="Company is already deleted.")

    company.status = "deleted"
    _sync_members_to_company_status(db, company, admin=admin, reason="Company deleted")
    memberships = (
        db.query(CargoCompanyMembership)
        .filter(
            CargoCompanyMembership.company_id == company.id,
            CargoCompanyMembership.status == "active",
        )
        .all()
    )
    for membership in memberships:
        membership.status = "disabled"
        membership.disabled_at = datetime.utcnow()

    log_action(
        db=db,
        action="CARGO_COMPANY_DELETED",
        user_id=admin.id,
        entity_type="cargo_company",
        entity_id=company.id,
        metadata={"company_name": company.name},
    )
    db.commit()
    return {"message": f"Cargo company {company.name} was deleted (soft)."}
