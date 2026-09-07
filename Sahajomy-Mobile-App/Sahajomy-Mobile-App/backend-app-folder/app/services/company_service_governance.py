"""Runtime enforcement for Super Admin cargo-company service controls."""

from app.models.cargo_company import CargoOperatorProfile
from fastapi import HTTPException
from sqlalchemy.orm import Session


def company_service_is_bookable(
    db: Session, *, operator_id, service_type: str
) -> bool:
    profile = (
        db.query(CargoOperatorProfile)
        .filter(CargoOperatorProfile.user_id == operator_id)
        .first()
    )
    # Legacy operators without an onboarding profile retain their existing
    # access until Super Admin creates/reviews a profile for them.
    if not profile:
        return True
    if profile.status != "verified" or profile.booking_paused:
        return False
    statuses = dict(profile.service_statuses or {})
    if statuses:
        return statuses.get(service_type) == "approved"
    approved = set(profile.approved_service_types or [])
    return (
        service_type in approved
        if approved
        else service_type in set(profile.service_types or [])
    )


def require_company_service_bookable(
    db: Session, *, operator_id, service_type: str
) -> None:
    if not company_service_is_bookable(
        db, operator_id=operator_id, service_type=service_type
    ):
        raise HTTPException(
            status_code=409,
            detail=(
                "This cargo company is not currently accepting bookings "
                "for the selected service."
            ),
        )
