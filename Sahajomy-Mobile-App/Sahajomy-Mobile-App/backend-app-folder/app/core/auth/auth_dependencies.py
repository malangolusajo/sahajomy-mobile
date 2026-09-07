"""
STABLE AUTHENTICATION DEPENDENCIES - DO NOT MODIFY UNDER ANY CIRCUMSTANCES
========================================================================

This module provides the get_current_user dependency using consistent user ID lookup.
It is the ONLY entry point for authentication in protected endpoints.

CRITICAL RULES:
- This is the single source of truth for user authentication
- NEVER change the dependency signature or logic
- ALWAYS use user ID as subject (never phone number or other fields)
- All protected endpoints MUST use this dependency

Any modification will cause system-wide 401 Unauthorized errors.
"""

from app.core.auth.auth_utils import get_user_by_id, verify_access_token
from app.core.config import settings
from app.database import get_db
from fastapi import Depends, HTTPException, Request, status
from sqlalchemy.orm import Session


def get_current_user(request: Request, db: Session = Depends(get_db)):
    """
    Get current authenticated user from JWT token.
    This is the ONLY dependency for protected endpoints.
    Uses user ID as subject for reliable lookup.
    """
    try:
        authorization = request.headers.get("authorization", "")
        bearer_token = (
            authorization[7:].strip()
            if authorization.lower().startswith("bearer ")
            else None
        )
        token = bearer_token or request.cookies.get(settings.ACCESS_COOKIE_NAME)
        if not token:
            raise ValueError("Authentication required")
        payload = verify_access_token(token)
        user_id = payload.get("sub")

        # Get user by ID (this validates existence and status)
        user = get_user_by_id(db, user_id)

        return user

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Token invalid or expired"
        )
