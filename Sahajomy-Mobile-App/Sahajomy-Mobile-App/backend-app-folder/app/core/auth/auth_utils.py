"""
STABLE AUTHENTICATION UTILITIES - DO NOT MODIFY UNDER ANY CIRCUMSTANCES
======================================================================

This module provides consistent token creation and verification using user ID as subject.
It was created to resolve authentication inconsistencies that were causing 401 errors.

CRITICAL RULES:
- Token subjects MUST remain as user ID (str(user.id))
- NEVER change the token structure or payload format
- NEVER modify the verification logic
- This is the single source of truth for all JWT operations

Any changes will break the entire authentication system.
"""

import secrets
from datetime import datetime, timedelta
from typing import Optional

import jwt
from app.core.config import settings
from app.models.user import User
from jwt.exceptions import PyJWTError as JWTError
from sqlalchemy.orm import Session


def create_access_token(user_id: str, role: str) -> str:
    """Create a JWT access token with user ID as subject."""
    to_encode = {"sub": user_id, "role": role}
    expire = datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update(
        {
            "exp": expire,
            "type": "access",
            "jti": secrets.token_hex(16),
            "iat": datetime.utcnow(),
        }
    )
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def create_refresh_token(user_id: str, role: str) -> str:
    """Create a JWT refresh token with user ID as subject."""
    to_encode = {"sub": user_id, "role": role}
    expire = datetime.utcnow() + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    to_encode.update(
        {
            "exp": expire,
            "type": "refresh",
            "jti": secrets.token_hex(16),
            "iat": datetime.utcnow(),
        }
    )
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def create_mfa_challenge_token(user_id: str, challenge_type: str) -> str:
    """Create a short-lived token which cannot authorize normal API requests."""
    payload = {
        "sub": user_id,
        "type": challenge_type,
        "jti": secrets.token_hex(16),
        "iat": datetime.utcnow(),
        "exp": datetime.utcnow() + timedelta(minutes=10),
    }
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def verify_mfa_challenge_token(token: str) -> dict:
    payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
    if payload.get("type") not in {"mfa_setup", "mfa_challenge"}:
        raise JWTError("Invalid MFA challenge")
    return payload


def verify_access_token(token: str) -> dict:
    """Verify and decode an access token."""
    try:
        payload = jwt.decode(
            token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM]
        )
        if payload.get("type") != "access":
            raise JWTError("Invalid token type")
        return payload
    except JWTError:
        raise JWTError("Invalid or expired access token")


def verify_refresh_token(token: str) -> dict:
    """Verify and decode a refresh token."""
    try:
        payload = jwt.decode(
            token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM]
        )
        if payload.get("type") != "refresh":
            raise JWTError("Invalid token type")
        return payload
    except JWTError:
        raise JWTError("Invalid or expired refresh token")


def get_user_by_id(db: Session, user_id: str) -> Optional[User]:
    """
    Get user by ID with validation.
    Returns User object if found and active, None otherwise.
    """
    user = db.query(User).filter(User.id == user_id).first()

    if not user:
        raise JWTError("User not found")

    if user.status == "suspended":
        raise JWTError("Account suspended")

    return user
