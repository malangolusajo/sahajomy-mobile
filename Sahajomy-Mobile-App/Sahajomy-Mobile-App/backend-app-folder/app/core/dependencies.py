"""
RBAC dependencies for Sahajomy.
Roles: super_admin | cargo_admin | sourcing_agent | customer

NOTE: Authentication logic is now centralized in app.core.auth modules.
This file should NOT contain token verification or user lookup logic.
"""

from typing import Optional
from uuid import UUID

from app.core.auth.auth_dependencies import get_current_user
from app.core.auth.auth_utils import get_user_by_id, verify_access_token
from app.core.config import settings
from app.core.security_policy import permission_requires_mfa
from app.core.workspace_actor import (
    workspace_actor_id,
    workspace_branch_id,
    workspace_company_id,
)
from app.database import get_db
from app.models.cargo_workspace import CargoCompany, CargoCompanyMembership
from app.models.user import User
from fastapi import Depends, Header, HTTPException, Request, status
from sqlalchemy.orm import Session


# Public routes can optionally attach an authenticated customer without making
# browsing require a bearer token. Protected routes continue to use the stable
# get_current_user dependency above.
def get_optional_authenticated_user(
    request: Request,
    db=Depends(get_db),
) -> Optional[User]:
    authorization = request.headers.get("authorization", "")
    token = (
        authorization[7:].strip()
        if authorization.lower().startswith("bearer ")
        else request.cookies.get(settings.ACCESS_COOKIE_NAME)
    )
    if not token:
        return None
    try:
        payload = verify_access_token(token)
        return get_user_by_id(db, payload.get("sub"))
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token invalid or expired",
        ) from exc


def require_roles(*roles: str):
    """Factory: returns a dependency that checks the user has one of the given roles."""

    def dependency(current_user: User = Depends(get_current_user)) -> User:
        if current_user.role not in roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access denied. Required role(s): {', '.join(roles)}",
            )
        return current_user

    return dependency


# Convenience dependencies
def get_any_authenticated_user(current_user: User = Depends(get_current_user)) -> User:
    """Any authenticated user with an active account can access core services."""
    # All roles are valid — suspended accounts are already blocked in get_current_user
    return current_user


def get_super_admin(current_user: User = Depends(get_current_user)) -> User:
    if current_user.role != "super_admin":
        raise HTTPException(status_code=403, detail="Super Admin access required")
    return current_user


def _cargo_permission_for_request(request: Request) -> str:
    path = request.url.path.lower()
    is_write = request.method != "GET"
    if "warehouse-automation" in path or "collect" in path or "release" in path:
        return "cargo.release" if is_write else "parcel.view"
    if "manual-cargo-intake" in path:
        if "mark-received" in path:
            return "intake.receive"
        return "intake.manage" if is_write else "intake.view"
    if "customs-packing" in path or "packing-list" in path or "/customers" in path:
        return "customs.manage" if is_write else "customs.view"
    if "warehouse" in path:
        return "warehouse.manage" if is_write else "warehouse.view"
    if "air-departure" in path or "express-air-cargo" in path:
        return "aircargo.manage" if is_write else "aircargo.view"
    if "financial" in path or "payment" in path or "receipt" in path:
        return "payment.confirm" if is_write else "payment.view"
    if "shipment" in path or "tracking" in path:
        return "shipment.update" if is_write else "shipment.view"
    if "sea_booking" in path or "booking" in path or "container" in path:
        return "booking.manage" if is_write else "booking.view"
    return "parcel.edit" if is_write else "parcel.view"


def get_cargo_admin(
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    workspace: Optional[str] = Header(None, alias="X-Sahajomy-Workspace"),
    company_header: Optional[str] = Header(None, alias="X-Sahajomy-Company"),
    branch_header: Optional[str] = Header(None, alias="X-Sahajomy-Branch"),
) -> User:
    required = _cargo_permission_for_request(request)
    if current_user.role == "super_admin":
        return current_user
    if workspace == "personal":
        raise HTTPException(
            status_code=403,
            detail="Switch to a cargo company workspace for company operations.",
        )
    if current_user.role == "cargo_admin" and not company_header:
        if current_user.status != "active":
            raise HTTPException(
                status_code=403, detail="Cargo company account is pending approval."
            )
        if permission_requires_mfa(required) and not current_user.mfa_enabled:
            raise HTTPException(
                status_code=403, detail="MFA is required for this action."
            )
        return current_user
    if not company_header:
        raise HTTPException(status_code=403, detail="Select a cargo company workspace.")
    try:
        company_id = UUID(company_header)
        branch_id = UUID(branch_header) if branch_header else None
    except ValueError as exc:
        raise HTTPException(
            status_code=400, detail="Invalid workspace identifier."
        ) from exc
    membership = (
        db.query(CargoCompanyMembership)
        .filter(
            CargoCompanyMembership.user_id == current_user.id,
            CargoCompanyMembership.company_id == company_id,
            CargoCompanyMembership.status == "active",
        )
        .first()
    )
    if not membership:
        raise HTTPException(status_code=403, detail="Cargo workspace access denied.")
    if (
        branch_id
        and membership.role.scope != "company"
        and branch_id != membership.default_branch_id
    ):
        raise HTTPException(status_code=403, detail="Branch access denied.")
    if required not in {permission.key for permission in membership.role.permissions}:
        raise HTTPException(status_code=403, detail=f"Missing permission: {required}")
    if permission_requires_mfa(required) and not current_user.mfa_enabled:
        raise HTTPException(status_code=403, detail="MFA is required for this action.")
    company = (
        db.query(CargoCompany)
        .filter(CargoCompany.id == company_id, CargoCompany.status == "active")
        .first()
    )
    if not company or not company.created_by_user_id:
        raise HTTPException(status_code=403, detail="Cargo company is not operational.")
    operational_owner = (
        db.query(User).filter(User.id == company.created_by_user_id).first()
    )
    if not operational_owner:
        raise HTTPException(
            status_code=403, detail="Cargo company owner is unavailable."
        )
    workspace_actor_id.set(current_user.id)
    workspace_company_id.set(company_id)
    workspace_branch_id.set(branch_id or membership.default_branch_id)
    return operational_owner


def get_sourcing_agent(
    current_user: User = Depends(get_current_user),
    workspace: Optional[str] = Header(None, alias="X-Sahajomy-Workspace"),
    company_header: Optional[str] = Header(None, alias="X-Sahajomy-Company"),
) -> User:
    if current_user.role == "super_admin":
        return current_user

    if workspace == "personal" or company_header:
        raise HTTPException(
            status_code=403,
            detail="Switch to your sourcing agent workspace for agent operations.",
        )

    if current_user.role != "sourcing_agent":
        raise HTTPException(status_code=403, detail="Sourcing Agent access required")

    if current_user.status != "active":
        raise HTTPException(
            status_code=403,
            detail=(
                "Sourcing agent account is pending approval. "
                "Please wait for super-admin verification."
            ),
        )

    return current_user


def get_customer(
    current_user: User = Depends(get_current_user),
    workspace: Optional[str] = Header(None, alias="X-Sahajomy-Workspace"),
    company_header: Optional[str] = Header(None, alias="X-Sahajomy-Company"),
) -> User:
    if company_header:
        raise HTTPException(
            status_code=403,
            detail="Switch to My Sahajomy Account for personal bookings.",
        )
    if current_user.role in ("customer", "super_admin"):
        return current_user
    if workspace == "personal" and current_user.role in (
        "cargo_admin",
        "sourcing_agent",
    ):
        return current_user
    raise HTTPException(status_code=403, detail="Personal customer workspace required")
