"""Resolve the business identity that must appear on generated artifacts."""

from typing import Any
from uuid import UUID

from app.models.cargo_company import CargoOperatorProfile
from app.models.container import Warehouse
from app.models.sourcing_agent import SourcingAgent
from app.models.user import User
from app.services.subscriptions import company_for_operator
from sqlalchemy.orm import Session


def _clean(value: Any) -> str | None:
    text = str(value or "").strip()
    return text or None


def operator_document_branding(db: Session, operator_id: UUID | None) -> dict:
    """Return cargo-company information without platform-owner branding."""
    if not operator_id:
        return {"name": "Cargo Company", "kind": "cargo_company"}

    company = company_for_operator(db, operator_id)
    owner_id = company.created_by_user_id if company else operator_id
    owner = db.query(User).filter(User.id == owner_id).first()
    profile = (
        db.query(CargoOperatorProfile)
        .filter(CargoOperatorProfile.user_id == owner_id)
        .first()
    )
    warehouse = (
        db.query(Warehouse)
        .filter(Warehouse.admin_id == owner_id)
        .order_by(Warehouse.created_at.asc())
        .first()
    )

    address = None
    city = profile.headquarters_city if profile else None
    country = profile.headquarters_country if profile else None
    if warehouse:
        address = warehouse.address or warehouse.location
        city = warehouse.city or city
        country = warehouse.country or country

    return {
        "id": str(company.id) if company else None,
        "name": _clean(company.name if company else None)
        or _clean(profile.company_name if profile else None)
        or _clean(owner.name if owner else None)
        or "Cargo Company",
        "kind": "cargo_company",
        "registration_number": _clean(profile.registration_number if profile else None),
        "phone": _clean(owner.secure_phone if owner else None),
        "email": _clean(owner.secure_email if owner else None),
        "website": _clean(profile.website if profile else None),
        "address": _clean(address),
        "city": _clean(city),
        "country": _clean(country),
    }


def sourcing_agent_document_branding(db: Session, user: User) -> dict:
    """Return the sourcing agent identity for agent-owned artifacts."""
    profile = db.query(SourcingAgent).filter(SourcingAgent.user_id == user.id).first()
    return {
        "id": str(user.id),
        "name": _clean(profile.full_name if profile else None)
        or _clean(user.name)
        or "Sourcing Agent",
        "kind": "sourcing_agent",
        "phone": _clean(
            (profile.whatsapp or profile.secure_phone) if profile else user.secure_phone
        ),
        "email": _clean(profile.secure_email if profile else user.secure_email),
        "address": _clean(profile.location if profile else None),
        "city": _clean(profile.location if profile else None),
        "country": None,
        "website": None,
        "registration_number": None,
        "profile_image_url": _clean(
            profile.profile_photo if profile else user.profile_image_url
        ),
    }
