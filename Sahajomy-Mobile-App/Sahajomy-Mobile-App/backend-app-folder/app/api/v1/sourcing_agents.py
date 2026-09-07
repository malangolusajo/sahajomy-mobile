"""Compatibility shim for sourcing-agent registration routes.

Canonical location:
    app.api.v1.sourcing_agent.registration_routes

This keeps imports stable while we align route modules under the
existing `sourcing_agent` package to reduce naming confusion.
"""

from app.api.v1.sourcing_agent.registration_routes import router

__all__ = ["router"]
