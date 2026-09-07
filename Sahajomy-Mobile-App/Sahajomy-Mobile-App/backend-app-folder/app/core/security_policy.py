"""Security policy shared by authentication and authorization dependencies."""

MFA_REQUIRED_ROLES = {"super_admin", "cargo_admin", "sourcing_agent"}

SENSITIVE_WORKSPACE_PERMISSIONS = {
    "company.staff.create",
    "company.staff.disable",
    "company.billing.manage",
    "payment.confirm",
    "finance.payment.confirm",
    "finance.expense.approve",
    "finance.export",
}


def permission_requires_mfa(permission: str) -> bool:
    return permission in SENSITIVE_WORKSPACE_PERMISSIONS
