"""Request-local actor identity for legacy cargo operations."""

from contextvars import ContextVar

workspace_actor_id = ContextVar("workspace_actor_id", default=None)
workspace_company_id = ContextVar("workspace_company_id", default=None)
workspace_branch_id = ContextVar("workspace_branch_id", default=None)
