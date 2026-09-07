"""Audit logging helper - creates immutable audit trail for sensitive actions."""

import uuid

from app.core.workspace_actor import (
    workspace_actor_id,
    workspace_branch_id,
    workspace_company_id,
)
from app.models.finance import AuditLog
from sqlalchemy.orm import Session


def log_action(
    db: Session,
    action: str,
    user_id=None,
    entity_type: str = None,
    entity_id=None,
    metadata: dict = None,
    reason: str = None,
):
    """
    Create an audit log entry.
    Required for: hold actions, collection confirmations, admin overrides, role changes.
    """
    actor_id = workspace_actor_id.get() or user_id
    context_metadata = dict(metadata or {})
    if workspace_company_id.get():
        context_metadata.setdefault("company_id", str(workspace_company_id.get()))
    if workspace_branch_id.get():
        context_metadata.setdefault("branch_id", str(workspace_branch_id.get()))
    log = AuditLog(
        user_id=actor_id,
        action=action,
        entity_type=entity_type,
        entity_id=entity_id,
        extra_data=context_metadata,
        reason=reason,
    )
    db.add(log)
    db.flush()  # Don't commit here; let the caller commit the transaction
