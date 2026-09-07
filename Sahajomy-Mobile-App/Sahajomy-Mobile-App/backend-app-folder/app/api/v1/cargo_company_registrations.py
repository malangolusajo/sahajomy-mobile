"""Public cargo-company registration and capability metadata."""

import os
import tempfile
from datetime import datetime
from typing import List, Optional

from app.core.audit import log_action
from app.core.cloudinary import upload_to_cloudinary
from app.core.config import settings
from app.core.email_service import validate_email
from app.core.encryption import data_encryption
from app.core.upload_validation import validated_image_format
from app.core.validation import validate_and_format_phone
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
from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from pydantic import BaseModel, Field, field_validator
from sqlalchemy import or_
from sqlalchemy.orm import Session

router = APIRouter(tags=["Cargo Company Registration"])

AFRICAN_COUNTRIES = (
    "Algeria",
    "Angola",
    "Benin",
    "Botswana",
    "Burkina Faso",
    "Burundi",
    "Cabo Verde",
    "Cameroon",
    "Central African Republic",
    "Chad",
    "Comoros",
    "Congo",
    "Côte d’Ivoire",
    "Democratic Republic of the Congo",
    "Djibouti",
    "Egypt",
    "Equatorial Guinea",
    "Eritrea",
    "Eswatini",
    "Ethiopia",
    "Gabon",
    "Gambia",
    "Ghana",
    "Guinea",
    "Guinea-Bissau",
    "Kenya",
    "Lesotho",
    "Liberia",
    "Libya",
    "Madagascar",
    "Malawi",
    "Mali",
    "Mauritania",
    "Mauritius",
    "Morocco",
    "Mozambique",
    "Namibia",
    "Niger",
    "Nigeria",
    "Rwanda",
    "São Tomé and Príncipe",
    "Senegal",
    "Seychelles",
    "Sierra Leone",
    "Somalia",
    "South Africa",
    "South Sudan",
    "Sudan",
    "Tanzania",
    "Togo",
    "Tunisia",
    "Uganda",
    "Zambia",
    "Zimbabwe",
)

SERVICE_TYPES = {
    "shared_container": "Shared container / LCL (CBM)",
    "full_container": "Full container / FCL",
    "air_cargo": "Air cargo",
    "warehousing": "China warehousing",
    "customs_clearance": "Customs clearance",
    "last_mile_delivery": "Last-mile delivery",
    "cargo_consolidation": "Cargo consolidation",
    "documentation": "Shipping documentation",
}

SPECIAL_CAPABILITIES = {
    "dangerous_goods": "Dangerous goods",
    "temperature_controlled": "Temperature-controlled cargo",
    "oversized_cargo": "Oversized cargo",
    "fragile_cargo": "Fragile cargo",
    "ecommerce_fulfilment": "E-commerce fulfilment",
    "inspection": "Inspection and quality checks",
}

CHINA_ORIGIN_CITIES = (
    "Guangzhou",
    "Yiwu",
    "Shenzhen",
    "Foshan",
    "Shanghai",
    "Ningbo",
    "Qingdao",
    "Xiamen",
    "Keqiao",
    "Hangzhou",
    "Beijing",
    "Other",
)

SUPPORTED_CURRENCIES = ("USD", "RMB", "TZS")


def _clean_list(values: List[str], *, maximum: int = 54) -> list[str]:
    cleaned = []
    for value in values[:maximum]:
        item = " ".join(str(value or "").split()).strip()
        if item and item not in cleaned:
            cleaned.append(item)
    return cleaned


class CargoCompanyRegistrationRequest(BaseModel):
    contact_name: str = Field(..., min_length=2, max_length=150)
    company_name: str = Field(..., min_length=2, max_length=180)
    phone: str = Field(..., min_length=7, max_length=30)
    email: str = Field(..., min_length=5, max_length=255)
    registration_number: Optional[str] = Field(default=None, max_length=120)
    website: Optional[str] = Field(default=None, max_length=255)
    logo_url: Optional[str] = Field(default=None, max_length=500)
    headquarters_country: str = Field(..., min_length=2, max_length=100)
    headquarters_city: str = Field(..., min_length=2, max_length=120)
    china_origin_cities: List[str] = Field(..., min_length=1, max_length=20)
    destination_countries: List[str] = Field(..., min_length=1, max_length=54)
    service_types: List[str] = Field(..., min_length=1, max_length=8)
    special_capabilities: List[str] = Field(default_factory=list, max_length=6)
    preferred_currencies: List[str] = Field(
        default_factory=lambda: ["USD"], max_length=10
    )
    years_experience: Optional[str] = Field(default=None, max_length=30)
    operations_summary: Optional[str] = Field(default=None, max_length=1500)

    @field_validator(
        "contact_name", "company_name", "headquarters_country", "headquarters_city"
    )
    @classmethod
    def normalize_required_text(cls, value: str) -> str:
        return " ".join(value.split()).strip()


def serialize_cargo_company_profile(profile: CargoOperatorProfile) -> dict:
    return {
        "id": str(profile.id),
        "user_id": str(profile.user_id),
        "company_name": profile.company_name,
        "registration_number": profile.registration_number,
        "website": profile.website,
        "logo_url": profile.logo_url,
        "headquarters_country": profile.headquarters_country,
        "headquarters_city": profile.headquarters_city,
        "china_origin_cities": list(profile.china_origin_cities or []),
        "destination_countries": list(profile.destination_countries or []),
        "service_types": list(profile.service_types or []),
        "service_labels": [
            SERVICE_TYPES.get(item, item) for item in (profile.service_types or [])
        ],
        "special_capabilities": list(profile.special_capabilities or []),
        "special_capability_labels": [
            SPECIAL_CAPABILITIES.get(item, item)
            for item in (profile.special_capabilities or [])
        ],
        "preferred_currencies": list(profile.preferred_currencies or []),
        "years_experience": profile.years_experience,
        "operations_summary": profile.operations_summary,
        "approved_service_types": list(profile.approved_service_types or []),
        "service_statuses": dict(profile.service_statuses or {}),
        "compliance_status": profile.compliance_status,
        "compliance_documents": list(profile.compliance_documents or []),
        "compliance_expires_at": (
            profile.compliance_expires_at.isoformat()
            if profile.compliance_expires_at
            else None
        ),
        "status_reason": profile.status_reason,
        "booking_paused": bool(profile.booking_paused),
        "paused_at": profile.paused_at.isoformat() if profile.paused_at else None,
        "status": profile.status,
        "is_verified": bool(profile.is_verified),
        "verified_at": profile.verified_at.isoformat() if profile.verified_at else None,
        "created_at": profile.created_at.isoformat() if profile.created_at else None,
    }


def sync_cargo_operator_profile_status(
    db: Session, *, user: User, status: str, verified_by=None
) -> None:
    profile = (
        db.query(CargoOperatorProfile)
        .filter(CargoOperatorProfile.user_id == user.id)
        .first()
    )
    if not profile:
        return
    if status == "active":
        membership = (
            db.query(CargoCompanyMembership)
            .filter(CargoCompanyMembership.user_id == user.id)
            .first()
        )
        if not membership:
            company = CargoCompany(
                name=profile.company_name,
                logo_url=profile.logo_url,
                created_by_user_id=user.id,
                status="active",
            )
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
                created_by_user_id=user.id,
                joined_at=datetime.utcnow(),
            )
            db.add_all([company, owner_role, membership])
            db.flush()
            create_default_subscription(
                db,
                company.id,
                created_by_id=user.id,
                plan_code="starter",
            )
        profile.status = "verified"
        profile.is_verified = True
        profile.verified_at = datetime.utcnow()
        profile.verified_by = verified_by
        user.is_verified = True
        profile.status_reason = None
        if not profile.approved_service_types:
            profile.approved_service_types = list(profile.service_types or [])
        if not profile.service_statuses:
            profile.service_statuses = {
                item: "approved" for item in (profile.service_types or [])
            }
        profile.booking_paused = False
        profile.paused_at = None
        profile.paused_by = None
    elif status == "pending_approval":
        profile.status = "pending"
        profile.is_verified = False
        profile.verified_at = None
        profile.verified_by = None
        user.is_verified = False
    else:
        profile.status = "inactive"
        profile.is_verified = False
        profile.verified_at = None
        profile.verified_by = None
        user.is_verified = False


@router.get("/public/cargo-operators/options")
def cargo_operator_registration_options():
    return {
        "african_countries": list(AFRICAN_COUNTRIES),
        "china_origin_cities": list(CHINA_ORIGIN_CITIES),
        "service_types": [
            {"value": value, "label": label} for value, label in SERVICE_TYPES.items()
        ],
        "special_capabilities": [
            {"value": value, "label": label}
            for value, label in SPECIAL_CAPABILITIES.items()
        ],
        "currencies": list(SUPPORTED_CURRENCIES),
    }


@router.post("/public/cargo-operators/logo-upload")
async def upload_registration_company_logo(file: UploadFile = File(...)):
    """Upload a company logo while filling in the public registration form.

    Anonymous applicants cannot use the authenticated upload endpoint, so
    this public variant stores the logo under company_branding/pending and
    returns its URL for inclusion in the registration payload. It is
    rate-limited per IP in main.py just like the registration endpoint.
    """
    allowed_types = ["image/jpeg", "image/png", "image/webp"]
    if file.content_type not in allowed_types:
        raise HTTPException(
            status_code=400,
            detail="Invalid file type. Only JPEG, PNG, and WebP images are allowed.",
        )

    content = await file.read()
    if len(content) > 2 * 1024 * 1024:
        raise HTTPException(
            status_code=400,
            detail=f"File too large. Maximum file size is {settings.MAX_IMAGE_SIZE_MB}MB.",
        )
    _, file_extension = validated_image_format(content, file.content_type)

    with tempfile.NamedTemporaryFile(delete=False, suffix=f".{file_extension}") as tmp:
        tmp.write(content)
        tmp_path = tmp.name

    try:
        image_url = upload_to_cloudinary(
            file=tmp_path,
            folder="company_branding/pending",
            resource_type="image",
        )
        return {"url": image_url, "logo_url": image_url}
    finally:
        os.unlink(tmp_path)


@router.post("/public/cargo-operators/register", status_code=201)
def register_cargo_company(
    body: CargoCompanyRegistrationRequest,
    db: Session = Depends(get_db),
):
    valid_phone, formatted_phone = validate_and_format_phone(body.phone)
    if not valid_phone:
        raise HTTPException(status_code=400, detail="Invalid phone number format.")

    normalized_email = body.email.strip().lower()
    if not validate_email(normalized_email):
        raise HTTPException(status_code=400, detail="Invalid email format.")

    headquarters_country = " ".join(body.headquarters_country.split()).strip()
    destinations = _clean_list(body.destination_countries)
    if headquarters_country not in AFRICAN_COUNTRIES:
        raise HTTPException(
            status_code=400,
            detail="Headquarters country must be an African country listed by Sahajomy.",
        )
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
            status_code=400, detail=f"Unsupported service type: {unknown_services[0]}."
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

    origins = _clean_list(body.china_origin_cities, maximum=20)
    currencies = [
        item.upper() for item in _clean_list(body.preferred_currencies, maximum=10)
    ]
    currencies = [item for item in currencies if item in SUPPORTED_CURRENCIES] or [
        "USD"
    ]

    phone_hash = data_encryption.hash_phone(formatted_phone)
    email_hash = data_encryption.hash_email(normalized_email)
    existing_user = (
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
    if existing_user:
        raise HTTPException(
            status_code=409,
            detail="An account with this phone or email already exists. Sign in or contact support.",
        )

    website = (body.website or "").strip() or None
    if website and not website.lower().startswith(("https://", "http://")):
        raise HTTPException(
            status_code=400, detail="Website must start with https:// or http://."
        )

    user = User(
        name=body.contact_name,
        phone_number=formatted_phone,
        phone_encrypted=data_encryption.encrypt_phone(formatted_phone),
        phone_hash=phone_hash,
        email=normalized_email,
        email_encrypted=data_encryption.encrypt_email(normalized_email),
        email_hash=email_hash,
        auth_provider=AuthProvider.OTP,
        role="cargo_admin",
        status="pending_approval",
        is_verified=False,
        is_active=True,
    )
    db.add(user)
    db.flush()

    profile = CargoOperatorProfile(
        user_id=user.id,
        company_name=body.company_name,
        registration_number=(body.registration_number or "").strip() or None,
        website=website,
        logo_url=(body.logo_url or "").strip() or None,
        headquarters_country=headquarters_country,
        headquarters_city=body.headquarters_city,
        china_origin_cities=origins,
        destination_countries=destinations,
        service_types=services,
        special_capabilities=capabilities,
        preferred_currencies=currencies,
        years_experience=(body.years_experience or "").strip() or None,
        operations_summary=(body.operations_summary or "").strip() or None,
        status="pending",
        is_verified=False,
    )
    db.add(profile)
    db.flush()

    admins = (
        db.query(User).filter(User.role == "super_admin", User.status == "active").all()
    )
    for admin in admins:
        create_notification(
            db=db,
            user_id=admin.id,
            notification_type="cargo_operator_registration",
            message=f"New cargo company application from {profile.company_name}.",
            priority="info",
            target_type="user",
            target_id=user.id,
        )

    log_action(
        db=db,
        action="CARGO_COMPANY_REGISTRATION_SUBMITTED",
        user_id=None,
        entity_type="cargo_operator_profile",
        entity_id=profile.id,
        metadata={
            "company_name": profile.company_name,
            "headquarters_country": profile.headquarters_country,
            "destination_countries": destinations,
            "service_types": services,
            "email": data_encryption.mask_email(normalized_email),
            "phone": data_encryption.mask_phone(formatted_phone),
        },
    )
    db.commit()
    return {
        "id": str(profile.id),
        "user_id": str(user.id),
        "status": profile.status,
        "message": (
            "Your cargo company application has been submitted. "
            "Sahajomy will review your routes and services before activation."
        ),
    }
