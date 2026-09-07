"""One-login multi-workspace API for cargo companies, branches, and staff."""

import hashlib
import secrets
from datetime import datetime
from typing import Optional
from uuid import UUID

from app.core.audit import log_action
from app.core.auth.auth_dependencies import get_current_user
from app.core.config import settings
from app.core.email_service import send_staff_invitation_email
from app.core.encryption import data_encryption
from app.core.validation import validate_and_format_phone, validate_email
from app.core.workspace_security import (
    WorkspaceContext,
    get_workspace_context,
    require_permission,
)
from app.database import get_db
from app.models.cargo_workspace import (
    CargoBranch,
    CargoCompanyMembership,
    CargoRole,
    CargoStaffInvitation,
)
from app.models.container import Warehouse
from app.models.user import User
from app.services.cargo_dashboard import build_cargo_dashboard
from app.services.subscriptions import (
    company_branch_count,
    company_staff_seats,
    enforce_resource_limit,
)
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import or_
from sqlalchemy.orm import Session

router = APIRouter(prefix="/workspaces", tags=["Workspaces & cargo staff"])

PERMISSION_KEYS = [
    "company.staff.create",
    "company.staff.disable",
    "company.branch.manage",
    "parcel.view",
    "parcel.receive",
    "parcel.edit",
    "parcel.reassign",
    "booking.view",
    "booking.manage",
    "shipment.view",
    "shipment.update",
    "payment.view",
    "payment.confirm",
    "cargo.release",
    "audit.view",
    "customs.view",
    "customs.manage",
    "intake.view",
    "intake.receive",
    "intake.manage",
    "warehouse.view",
    "warehouse.manage",
    "aircargo.view",
    "aircargo.manage",
    "finance.dashboard.view",
    "finance.revenue.view",
    "finance.cost.view",
    "finance.profit.view",
    "finance.expense.view",
    "finance.expense.create",
    "finance.expense.approve",
    "finance.receivables.view",
    "finance.payment.confirm",
    "finance.reports.view",
    "finance.export",
    "company.billing.view",
    "company.billing.manage",
]


def membership_payload(m):
    return {
        "id": str(m.id),
        "type": "cargo_company",
        "company_id": str(m.company_id),
        "company_name": m.company.name,
        "logo_url": m.company.logo_url,
        "branch_id": str(m.default_branch_id) if m.default_branch_id else None,
        "branch_name": m.default_branch.name if m.default_branch else None,
        "role_id": str(m.role_id),
        "role": m.role.name,
        "status": m.status,
        "permissions": sorted(p.key for p in m.role.permissions),
    }


@router.get("")
def list_workspaces(
    user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    memberships = (
        db.query(CargoCompanyMembership)
        .filter(
            CargoCompanyMembership.user_id == user.id,
            CargoCompanyMembership.status == "active",
        )
        .all()
    )
    operational = []
    if user.role == "sourcing_agent":
        operational.append(
            {
                "id": "sourcing_agent",
                "type": "sourcing_agent",
                "name": "Sourcing Agent Workspace",
            }
        )
    elif user.role == "cargo_admin" and not memberships:
        # Compatibility for operator accounts created before company workspaces.
        operational.append(
            {
                "id": "cargo_operations",
                "type": "cargo_operations",
                "name": "Cargo Operations",
            }
        )

    return {
        "personal": {
            "id": "personal",
            "type": "personal",
            "name": "My Sahajomy Account",
        },
        "operational": operational,
        "companies": [membership_payload(m) for m in memberships],
    }


@router.get("/dashboard")
def workspace_dashboard(
    ctx: WorkspaceContext = Depends(get_workspace_context),
    db: Session = Depends(get_db),
):
    """Return only dashboard sections allowed in the active cargo workspace."""
    owner_id = ctx.membership.company.created_by_user_id
    if not owner_id:
        raise HTTPException(409, "This cargo company has no operational owner.")

    branch_id = ctx.branch_id
    warehouse_id = None
    if branch_id:
        branch = (
            db.query(CargoBranch)
            .filter(
                CargoBranch.id == branch_id,
                CargoBranch.company_id == ctx.company_id,
                CargoBranch.status == "active",
            )
            .first()
        )
        if not branch:
            raise HTTPException(404, "The active cargo branch was not found.")
        warehouse_id = branch.warehouse_id

    return build_cargo_dashboard(
        db,
        owner_id=owner_id,
        permissions=ctx.permissions,
        role_name=ctx.membership.role.name,
        role_scope=ctx.membership.role.scope,
        company_id=ctx.company_id,
        branch_id=branch_id,
        warehouse_id=warehouse_id,
    )


class BranchCreate(BaseModel):
    name: str = Field(..., min_length=2, max_length=150)
    warehouse_id: UUID


def _company_warehouses(ctx: WorkspaceContext, db: Session):
    """Warehouses are still owned by the company's original operator user."""
    owner_id = ctx.membership.company.created_by_user_id
    if not owner_id:
        return db.query(Warehouse).filter(False)
    return db.query(Warehouse).filter(Warehouse.admin_id == owner_id)


@router.get("/warehouses")
def list_branch_warehouses(
    ctx: WorkspaceContext = Depends(require_permission("company.branch.manage")),
    db: Session = Depends(get_db),
):
    return [
        {
            "id": str(warehouse.id),
            "name": warehouse.name,
            "city": warehouse.city,
            "country": warehouse.country,
        }
        for warehouse in _company_warehouses(ctx, db).order_by(Warehouse.name).all()
    ]


@router.get("/branches")
def list_branches(
    ctx: WorkspaceContext = Depends(require_permission("company.branch.manage")),
    db: Session = Depends(get_db),
):
    return db.query(CargoBranch).filter(CargoBranch.company_id == ctx.company_id).all()


@router.post("/branches", status_code=201)
def create_branch(
    body: BranchCreate,
    ctx: WorkspaceContext = Depends(require_permission("company.branch.manage")),
    db: Session = Depends(get_db),
):
    enforce_resource_limit(
        db,
        ctx.company_id,
        "branches",
        company_branch_count(db, ctx.company_id),
    )
    warehouse = (
        _company_warehouses(ctx, db).filter(Warehouse.id == body.warehouse_id).first()
    )
    if not warehouse:
        raise HTTPException(404, "Warehouse not found for this cargo company.")
    if not warehouse.city or not warehouse.country:
        raise HTTPException(
            422,
            "Add the city and country to this warehouse before assigning it to a branch.",
        )
    duplicate = (
        db.query(CargoBranch)
        .filter(
            CargoBranch.company_id == ctx.company_id,
            CargoBranch.name.ilike(body.name.strip()),
        )
        .first()
    )
    if duplicate:
        raise HTTPException(409, "A branch with this name already exists.")
    branch = CargoBranch(
        company_id=ctx.company_id,
        name=body.name.strip(),
        warehouse_id=warehouse.id,
        country=warehouse.country,
        city=warehouse.city,
    )
    db.add(branch)
    db.flush()
    log_action(
        db,
        "CARGO_BRANCH_CREATED",
        ctx.user.id,
        "cargo_branch",
        branch.id,
        {"company_id": str(ctx.company_id), "branch": body.name},
    )
    db.commit()
    db.refresh(branch)
    return branch


@router.get("/roles")
def list_roles(
    ctx: WorkspaceContext = Depends(get_workspace_context),
    db: Session = Depends(get_db),
):
    roles = (
        db.query(CargoRole)
        .filter(
            or_(CargoRole.company_id == ctx.company_id, CargoRole.company_id.is_(None))
        )
        .all()
    )
    return [
        {
            "id": str(r.id),
            "name": r.name,
            "scope": r.scope,
            "permissions": sorted(p.key for p in r.permissions),
        }
        for r in roles
    ]


@router.get("/staff")
def list_staff(
    ctx: WorkspaceContext = Depends(require_permission("company.staff.create")),
    db: Session = Depends(get_db),
):
    rows = (
        db.query(CargoCompanyMembership)
        .filter(CargoCompanyMembership.company_id == ctx.company_id)
        .all()
    )
    return [
        {
            **membership_payload(m),
            "user_id": str(m.user_id),
            "name": m.user.name,
            "email": m.user.secure_email,
            "phone_number": m.user.secure_phone,
        }
        for m in rows
    ]


class StaffInvite(BaseModel):
    email: str = Field(..., min_length=3, max_length=254)
    phone_number: str = Field(..., min_length=8, max_length=30)
    role_id: UUID
    branch_id: Optional[UUID] = None


@router.post("/staff/invitations", status_code=201)
def invite_staff(
    body: StaffInvite,
    ctx: WorkspaceContext = Depends(require_permission("company.staff.create")),
    db: Session = Depends(get_db),
):
    email = body.email.strip().lower()
    if not validate_email(email):
        raise HTTPException(422, "Enter a valid, non-disposable email address.")
    if not body.phone_number.startswith("+"):
        raise HTTPException(
            422, "Phone number must include its country code (for example, +255...)."
        )
    valid_phone, phone_number = validate_and_format_phone(body.phone_number)
    if not valid_phone:
        raise HTTPException(422, "Enter a valid phone number with its country code.")
    role = (
        db.query(CargoRole)
        .filter(
            CargoRole.id == body.role_id,
            or_(CargoRole.company_id == ctx.company_id, CargoRole.company_id.is_(None)),
        )
        .first()
    )
    if not role:
        raise HTTPException(404, "Role not found.")
    if (
        body.branch_id
        and not db.query(CargoBranch)
        .filter(
            CargoBranch.id == body.branch_id, CargoBranch.company_id == ctx.company_id
        )
        .first()
    ):
        raise HTTPException(404, "Branch not found.")
    enforce_resource_limit(
        db,
        ctx.company_id,
        "staff_users",
        company_staff_seats(db, ctx.company_id),
    )
    email_hash = data_encryption.hash_email(email)
    phone_hash = data_encryption.hash_phone(phone_number)
    user = (
        db.query(User)
        .filter(
            or_(
                User.phone_hash == phone_hash,
                User.phone_number == phone_number,
            )
        )
        .first()
    )
    existing_user = user is not None
    if user:
        user_email_hash = user.email_hash or (
            data_encryption.hash_email(user.secure_email.strip().lower())
            if user.secure_email
            else None
        )
        if user_email_hash != email_hash:
            raise HTTPException(
                409,
                "The phone number and email do not belong to the same Sahajomy account.",
            )
        existing = (
            db.query(CargoCompanyMembership)
            .filter_by(user_id=user.id, company_id=ctx.company_id)
            .first()
        )
        if existing:
            raise HTTPException(
                409, "This person already belongs to the cargo company."
            )
    raw_token = secrets.token_urlsafe(32)
    invitation_path = f"/staff-invitation?token={raw_token}"
    invitation = CargoStaffInvitation(
        company_id=ctx.company_id,
        branch_id=body.branch_id,
        role_id=body.role_id,
        invited_email_hash=email_hash,
        invited_phone_hash=phone_hash,
        token_hash=hashlib.sha256(raw_token.encode()).hexdigest(),
        invited_by_user_id=ctx.user.id,
    )
    db.add(invitation)
    db.flush()
    invitation_sent = send_staff_invitation_email(
        email,
        ctx.membership.company.name,
        f"{settings.public_app_url}{invitation_path}",
    )
    if not invitation_sent:
        db.rollback()
        raise HTTPException(
            502, "Could not send the invitation email. Please try again."
        )
    log_action(
        db,
        "CARGO_STAFF_INVITED",
        ctx.user.id,
        "cargo_staff_invitation",
        invitation.id,
        {"company_id": str(ctx.company_id)},
    )
    db.commit()
    return {
        "existing_user": existing_user,
        "invitation_id": str(invitation.id),
        "invitation_token": raw_token,
        "invitation_path": invitation_path,
        "invitation_email_sent": True,
    }


class InvitationAccept(BaseModel):
    token: str


@router.post("/staff/invitations/accept")
def accept_invitation(
    body: InvitationAccept,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    token_hash = hashlib.sha256(body.token.encode()).hexdigest()
    invite = (
        db.query(CargoStaffInvitation)
        .filter_by(token_hash=token_hash, status="pending")
        .first()
    )
    if not invite or invite.expires_at <= datetime.utcnow():
        raise HTTPException(400, "Invitation is invalid or expired.")
    current_email_hash = user.email_hash or (
        data_encryption.hash_email(user.secure_email.strip().lower())
        if user.secure_email
        else None
    )
    current_phone_hash = user.phone_hash or (
        data_encryption.hash_phone(user.secure_phone) if user.secure_phone else None
    )
    # Phone is the login identity for all new staff invitations. Retain email
    # matching only for legacy invitations created before phone became required.
    valid_contact = (
        invite.invited_phone_hash == current_phone_hash
        if invite.invited_phone_hash
        else bool(
            invite.invited_email_hash
            and invite.invited_email_hash == current_email_hash
        )
    )
    if not valid_contact:
        raise HTTPException(
            403, "This invitation belongs to a different Sahajomy identity."
        )
    membership = (
        db.query(CargoCompanyMembership)
        .filter_by(user_id=user.id, company_id=invite.company_id)
        .first()
    )
    if not membership:
        membership = CargoCompanyMembership(
            user_id=user.id,
            company_id=invite.company_id,
            role_id=invite.role_id,
            default_branch_id=invite.branch_id,
            status="active",
            joined_at=datetime.utcnow(),
            created_by_user_id=invite.invited_by_user_id,
        )
        db.add(membership)
        db.flush()
    invite.status = "accepted"
    invite.accepted_at = datetime.utcnow()
    log_action(
        db,
        "CARGO_STAFF_INVITATION_ACCEPTED",
        user.id,
        "cargo_company_membership",
        membership.id,
        {"company_id": str(invite.company_id)},
    )
    db.commit()
    return membership_payload(membership)


class MembershipUpdate(BaseModel):
    role_id: Optional[UUID] = None
    branch_id: Optional[UUID] = None
    status: Optional[str] = Field(None, pattern="^(active|disabled)$")


@router.patch("/staff/{membership_id}")
def update_staff(
    membership_id: UUID,
    body: MembershipUpdate,
    ctx: WorkspaceContext = Depends(require_permission("company.staff.disable")),
    db: Session = Depends(get_db),
):
    membership = (
        db.query(CargoCompanyMembership)
        .filter_by(id=membership_id, company_id=ctx.company_id)
        .first()
    )
    if not membership:
        raise HTTPException(404, "Staff membership not found.")
    if membership.role.name == "Cargo Company Owner":
        raise HTTPException(
            403, "The cargo company owner membership cannot be disabled or reassigned."
        )
    before = {
        "role_id": str(membership.role_id),
        "branch_id": str(membership.default_branch_id),
        "status": membership.status,
    }
    if body.role_id:
        role = (
            db.query(CargoRole)
            .filter(
                CargoRole.id == body.role_id,
                or_(
                    CargoRole.company_id == ctx.company_id,
                    CargoRole.company_id.is_(None),
                ),
            )
            .first()
        )
        if not role or role.name == "Cargo Company Owner":
            raise HTTPException(404, "Assignable role not found.")
        membership.role_id = body.role_id
    if "branch_id" in body.model_fields_set:
        if (
            body.branch_id
            and not db.query(CargoBranch)
            .filter_by(id=body.branch_id, company_id=ctx.company_id)
            .first()
        ):
            raise HTTPException(404, "Branch not found.")
        membership.default_branch_id = body.branch_id
    if body.status:
        membership.status = body.status
        membership.disabled_at = (
            datetime.utcnow() if body.status == "disabled" else None
        )
    log_action(
        db,
        "CARGO_STAFF_UPDATED",
        ctx.user.id,
        "cargo_company_membership",
        membership.id,
        {"before": before, "company_id": str(ctx.company_id)},
    )
    db.commit()
    db.refresh(membership)
    return membership_payload(membership)
