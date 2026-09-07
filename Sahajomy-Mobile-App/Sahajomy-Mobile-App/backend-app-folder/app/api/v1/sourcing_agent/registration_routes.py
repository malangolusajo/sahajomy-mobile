"""Public sourcing-agent registration/search and super-admin management."""

from __future__ import annotations

import os
import re
import tempfile
from datetime import datetime
from typing import Optional

from app.core.audit import log_action
from app.core.cloudinary import upload_to_cloudinary
from app.core.dependencies import get_sourcing_agent, get_super_admin
from app.core.email_service import validate_email
from app.core.encryption import data_encryption
from app.core.reference_ids import build_display_reference
from app.core.upload_validation import validated_image_format
from app.core.validation import validate_and_format_phone
from app.database import get_db
from app.models.air_cargo import ExpressAirCargoBooking
from app.models.cargo_customs import ManualCargoIntake
from app.models.container import Container, SeaBooking
from app.models.shipment_orders import ShipmentOrder
from app.models.shipping_mark import ShippingMark
from app.models.sourcing_agent import SourcingAgent
from app.models.tracking import TrackingEvent
from app.models.user import User
from app.services.realtime_notifications import create_notification
from app.services.tracking import (
    TrackingService,
    resolve_current_location,
    resolve_logistics_stage,
)
from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile
from pydantic import BaseModel, Field
from sqlalchemy import String, cast, func, or_
from sqlalchemy.orm import Session

router = APIRouter(tags=["Sourcing Agents"])

ALLOWED_NICHES = {
    "electronics",
    "furniture",
    "clothes",
    "shoes",
    "machinery",
    "building materials",
    "beauty products",
    "general sourcing",
}

USERNAME_RE = re.compile(r"^[A-Za-z0-9._]{2,64}$")
DISPLAY_REFERENCE_RE = re.compile(r"^(SHP|SEA|AIR)-\d{4}-([A-F0-9]{8})$")
PUBLIC_HANDLE_RE = re.compile(r"^[a-z0-9][a-z0-9-]{2,59}$")


def ensure_sourcing_agent_profile(db: Session, user: User) -> bool:
    """Ensure a `sourcing_agents` registration row exists for this user.

    The super-admin "Sourcing Agents" section lists registrations, so users
    created or promoted to sourcing_agent without a row would never appear
    there. Self-registration already creates both rows; this helper covers
    admin-created and promoted accounts.

    Idempotent: links an existing orphaned registration (matched by phone or
    email) before creating anything new. Returns True when a row was created
    or linked.
    """
    profile = db.query(SourcingAgent).filter(SourcingAgent.user_id == user.id).first()
    if profile:
        return False

    # Link an orphaned registration matching this user's identifiers instead
    # of duplicating it (phone/email hashes are unique on this table).
    predicates = []
    if user.phone_hash:
        predicates.append(SourcingAgent.phone_hash == user.phone_hash)
    if user.email_hash:
        predicates.append(SourcingAgent.email_hash == user.email_hash)
    if user.phone_number:
        predicates.append(SourcingAgent.phone == user.phone_number)
    if user.email:
        predicates.append(SourcingAgent.email == user.email)

    if predicates:
        profile = (
            db.query(SourcingAgent)
            .filter(SourcingAgent.user_id.is_(None), or_(*predicates))
            .first()
        )
        if profile:
            profile.user_id = user.id
            return True

    db.add(
        SourcingAgent(
            user_id=user.id,
            full_name=user.name or "Unknown",
            phone_encrypted=user.phone_encrypted,
            phone_hash=user.phone_hash,
            email_encrypted=user.email_encrypted,
            email_hash=user.email_hash,
            phone=user.phone_number,
            email=user.email,
            niche="general sourcing",
            location="",
            status="pending",
            is_verified=False,
        )
    )
    return True


def _find_entity_by_display_reference(db: Session, token_upper: str):
    match = DISPLAY_REFERENCE_RE.fullmatch(token_upper)
    if not match:
        return None

    prefix, uuid8 = match.group(1), match.group(2)
    if prefix == "SHP":
        order = (
            db.query(ShipmentOrder)
            .filter(
                func.upper(
                    func.replace(cast(ShipmentOrder.id, String), "-", "")
                ).startswith(uuid8)
            )
            .first()
        )
        if order:
            return ("shipment_order", str(order.id), order)
    if prefix == "SEA":
        sea_booking = (
            db.query(SeaBooking)
            .filter(
                func.upper(
                    func.replace(cast(SeaBooking.id, String), "-", "")
                ).startswith(uuid8)
            )
            .first()
        )
        if sea_booking:
            return ("sea_booking", str(sea_booking.id), sea_booking)
    if prefix == "AIR":
        booking = (
            db.query(ExpressAirCargoBooking)
            .filter(
                func.upper(
                    func.replace(cast(ExpressAirCargoBooking.id, String), "-", "")
                ).startswith(uuid8)
            )
            .first()
        )
        if booking:
            return ("booking", str(booking.id), booking)

    return None


class SourcingAgentAdminUpdate(BaseModel):
    full_name: Optional[str] = Field(default=None, min_length=2, max_length=150)
    phone: Optional[str] = Field(default=None, min_length=7, max_length=30)
    email: Optional[str] = Field(default=None, min_length=5, max_length=255)
    whatsapp: Optional[str] = Field(default=None, max_length=30)
    instagram: Optional[str] = Field(default=None, max_length=255)
    tiktok: Optional[str] = Field(default=None, max_length=255)
    niche: Optional[str] = Field(default=None, max_length=100)
    location: Optional[str] = Field(default=None, max_length=120)
    bio: Optional[str] = None
    years_experience: Optional[str] = Field(default=None, max_length=30)
    status: Optional[str] = Field(
        default=None, pattern="^(pending|verified|rejected|inactive)$"
    )
    is_verified: Optional[bool] = None


class PublicSourcingAgentProfileUpdate(BaseModel):
    """Fields an agent can deliberately publish to their Agizisha storefront."""

    public_handle: Optional[str] = Field(default=None, max_length=60)
    is_public: Optional[bool] = None
    bio: Optional[str] = Field(default=None, max_length=1500)


def _normalize_public_handle(value: str) -> str:
    handle = value.strip().lower()
    if not PUBLIC_HANDLE_RE.fullmatch(handle):
        raise HTTPException(
            status_code=400,
            detail=(
                "Public handle must be 3-60 lowercase letters, numbers, or hyphens "
                "and must start with a letter or number."
            ),
        )
    return handle


def _public_profile_payload(profile: SourcingAgent) -> dict:
    """Private management response; never used by public Agizisha APIs."""
    return {
        "display_name": profile.full_name,
        "profile_photo": profile.profile_photo,
        "public_handle": profile.public_handle,
        "is_public": bool(profile.is_public),
        "bio": profile.bio,
        "is_verified": bool(profile.is_verified and profile.status == "verified"),
    }


def _normalize_niche(value: str) -> str:
    normalized = value.strip().lower()
    if normalized not in ALLOWED_NICHES:
        allowed = ", ".join(sorted(ALLOWED_NICHES))
        raise HTTPException(
            status_code=400, detail=f"Invalid niche. Allowed: {allowed}"
        )
    return normalized


def _normalize_social(value: Optional[str], platform: str) -> Optional[str]:
    if not value:
        return None
    raw = value.strip()
    if not raw:
        return None

    if raw.startswith("@"):
        raw = raw[1:]

    if raw.startswith("http://") or raw.startswith("https://"):
        lower_raw = raw.lower()
        domain_ok = False
        if platform == "instagram":
            domain_ok = "instagram.com/" in lower_raw
        elif platform == "tiktok":
            domain_ok = "tiktok.com/" in lower_raw
        if not domain_ok:
            raise HTTPException(status_code=400, detail=f"Invalid {platform} URL.")
        return raw

    if not USERNAME_RE.match(raw):
        raise HTTPException(
            status_code=400,
            detail=f"Invalid {platform} username format.",
        )
    return raw


def _validate_experience(value: Optional[str]) -> Optional[str]:
    if value is None:
        return None
    cleaned = value.strip()
    if not cleaned:
        return None
    if len(cleaned) > 30:
        raise HTTPException(status_code=400, detail="years_experience is too long.")
    return cleaned


def _normalize_optional_text(value: Optional[str], max_length: int) -> Optional[str]:
    if value is None:
        return None
    cleaned = value.strip()
    if not cleaned:
        return None
    if len(cleaned) > max_length:
        raise HTTPException(status_code=400, detail="Field value is too long.")
    return cleaned


def _normalize_optional_phone(value: Optional[str], field_name: str) -> Optional[str]:
    if value is None:
        return None
    cleaned = value.strip()
    if not cleaned:
        return None
    is_valid, formatted = validate_and_format_phone(cleaned)
    if not is_valid:
        raise HTTPException(
            status_code=400, detail=f"Invalid {field_name} phone number format."
        )
    return formatted


def _parse_location_from_route_label(
    route_label: Optional[str],
) -> tuple[Optional[str], Optional[str]]:
    if not route_label:
        return None, None
    if "→" in route_label:
        origin, destination = route_label.split("→", 1)
        return origin.strip() or None, destination.strip() or None
    if "->" in route_label:
        origin, destination = route_label.split("->", 1)
        return origin.strip() or None, destination.strip() or None
    return None, None


def _container_route_locations(
    container: Container,
) -> tuple[Optional[str], Optional[str]]:
    """Resolve display locations without losing route-only container data."""
    origin_warehouse = container.origin_warehouse
    destination_warehouse = container.destination_warehouse
    origin = (
        (origin_warehouse.city or origin_warehouse.location or origin_warehouse.name)
        if origin_warehouse
        else None
    ) or (container.route.origin if container.route else None)
    destination = (
        (
            destination_warehouse.city
            or destination_warehouse.location
            or destination_warehouse.name
        )
        if destination_warehouse
        else None
    ) or (container.route.destination if container.route else None)
    return origin, destination


def _event_status_label(event: TrackingEvent) -> str:
    stage = resolve_logistics_stage(event.event_type, event.extra_data) or {}
    if stage.get("stage_label"):
        return str(stage["stage_label"])
    if event.extra_data and event.extra_data.get("new_status"):
        return str(event.extra_data["new_status"]).replace("_", " ").title()
    return event.event_type.replace("_", " ").title()


def _timeline_from_events(
    events: list[TrackingEvent],
    *,
    origin: Optional[str] = None,
    destination: Optional[str] = None,
) -> list[dict[str, Optional[str]]]:
    events = sorted(events, key=lambda event: event.timestamp)
    timeline = []
    for event in events:
        extra_data = event.extra_data or {}
        timeline.append(
            {
                "status": _event_status_label(event),
                "description": event.description or "",
                "location": resolve_current_location(
                    [event], origin=origin, destination=destination
                ),
                "updated_at": event.timestamp.isoformat() if event.timestamp else None,
            }
        )
    return timeline


def _timeline_for_entity(
    db: Session,
    entity_type: str,
    entity_id: str,
    *,
    origin: Optional[str] = None,
    destination: Optional[str] = None,
) -> list[dict[str, Optional[str]]]:
    return _timeline_from_events(
        TrackingService.get_entity_timeline(db, entity_type, entity_id),
        origin=origin,
        destination=destination,
    )


@router.post("/public/sourcing-agents/register")
async def register_sourcing_agent(
    full_name: str = Form(...),
    phone: str = Form(...),
    email: str = Form(...),
    whatsapp: Optional[str] = Form(None),
    instagram: Optional[str] = Form(None),
    tiktok: Optional[str] = Form(None),
    niche: str = Form(...),
    location: str = Form(...),
    bio: Optional[str] = Form(None),
    years_experience: Optional[str] = Form(None),
    profile_photo: Optional[UploadFile] = File(None),
    db: Session = Depends(get_db),
):
    normalized_name = full_name.strip()
    if len(normalized_name) < 2:
        raise HTTPException(status_code=400, detail="Full name is required.")

    is_valid_phone, formatted_phone = validate_and_format_phone(phone)
    if not is_valid_phone:
        raise HTTPException(status_code=400, detail="Invalid phone number format.")

    normalized_email = email.strip().lower()
    if not validate_email(normalized_email):
        raise HTTPException(status_code=400, detail="Invalid email format.")

    normalized_niche = _normalize_niche(niche)
    normalized_location = _normalize_optional_text(location, 120)
    if not normalized_location:
        raise HTTPException(status_code=400, detail="Location is required.")

    normalized_whatsapp = _normalize_optional_phone(whatsapp, "WhatsApp")
    normalized_instagram = _normalize_social(instagram, "instagram")
    normalized_tiktok = _normalize_social(tiktok, "tiktok")
    normalized_experience = _validate_experience(years_experience)
    normalized_bio = _normalize_optional_text(bio, 1000)
    phone_hash = data_encryption.hash_phone(formatted_phone)
    email_hash = data_encryption.hash_email(normalized_email)

    existing_registration = (
        db.query(SourcingAgent)
        .filter(
            or_(
                SourcingAgent.phone_hash == phone_hash,
                SourcingAgent.email_hash == email_hash,
                SourcingAgent.phone == formatted_phone,
                SourcingAgent.email == normalized_email,
            )
        )
        .first()
    )
    if existing_registration:
        raise HTTPException(
            status_code=400,
            detail=(
                "A sourcing-agent registration with this phone or email "
                "already exists."
            ),
        )

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
            status_code=400,
            detail="An account with this phone or email already exists.",
        )

    profile_photo_url = None
    if profile_photo and profile_photo.filename:
        content_type = profile_photo.content_type or ""
        allowed_types = {"image/jpeg", "image/png", "image/webp", "image/gif"}
        if content_type not in allowed_types:
            raise HTTPException(status_code=400, detail="Invalid profile photo format.")

        content = await profile_photo.read()
        max_bytes = 5 * 1024 * 1024
        if len(content) > max_bytes:
            raise HTTPException(
                status_code=400, detail="Profile photo is too large (max 5MB)."
            )

        _, extension = validated_image_format(content, content_type, allow_gif=True)
        with tempfile.NamedTemporaryFile(
            delete=False, suffix=f".{extension}"
        ) as tmp_file:
            tmp_file.write(content)
            tmp_path = tmp_file.name

        try:
            profile_photo_url = upload_to_cloudinary(
                file=tmp_path,
                folder="sourcing_agents/profiles",
                resource_type="image",
                tags=["sourcing_agent_profile"],
            )
        finally:
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)

    new_user = User(
        name=normalized_name,
        phone_number=formatted_phone,
        phone_encrypted=data_encryption.encrypt_phone(formatted_phone),
        phone_hash=phone_hash,
        email=normalized_email,
        email_encrypted=data_encryption.encrypt_email(normalized_email),
        email_hash=email_hash,
        role="sourcing_agent",
        status="pending_approval",
        is_verified=False,
        is_active=True,
    )
    db.add(new_user)
    db.flush()

    registration = SourcingAgent(
        user_id=new_user.id,
        full_name=normalized_name,
        phone_encrypted=data_encryption.encrypt_phone(formatted_phone),
        phone_hash=phone_hash,
        email_encrypted=data_encryption.encrypt_email(normalized_email),
        email_hash=email_hash,
        phone=formatted_phone,
        email=normalized_email,
        whatsapp=normalized_whatsapp,
        instagram=normalized_instagram,
        tiktok=normalized_tiktok,
        niche=normalized_niche,
        location=normalized_location,
        bio=normalized_bio,
        years_experience=normalized_experience,
        profile_photo=profile_photo_url,
        status="pending",
        is_verified=False,
    )
    db.add(registration)
    db.flush()

    admins = (
        db.query(User).filter(User.role == "super_admin", User.status == "active").all()
    )
    for admin in admins:
        create_notification(
            db=db,
            user_id=admin.id,
            notification_type="sourcing_agent_registration",
            message=(
                f"New sourcing agent registration submitted by {normalized_name}."
            ),
            priority="info",
            target_type="sourcing_agent",
            target_id=registration.id,
        )

    log_action(
        db=db,
        action="SOURCING_AGENT_REGISTRATION_SUBMITTED",
        user_id=None,
        entity_type="sourcing_agent",
        entity_id=registration.id,
        metadata={
            "name": normalized_name,
            "email": data_encryption.mask_email(normalized_email),
            "phone": data_encryption.mask_phone(formatted_phone),
            "niche": normalized_niche,
            "location": normalized_location,
        },
    )

    db.commit()
    return {
        "id": str(registration.id),
        "status": registration.status,
        "message": (
            "Your sourcing agent registration has been submitted. "
            "Our team will review and verify your account."
        ),
    }


@router.get("/sourcing_agent/public-profile")
def get_my_public_sourcing_agent_profile(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_sourcing_agent),
):
    profile = (
        db.query(SourcingAgent).filter(SourcingAgent.user_id == current_user.id).first()
    )
    if not profile:
        raise HTTPException(
            status_code=404,
            detail="Your sourcing-agent registration profile was not found.",
        )
    return _public_profile_payload(profile)


@router.patch("/sourcing_agent/public-profile")
def update_my_public_sourcing_agent_profile(
    payload: PublicSourcingAgentProfileUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_sourcing_agent),
):
    """Let a verified agent opt in to a safe, public Agizisha storefront."""
    profile = (
        db.query(SourcingAgent).filter(SourcingAgent.user_id == current_user.id).first()
    )
    if not profile:
        raise HTTPException(
            status_code=404,
            detail="Your sourcing-agent registration profile was not found.",
        )

    if payload.public_handle is not None:
        handle = _normalize_public_handle(payload.public_handle)
        existing = (
            db.query(SourcingAgent)
            .filter(
                SourcingAgent.public_handle == handle,
                SourcingAgent.id != profile.id,
            )
            .first()
        )
        if existing:
            raise HTTPException(
                status_code=409, detail="That public handle is already in use."
            )
        profile.public_handle = handle

    if payload.bio is not None:
        profile.bio = payload.bio.strip() or None

    if payload.is_public is not None:
        if payload.is_public:
            if profile.status != "verified" or not profile.is_verified:
                raise HTTPException(
                    status_code=403,
                    detail="Only verified sourcing agents can publish an Agizisha storefront.",
                )
            if not profile.public_handle:
                raise HTTPException(
                    status_code=422,
                    detail="Choose a public handle before publishing your storefront.",
                )
        profile.is_public = payload.is_public

    db.commit()
    db.refresh(profile)
    return _public_profile_payload(profile)


@router.get("/public/sourcing-agents/search")
def search_verified_sourcing_agents(
    q: Optional[str] = Query(default=None),
    niche: Optional[str] = Query(default=None),
    location: Optional[str] = Query(default=None),
    page: int = Query(default=1, ge=1),
    size: int = Query(default=10, ge=1, le=20),
    db: Session = Depends(get_db),
):
    search_q = (q or "").strip()
    search_niche = (niche or "").strip()
    search_location = (location or "").strip()

    # Search-first behavior for scale:
    # do not return broad listings unless a meaningful filter is provided.
    if not search_q and not search_niche and not search_location:
        return {"total": 0, "page": page, "size": size, "data": []}
    if search_q and len(search_q) < 2:
        raise HTTPException(
            status_code=400,
            detail="Search query must be at least 2 characters.",
        )

    query = db.query(SourcingAgent).filter(
        SourcingAgent.status == "verified",
        SourcingAgent.is_verified.is_(True),
    )

    if search_q:
        token = search_q
        query = query.filter(
            or_(
                SourcingAgent.full_name.ilike(f"%{token}%"),
                SourcingAgent.niche.ilike(f"%{token}%"),
                SourcingAgent.location.ilike(f"%{token}%"),
                SourcingAgent.instagram.ilike(f"%{token}%"),
                SourcingAgent.tiktok.ilike(f"%{token}%"),
            )
        )
    if search_niche:
        query = query.filter(SourcingAgent.niche.ilike(f"%{search_niche}%"))
    if search_location:
        query = query.filter(SourcingAgent.location.ilike(f"%{search_location}%"))

    total = query.count()
    rows = (
        query.order_by(SourcingAgent.created_at.desc())
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
                "id": str(agent.id),
                "full_name": agent.full_name,
                "whatsapp": agent.whatsapp,
                "instagram": agent.instagram,
                "tiktok": agent.tiktok,
                "niche": agent.niche,
                "location": agent.location,
                "bio": agent.bio,
                "years_experience": agent.years_experience,
                "profile_photo": agent.profile_photo,
                "is_verified": bool(agent.is_verified),
            }
            for agent in rows
        ],
    }


@router.get("/public/tracking/search")
def search_tracking_number(
    tracking_number: str = Query(..., min_length=2, max_length=120),
    db: Session = Depends(get_db),
):
    token = tracking_number.strip()
    token_upper = token.upper()
    if not token:
        raise HTTPException(status_code=400, detail="Tracking number is required.")

    shipment_order = (
        db.query(ShipmentOrder)
        .filter(ShipmentOrder.tracking_number.ilike(token_upper))
        .first()
    )
    booking = None
    manual_intake = None
    entity_type = None
    entity_id = None
    current_status = None
    shipment_reference = None
    origin = None
    destination = None
    current_location = None

    if shipment_order:
        entity_type = "shipment_order"
        entity_id = str(shipment_order.id)
        current_status = (
            shipment_order.status.value
            if hasattr(shipment_order.status, "value")
            else str(shipment_order.status)
        )
        shipment_reference = build_display_reference(
            "shipment_order",
            shipment_order.id,
            shipment_order.created_at,
        )

        if shipment_order.sea_booking_id:
            sea_booking = (
                db.query(SeaBooking)
                .filter(SeaBooking.id == shipment_order.sea_booking_id)
                .first()
            )
            if sea_booking:
                container = (
                    db.query(Container)
                    .filter(Container.id == sea_booking.container_id)
                    .first()
                )
                if container:
                    origin, destination = _container_route_locations(container)
        elif shipment_order.air_booking_id:
            booking = (
                db.query(ExpressAirCargoBooking)
                .filter(ExpressAirCargoBooking.id == shipment_order.air_booking_id)
                .first()
            )
            if booking:
                origin, destination = _parse_location_from_route_label(
                    booking.route_label
                )
    else:
        booking = (
            db.query(ExpressAirCargoBooking)
            .filter(
                or_(
                    ExpressAirCargoBooking.tracking_number.ilike(token_upper),
                    ExpressAirCargoBooking.airway_bill_number.ilike(token_upper),
                )
            )
            .first()
        )
        if booking:
            entity_type = "booking"
            entity_id = str(booking.id)
            current_status = booking.status
            shipment_reference = build_display_reference(
                "booking", booking.id, booking.created_at
            )
            origin, destination = _parse_location_from_route_label(booking.route_label)

    if not entity_type or not entity_id:
        manual_intake = (
            db.query(ManualCargoIntake)
            .filter(ManualCargoIntake.tracking_number.ilike(token_upper))
            .first()
        )
        if manual_intake:
            entity_type = "manual_cargo_intake"
            entity_id = str(manual_intake.id)
            if manual_intake.collection_status == "collected":
                current_status = "completed"
            elif manual_intake.collection_status == "ready":
                current_status = "ready_for_pickup"
            else:
                current_status = manual_intake.status
            shipment_reference = manual_intake.tracking_number
            warehouse = manual_intake.warehouse
            if warehouse:
                origin = warehouse.name or warehouse.city or warehouse.country
            destination = (
                ", ".join(
                    value
                    for value in [
                        manual_intake.destination_city,
                        manual_intake.destination_country,
                    ]
                    if value
                )
                or None
            )

    if not entity_type or not entity_id:
        shipping_mark = (
            db.query(ShippingMark)
            .filter(ShippingMark.shipping_mark_code.ilike(token_upper))
            .first()
        )
        if shipping_mark and shipping_mark.sea_booking_id:
            entity_type = "sea_booking"
            entity_id = str(shipping_mark.sea_booking_id)
            current_status = "in_transit"
            shipment_reference = build_display_reference(
                "sea_booking",
                shipping_mark.sea_booking_id,
                shipping_mark.created_at,
            )
            destination = shipping_mark.destination_region
        elif shipping_mark and shipping_mark.air_booking_id:
            entity_type = "booking"
            entity_id = str(shipping_mark.air_booking_id)
            current_status = "in_transit"
            shipment_reference = build_display_reference(
                "booking", shipping_mark.air_booking_id, shipping_mark.created_at
            )
            destination = shipping_mark.destination_region

    if not entity_type or not entity_id:
        reference_match = _find_entity_by_display_reference(db, token_upper)
        if reference_match:
            entity_type, entity_id, entity_obj = reference_match
            if entity_type == "shipment_order":
                current_status = (
                    entity_obj.status.value
                    if hasattr(entity_obj.status, "value")
                    else str(entity_obj.status)
                )
                shipment_reference = build_display_reference(
                    "shipment_order",
                    entity_obj.id,
                    entity_obj.created_at,
                )
                if entity_obj.air_booking_id:
                    booking = (
                        db.query(ExpressAirCargoBooking)
                        .filter(ExpressAirCargoBooking.id == entity_obj.air_booking_id)
                        .first()
                    )
                    if booking:
                        origin, destination = _parse_location_from_route_label(
                            booking.route_label
                        )
                elif entity_obj.sea_booking_id:
                    sea_booking = (
                        db.query(SeaBooking)
                        .filter(SeaBooking.id == entity_obj.sea_booking_id)
                        .first()
                    )
                    if sea_booking:
                        container = (
                            db.query(Container)
                            .filter(Container.id == sea_booking.container_id)
                            .first()
                        )
                        if container:
                            origin, destination = _container_route_locations(container)
            elif entity_type == "sea_booking":
                current_status = getattr(entity_obj, "goods_status", "in_transit")
                shipment_reference = build_display_reference(
                    "sea_booking", entity_obj.id, entity_obj.created_at
                )
                container = (
                    db.query(Container)
                    .filter(Container.id == entity_obj.container_id)
                    .first()
                )
                if container:
                    origin, destination = _container_route_locations(container)
            elif entity_type == "booking":
                current_status = getattr(entity_obj, "status", "in_transit")
                shipment_reference = build_display_reference(
                    "booking", entity_obj.id, entity_obj.created_at
                )
                origin, destination = _parse_location_from_route_label(
                    entity_obj.route_label
                )

    if not entity_type or not entity_id:
        raise HTTPException(
            status_code=404,
            detail=(
                "No shipment found for this tracking number. "
                "Please check and try again."
            ),
        )

    timeline_events = TrackingService.get_entity_timeline(db, entity_type, entity_id)
    # A public tracking number normally belongs to the unified shipment order,
    # while movement is recorded against its booking or sea_booking. Include
    # that linked operational timeline so public tracking follows the actual
    # origin-to-destination journey instead of only showing order setup events.
    if entity_type == "shipment_order":
        linked_order = (
            shipment_order
            or db.query(ShipmentOrder).filter(ShipmentOrder.id == entity_id).first()
        )
        if linked_order and linked_order.sea_booking_id:
            timeline_events.extend(
                TrackingService.get_entity_timeline(
                    db, "sea_booking", str(linked_order.sea_booking_id)
                )
            )
        elif linked_order and linked_order.air_booking_id:
            timeline_events.extend(
                TrackingService.get_entity_timeline(
                    db, "booking", str(linked_order.air_booking_id)
                )
            )

    timeline = _timeline_from_events(
        timeline_events,
        origin=origin,
        destination=destination,
    )
    last_update = timeline[-1]["updated_at"] if timeline else None
    current_location = resolve_current_location(
        timeline_events,
        origin=origin,
        destination=destination,
    )

    return {
        "tracking_number": token_upper,
        "entity_type": entity_type,
        "current_status": current_status,
        "shipment_reference": shipment_reference,
        "origin": origin,
        "destination": destination,
        "current_location": current_location,
        "last_update": last_update,
        "timeline": timeline,
    }


@router.get("/public/tracking/{tracking_number}")
def get_public_tracking_by_path(
    tracking_number: str,
    db: Session = Depends(get_db),
):
    return search_tracking_number(tracking_number=tracking_number, db=db)


@router.get("/super_admin/sourcing-agents")
def list_sourcing_agent_registrations(
    status: Optional[str] = Query(default=None),
    niche: Optional[str] = Query(default=None),
    search: Optional[str] = Query(default=None),
    page: int = Query(default=1, ge=1),
    size: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
    admin: User = Depends(get_super_admin),
):
    # Self-heal: every user carrying the sourcing_agent role must have a
    # registration row (covers admin-created, promoted, and legacy accounts).
    backfilled = False
    for agent_user in db.query(User).filter(User.role == "sourcing_agent").all():
        if ensure_sourcing_agent_profile(db, agent_user):
            backfilled = True
    if backfilled:
        db.commit()

    query = db.query(SourcingAgent)
    if status:
        query = query.filter(SourcingAgent.status == status)
    if niche:
        query = query.filter(SourcingAgent.niche.ilike(f"%{niche.strip()}%"))
    if search:
        token = search.strip()
        search_predicates = [
            SourcingAgent.full_name.ilike(f"%{token}%"),
            SourcingAgent.instagram.ilike(f"%{token}%"),
            SourcingAgent.tiktok.ilike(f"%{token}%"),
            SourcingAgent.niche.ilike(f"%{token}%"),
            SourcingAgent.phone.ilike(f"%{token}%"),
            SourcingAgent.email.ilike(f"%{token}%"),
        ]
        maybe_email = token.lower()
        if validate_email(maybe_email):
            search_predicates.append(
                SourcingAgent.email_hash == data_encryption.hash_email(maybe_email)
            )
        is_valid_phone, formatted_phone = validate_and_format_phone(token)
        if is_valid_phone:
            search_predicates.append(
                SourcingAgent.phone_hash == data_encryption.hash_phone(formatted_phone)
            )
        query = query.filter(or_(*search_predicates))

    total = query.count()
    rows = (
        query.order_by(SourcingAgent.created_at.desc())
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
                "id": str(agent.id),
                "user_id": str(agent.user_id) if agent.user_id else None,
                "full_name": agent.full_name,
                "phone": agent.secure_phone,
                "email": agent.secure_email,
                "whatsapp": agent.whatsapp,
                "instagram": agent.instagram,
                "tiktok": agent.tiktok,
                "niche": agent.niche,
                "location": agent.location,
                "bio": agent.bio,
                "years_experience": agent.years_experience,
                "profile_photo": agent.profile_photo,
                "status": agent.status,
                "is_verified": bool(agent.is_verified),
                "verified_at": (
                    agent.verified_at.isoformat() if agent.verified_at else None
                ),
                "verified_by": str(agent.verified_by) if agent.verified_by else None,
                "created_at": (
                    agent.created_at.isoformat() if agent.created_at else None
                ),
            }
            for agent in rows
        ],
    }


@router.patch("/super_admin/sourcing-agents/{agent_id}")
def update_sourcing_agent_registration(
    agent_id: str,
    body: SourcingAgentAdminUpdate,
    db: Session = Depends(get_db),
    admin: User = Depends(get_super_admin),
):
    agent = db.query(SourcingAgent).filter(SourcingAgent.id == agent_id).first()
    if not agent:
        raise HTTPException(status_code=404, detail="Sourcing agent not found.")

    linked_user = None
    if agent.user_id:
        linked_user = db.query(User).filter(User.id == agent.user_id).first()

    if body.full_name is not None:
        agent.full_name = body.full_name.strip()
        if linked_user:
            linked_user.name = agent.full_name

    if body.phone is not None:
        is_valid_phone, formatted_phone = validate_and_format_phone(body.phone)
        if not is_valid_phone:
            raise HTTPException(status_code=400, detail="Invalid phone number format.")
        phone_hash = data_encryption.hash_phone(formatted_phone)
        duplicate_phone = (
            db.query(SourcingAgent)
            .filter(
                or_(
                    SourcingAgent.phone_hash == phone_hash,
                    SourcingAgent.phone == formatted_phone,
                ),
                SourcingAgent.id != agent.id,
            )
            .first()
        )
        if duplicate_phone:
            raise HTTPException(status_code=400, detail="Phone number already in use.")
        agent.phone_encrypted = data_encryption.encrypt_phone(formatted_phone)
        agent.phone_hash = phone_hash
        agent.phone = formatted_phone
        if linked_user:
            linked_user.phone_number = formatted_phone
            linked_user.phone_encrypted = data_encryption.encrypt_phone(formatted_phone)
            linked_user.phone_hash = phone_hash

    if body.email is not None:
        normalized_email = body.email.strip().lower()
        if not validate_email(normalized_email):
            raise HTTPException(status_code=400, detail="Invalid email format.")
        email_hash = data_encryption.hash_email(normalized_email)
        duplicate_email = (
            db.query(SourcingAgent)
            .filter(
                or_(
                    SourcingAgent.email_hash == email_hash,
                    SourcingAgent.email == normalized_email,
                ),
                SourcingAgent.id != agent.id,
            )
            .first()
        )
        if duplicate_email:
            raise HTTPException(status_code=400, detail="Email already in use.")
        agent.email_encrypted = data_encryption.encrypt_email(normalized_email)
        agent.email_hash = email_hash
        agent.email = normalized_email
        if linked_user:
            linked_user.email = normalized_email
            linked_user.email_encrypted = data_encryption.encrypt_email(
                normalized_email
            )
            linked_user.email_hash = email_hash

    if body.whatsapp is not None:
        agent.whatsapp = _normalize_optional_phone(body.whatsapp, "WhatsApp")
    if body.instagram is not None:
        agent.instagram = _normalize_social(body.instagram, "instagram")
    if body.tiktok is not None:
        agent.tiktok = _normalize_social(body.tiktok, "tiktok")
    if body.niche is not None:
        agent.niche = _normalize_niche(body.niche)
    if body.location is not None:
        normalized_location = _normalize_optional_text(body.location, 120)
        if not normalized_location:
            raise HTTPException(status_code=400, detail="Location is required.")
        agent.location = normalized_location
    if body.bio is not None:
        agent.bio = _normalize_optional_text(body.bio, 1000)
    if body.years_experience is not None:
        agent.years_experience = _validate_experience(body.years_experience)

    desired_status = body.status or agent.status
    desired_verified = body.is_verified
    if desired_verified is None:
        desired_verified = desired_status == "verified"

    if desired_status == "verified":
        desired_verified = True
    elif desired_status in {"pending", "rejected", "inactive"}:
        desired_verified = False

    agent.status = desired_status
    agent.is_verified = bool(desired_verified)
    if agent.is_verified:
        agent.verified_at = datetime.utcnow()
        agent.verified_by = admin.id
    else:
        if desired_status != "verified":
            agent.verified_at = None
            agent.verified_by = None

    if linked_user:
        linked_user.role = "sourcing_agent"
        linked_user.is_verified = agent.is_verified
        if agent.status == "verified":
            linked_user.status = "active"
        elif agent.status == "pending":
            linked_user.status = "pending_approval"
        else:
            linked_user.status = "suspended"

    if agent.user_id:
        create_notification(
            db=db,
            user_id=agent.user_id,
            notification_type="sourcing_agent_verification",
            message=f"Your sourcing-agent profile status is now: {agent.status}.",
            priority="info",
            target_type="sourcing_agent",
            target_id=agent.id,
        )

    log_action(
        db=db,
        action="SOURCING_AGENT_REGISTRATION_UPDATED",
        user_id=admin.id,
        entity_type="sourcing_agent",
        entity_id=agent.id,
        metadata={
            "status": agent.status,
            "is_verified": agent.is_verified,
            "updated_by": str(admin.id),
        },
    )

    db.commit()
    db.refresh(agent)

    return {
        "id": str(agent.id),
        "status": agent.status,
        "is_verified": bool(agent.is_verified),
        "verified_at": agent.verified_at.isoformat() if agent.verified_at else None,
        "message": "Sourcing agent registration updated successfully.",
    }
