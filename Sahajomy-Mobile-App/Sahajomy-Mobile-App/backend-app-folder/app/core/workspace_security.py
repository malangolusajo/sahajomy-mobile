"""Trusted active-workspace resolution and permission dependencies."""

from dataclasses import dataclass
from uuid import UUID

from app.core.auth.auth_dependencies import get_current_user
from app.core.security_policy import permission_requires_mfa
from app.database import get_db
from app.models.cargo_workspace import CargoCompanyMembership
from fastapi import Depends, Header, HTTPException
from sqlalchemy.orm import Session


@dataclass
class WorkspaceContext:
    user: object
    membership: CargoCompanyMembership
    company_id: UUID
    branch_id: UUID | None
    permissions: set[str]


def get_workspace_context(
    x_sahajomy_company: str = Header(..., alias="X-Sahajomy-Company"),
    x_sahajomy_branch: str | None = Header(None, alias="X-Sahajomy-Branch"),
    user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        company_id = UUID(x_sahajomy_company)
        requested_branch_id = UUID(x_sahajomy_branch) if x_sahajomy_branch else None
    except ValueError as exc:
        raise HTTPException(400, "Invalid workspace identifier.") from exc
    membership = (
        db.query(CargoCompanyMembership)
        .filter(
            CargoCompanyMembership.user_id == user.id,
            CargoCompanyMembership.company_id == company_id,
            CargoCompanyMembership.status == "active",
        )
        .first()
    )
    if not membership:
        raise HTTPException(403, "The selected cargo workspace is not available.")
    branch_id = requested_branch_id or membership.default_branch_id
    if (
        branch_id
        and membership.role.scope != "company"
        and branch_id != membership.default_branch_id
    ):
        raise HTTPException(403, "You are not assigned to this branch.")
    return WorkspaceContext(
        user=user,
        membership=membership,
        company_id=membership.company_id,
        branch_id=branch_id,
        permissions={p.key for p in membership.role.permissions},
    )


def require_permission(key):
    def dependency(context: WorkspaceContext = Depends(get_workspace_context)):
        if key not in context.permissions:
            raise HTTPException(403, f"Missing permission: {key}")
        if permission_requires_mfa(key) and not context.user.mfa_enabled:
            raise HTTPException(403, "MFA is required for this action.")
        return context

    return dependency
