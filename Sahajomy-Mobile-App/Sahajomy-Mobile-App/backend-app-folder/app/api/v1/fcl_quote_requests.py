"""Public FCL quote submission and cargo-admin management endpoints."""

import html
import logging
from typing import Literal, Optional
from uuid import UUID

from app.core.audit import log_action
from app.core.dependencies import require_roles
from app.core.email_service import send_email
from app.core.validation import validate_email
from app.database import get_db
from app.models.finance import AuditLog
from app.models.quote_request import QuoteRequest
from app.models.user import User
from app.services.company_service_governance import company_service_is_bookable
from app.services.realtime_notifications import create_notification
from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, field_validator
from sqlalchemy import or_
from sqlalchemy.orm import Session, joinedload

router = APIRouter(tags=["FCL Quote Requests"])
logger = logging.getLogger(__name__)

FCL_STATUSES = {"pending", "quotations_sent", "done", "complete"}


class FclQuoteRequestCreate(BaseModel):
    request_type: Literal["FCL"] = "FCL"
    product: str
    specifications: str
    supplier_status: Literal["has_supplier", "needs_sourcing"]
    incoterm: Literal["EXW", "FOB"]
    destination: str
    company_name: str
    business_license: str
    email: str
    whatsapp_number: str
    assigned_cargo_admin_id: Optional[UUID] = None

    @field_validator(
        "product",
        "specifications",
        "destination",
        "company_name",
        "business_license",
        "email",
        "whatsapp_number",
    )
    @classmethod
    def required_text(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("This field is required")
        return cleaned

    @field_validator("email")
    @classmethod
    def valid_contact_email(cls, value: str) -> str:
        if not validate_email(value):
            raise ValueError("Please provide a valid business email")
        return value.lower()


class FclQuoteStatusUpdate(BaseModel):
    status: Literal["pending", "quotations_sent", "done", "complete"]


def _serialize_request(request: QuoteRequest, include_contact: bool = False) -> dict:
    data = {
        "id": str(request.id),
        "request_type": request.request_type,
        "product": request.product,
        "specifications": request.specifications,
        "supplier_status": request.supplier_status,
        "incoterm": request.incoterm,
        "destination": request.destination,
        "company_name": request.company_name,
        "status": request.status,
        "assigned_role": request.assigned_role,
        "assigned_cargo_admin_id": (
            str(request.assigned_cargo_admin_id)
            if request.assigned_cargo_admin_id
            else None
        ),
        "created_at": request.created_at.isoformat() if request.created_at else None,
    }
    if include_contact:
        data.update(
            {
                "business_license": request.business_license,
                "email": request.email,
                "whatsapp_number": request.whatsapp_number,
                "customer": (
                    {"name": request.customer.name}
                    if request.customer and request.customer.name
                    else None
                ),
            }
        )
    return data


def _cargo_admin_email(cargo_admin: User) -> Optional[str]:
    """Use the encrypted email accessor when available, with legacy fallback."""
    if cargo_admin.email:
        return cargo_admin.email
    try:
        return cargo_admin.secure_email
    except Exception:
        return None


def _send_fcl_request_emails(
    cargo_admins: list[User], quote_request: QuoteRequest
) -> None:
    """Best-effort post-commit email alert for the cargo-admin queue."""
    request_url = "https://sahajomy.co.tz/cargo/fcl-requests"
    company = html.escape(quote_request.company_name)
    product = html.escape(quote_request.product)
    destination = html.escape(quote_request.destination)
    for cargo_admin in cargo_admins:
        recipient_email = _cargo_admin_email(cargo_admin)
        if not recipient_email:
            logger.warning(
                "FCL request email skipped: cargo admin %s has no email", cargo_admin.id
            )
            continue

        sent = send_email(
            recipient_email,
            cargo_admin.name or "Cargo Admin",
            "New FCL quote request awaiting review",
            f"""
            <p>Hello {html.escape(cargo_admin.name or 'Cargo Admin')},</p>
            <p>A new Full Container Loading quote request is ready for review.</p>
            <ul>
              <li><strong>Company:</strong> {company}</li>
              <li><strong>Product:</strong> {product}</li>
              <li><strong>Destination:</strong> {destination}</li>
              <li><strong>Shipping terms:</strong> {html.escape(quote_request.incoterm)}</li>
            </ul>
            <p><a href="{request_url}">Open FCL Requests</a> to review the full request.</p>
            """,
        )
        if not sent:
            logger.warning(
                "FCL request email could not be sent to cargo admin %s", cargo_admin.id
            )


def _active_cargo_admins(db: Session) -> list[User]:
    rows = (
        db.query(User)
        .filter(
            User.role == "cargo_admin",
            User.is_active.is_(True),
            User.status == "active",
        )
        .order_by(User.name.asc(), User.created_at.asc())
        .all()
    )
    return [
        row
        for row in rows
        if company_service_is_bookable(
            db, operator_id=row.id, service_type="full_container"
        )
    ]


@router.get("/public/fcl-quote-request/cargo-admins")
def list_public_fcl_cargo_admins(db: Session = Depends(get_db)):
    """Minimal public profile data for choosing an FCL cargo administrator."""
    return [
        {
            "id": str(cargo_admin.id),
            "name": cargo_admin.name or "Cargo Admin",
            "profile_image_url": cargo_admin.profile_image_url,
        }
        for cargo_admin in _active_cargo_admins(db)
    ]


@router.post("/fcl-quote-request", status_code=status.HTTP_201_CREATED)
def create_fcl_quote_request(
    payload: FclQuoteRequestCreate, db: Session = Depends(get_db)
):
    """Create a public FCL request for one active cargo administrator."""
    cargo_admins = _active_cargo_admins(db)
    if not cargo_admins:
        raise HTTPException(
            status_code=503,
            detail="FCL requests are temporarily unavailable. Please try again later.",
        )

    if payload.assigned_cargo_admin_id:
        assigned_cargo_admin = next(
            (
                admin
                for admin in cargo_admins
                if admin.id == payload.assigned_cargo_admin_id
            ),
            None,
        )
        if not assigned_cargo_admin:
            raise HTTPException(
                status_code=400, detail="Selected cargo admin is unavailable"
            )
    elif len(cargo_admins) == 1:
        assigned_cargo_admin = cargo_admins[0]
    else:
        raise HTTPException(status_code=400, detail="Please select a cargo admin")

    quote_request = QuoteRequest(
        request_type=payload.request_type,
        product=payload.product,
        specifications=payload.specifications,
        supplier_status=payload.supplier_status,
        incoterm=payload.incoterm,
        destination=payload.destination,
        company_name=payload.company_name,
        business_license=payload.business_license,
        email=payload.email,
        whatsapp_number=payload.whatsapp_number,
        status="pending",
        assigned_role="cargo_admin",
        assigned_cargo_admin_id=assigned_cargo_admin.id,
    )
    db.add(quote_request)
    db.flush()

    log_action(
        db,
        action="FCL_QUOTE_REQUEST_CREATED",
        entity_type="fcl_quote_request",
        entity_id=quote_request.id,
        metadata={
            "request_type": "FCL",
            "assigned_role": "cargo_admin",
            "assigned_cargo_admin_id": str(assigned_cargo_admin.id),
            "status": "pending",
        },
    )

    create_notification(
        db,
        user_id=assigned_cargo_admin.id,
        notification_type="fcl_quote_request_created",
        message="A new FCL quote request is ready for review.",
        priority="warning",
        target_type="fcl_quote_request",
        target_id=quote_request.id,
    )

    db.commit()
    db.refresh(quote_request)
    _send_fcl_request_emails([assigned_cargo_admin], quote_request)
    return {
        "id": str(quote_request.id),
        "request_type": quote_request.request_type,
        "status": quote_request.status,
        "created_at": quote_request.created_at.isoformat(),
    }


@router.get("/cargo_admin/fcl-requests")
def list_fcl_quote_requests(
    request_status: Optional[str] = Query(None, alias="status"),
    db: Session = Depends(get_db),
    admin: User = Depends(require_roles("cargo_admin")),
):
    """Return the FCL queue assigned exclusively to the cargo-admin role."""
    if request_status and request_status not in FCL_STATUSES:
        raise HTTPException(status_code=400, detail="Invalid FCL request status")

    query = (
        db.query(QuoteRequest)
        .filter(
            QuoteRequest.request_type == "FCL",
            QuoteRequest.assigned_role == "cargo_admin",
            or_(
                QuoteRequest.assigned_cargo_admin_id == admin.id,
                QuoteRequest.assigned_cargo_admin_id.is_(None),
            ),
        )
        .order_by(QuoteRequest.created_at.desc())
    )
    if request_status:
        query = query.filter(QuoteRequest.status == request_status)
    return [_serialize_request(item) for item in query.all()]


@router.get("/cargo_admin/fcl-requests/{request_id}")
def get_fcl_quote_request(
    request_id: UUID,
    db: Session = Depends(get_db),
    admin: User = Depends(require_roles("cargo_admin")),
):
    quote_request = (
        db.query(QuoteRequest)
        .options(joinedload(QuoteRequest.customer))
        .filter(
            QuoteRequest.id == request_id,
            QuoteRequest.request_type == "FCL",
            QuoteRequest.assigned_role == "cargo_admin",
            or_(
                QuoteRequest.assigned_cargo_admin_id == admin.id,
                QuoteRequest.assigned_cargo_admin_id.is_(None),
            ),
        )
        .first()
    )
    if not quote_request:
        raise HTTPException(status_code=404, detail="FCL quote request not found")

    data = _serialize_request(quote_request, include_contact=True)
    history = (
        db.query(AuditLog)
        .filter(
            AuditLog.entity_type == "fcl_quote_request",
            AuditLog.entity_id == quote_request.id,
        )
        .order_by(AuditLog.created_at.asc())
        .all()
    )
    data["status_history"] = [
        {
            "action": entry.action,
            "metadata": entry.extra_data or {},
            "created_at": entry.created_at.isoformat() if entry.created_at else None,
        }
        for entry in history
    ]
    return data


@router.patch("/cargo_admin/fcl-requests/{request_id}/status")
def update_fcl_quote_request_status(
    request_id: UUID,
    payload: FclQuoteStatusUpdate,
    db: Session = Depends(get_db),
    admin: User = Depends(require_roles("cargo_admin")),
):
    quote_request = (
        db.query(QuoteRequest)
        .filter(
            QuoteRequest.id == request_id,
            QuoteRequest.request_type == "FCL",
            QuoteRequest.assigned_role == "cargo_admin",
            or_(
                QuoteRequest.assigned_cargo_admin_id == admin.id,
                QuoteRequest.assigned_cargo_admin_id.is_(None),
            ),
        )
        .first()
    )
    if not quote_request:
        raise HTTPException(status_code=404, detail="FCL quote request not found")

    previous_status = quote_request.status
    quote_request.status = payload.status
    log_action(
        db,
        action="FCL_QUOTE_REQUEST_STATUS_UPDATED",
        user_id=admin.id,
        entity_type="fcl_quote_request",
        entity_id=quote_request.id,
        metadata={"previous_status": previous_status, "status": payload.status},
    )
    db.commit()
    db.refresh(quote_request)
    return _serialize_request(quote_request, include_contact=True)
