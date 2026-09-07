"""Auth API - Phone + Email OTP registration/login for Sahajomy.
Roles: super_admin | cargo_admin | sourcing_agent | customer
Guests: handled separately, no JWT.

NOTE: This file uses STABLE authentication utilities from app.core.auth.
DO NOT modify token creation/verification logic here - it's centralized in auth_utils.
"""

import hashlib
import secrets
from datetime import datetime, timedelta
from typing import Optional

import pyotp
from app.core.audit import log_action
from app.core.auth.auth_dependencies import (
    get_current_user as get_current_user_from_auth_deps,
)
from app.core.auth.auth_utils import (
    create_access_token,
    create_mfa_challenge_token,
    create_refresh_token,
    verify_mfa_challenge_token,
    verify_refresh_token,
)
from app.core.config import settings
from app.core.encryption import data_encryption
from app.core.otp_service import (
    OTP_EXPIRED_MESSAGE,
    OTP_INVALID_MESSAGE,
    send_otp_to_user,
    verify_otp,
)
from app.core.security_policy import (
    MFA_REQUIRED_ROLES,
    SENSITIVE_WORKSPACE_PERMISSIONS,
)
from app.database import get_db
from app.models.cargo_workspace import CargoCompanyMembership
from app.models.user import RefreshToken, User
from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from jwt.exceptions import PyJWTError as JWTError
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

router = APIRouter(prefix="/auth", tags=["Authentication"])


def _cargo_operator_profile_payload(user: User):
    profile = getattr(user, "cargo_operator_profile", None)
    if user.role != "cargo_admin" or not profile:
        return None
    return {
        "company_name": profile.company_name,
        "service_types": list(profile.service_types or []),
        "destination_countries": list(profile.destination_countries or []),
        "china_origin_cities": list(profile.china_origin_cities or []),
        "status": profile.status,
    }


def _requires_mfa(db: Session, user: User) -> bool:
    if user.role in MFA_REQUIRED_ROLES:
        return True
    memberships = (
        db.query(CargoCompanyMembership)
        .filter(
            CargoCompanyMembership.user_id == user.id,
            CargoCompanyMembership.status == "active",
        )
        .all()
    )
    return any(
        SENSITIVE_WORKSPACE_PERMISSIONS.intersection(
            permission.key for permission in membership.role.permissions
        )
        for membership in memberships
    )


def _hash_refresh_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def _find_active_refresh_token(db: Session, raw_token: str) -> Optional[RefreshToken]:
    """Look up refresh token by hashed value, with legacy plaintext fallback."""
    token_hash = _hash_refresh_token(raw_token)
    return (
        db.query(RefreshToken)
        .filter(
            RefreshToken.token.in_([token_hash, raw_token]),
            RefreshToken.revoked.is_(False),
            RefreshToken.expires_at > datetime.utcnow(),
        )
        .order_by(RefreshToken.created_at.desc())
        .first()
    )


def _cookie_secure() -> bool:
    return settings.ENVIRONMENT == "production"


def _set_auth_cookies(
    response: Response, access_token: str, refresh_token: Optional[str] = None
) -> None:
    common = {
        "secure": _cookie_secure(),
        "samesite": "strict",
    }
    response.set_cookie(
        settings.ACCESS_COOKIE_NAME,
        access_token,
        httponly=True,
        path="/",
        max_age=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        **common,
    )
    if refresh_token:
        response.set_cookie(
            settings.REFRESH_COOKIE_NAME,
            refresh_token,
            httponly=True,
            path="/api/v1/auth",
            max_age=settings.REFRESH_TOKEN_EXPIRE_DAYS * 86400,
            **common,
        )
    response.set_cookie(
        settings.CSRF_COOKIE_NAME,
        secrets.token_urlsafe(32),
        httponly=False,
        path="/",
        max_age=settings.REFRESH_TOKEN_EXPIRE_DAYS * 86400,
        **common,
    )


def _clear_auth_cookies(response: Response) -> None:
    response.delete_cookie(settings.ACCESS_COOKIE_NAME, path="/")
    response.delete_cookie(settings.REFRESH_COOKIE_NAME, path="/api/v1/auth")
    response.delete_cookie(settings.CSRF_COOKIE_NAME, path="/")


def _user_payload(user: User) -> dict:
    phone = user.secure_phone or user.phone_number
    email = user.secure_email or user.email
    return {
        "id": str(user.id),
        "phone_number": f"***{phone[-4:]}" if phone else None,
        "email": email,
        "name": user.name,
        "role": user.role,
        "status": user.status,
        "is_verified": user.is_verified,
        "profile_image_url": user.profile_image_url,
        "mfa_enabled": bool(user.mfa_enabled),
        "cargo_operator_profile": _cargo_operator_profile_payload(user),
    }


def _issue_session(db: Session, user: User, response: Response) -> dict:
    access_token = create_access_token(str(user.id), user.role)
    refresh_token_value = create_refresh_token(str(user.id), user.role)
    db.add(
        RefreshToken(
            token=_hash_refresh_token(refresh_token_value),
            user_id=user.id,
            expires_at=datetime.utcnow()
            + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS),
        )
    )
    db.commit()
    _set_auth_cookies(response, access_token, refresh_token_value)
    phone = user.secure_phone or user.phone_number
    log_action(
        db=db,
        action="LOGIN_MFA" if user.mfa_enabled else "LOGIN_OTP",
        user_id=user.id,
        entity_type="user",
        entity_id=user.id,
        metadata={
            "phone_number": f"***{phone[-4:]}" if phone else None,
            "role": user.role,
            "mfa": bool(user.mfa_enabled),
        },
    )
    # Tokens remain in the response for native/API clients. The browser client
    # deliberately ignores them and uses the HttpOnly cookies set above.
    return {
        "access_token": access_token,
        "refresh_token": refresh_token_value,
        "token_type": "bearer",
        "user": _user_payload(user),
    }


# ─── Schemas ────────────────────────────────────────────────────────


class SendOTPRequest(BaseModel):
    phone_number: str = Field(
        ..., min_length=7, max_length=25, pattern=r"^[\+]?[0-9\s\-\(\)]{7,25}$"
    )
    name: Optional[str] = None
    email: Optional[str] = None


class VerifyOTPRequest(BaseModel):
    phone_number: str = Field(
        ..., min_length=7, max_length=25, pattern=r"^[\+]?[0-9\s\-\(\)]{7,25}$"
    )
    otp_code: str = Field(..., min_length=4, max_length=8, pattern=r"^\d{4,8}$")


class RefreshTokenRequest(BaseModel):
    refresh_token: Optional[str] = None


class LogoutRequest(BaseModel):
    refresh_token: Optional[str] = None


class ProfileImageUpdateRequest(BaseModel):
    profile_image_url: Optional[str] = None


class MFAChallengeRequest(BaseModel):
    challenge_token: str = Field(..., min_length=40, max_length=4096)
    code: str = Field(..., min_length=6, max_length=6, pattern=r"^\d{6}$")


class MFASetupRequest(BaseModel):
    challenge_token: str = Field(..., min_length=40, max_length=4096)


# ─── Endpoints ──────────────────────────────────────────────────────


@router.post("/send-otp")
def send_otp(body: SendOTPRequest, db: Session = Depends(get_db)):
    """
    Request OTP for phone-based login.
    For new users: require name and email, store them, then send OTP via email
    For returning users: use stored email to send OTP via email
    """
    return send_otp_to_user(
        phone_number=body.phone_number, name=body.name, email=body.email, db=db
    )


@router.post("/verify-otp")
def verify_otp_endpoint(
    body: VerifyOTPRequest, response: Response, db: Session = Depends(get_db)
):
    """Verify OTP and issue JWT access + refresh tokens."""
    success, user, error_msg = verify_otp(
        phone_number=body.phone_number, otp_code=body.otp_code, db=db
    )

    if not success:
        if error_msg == OTP_EXPIRED_MESSAGE:
            raise HTTPException(status_code=status.HTTP_410_GONE, detail=error_msg)
        if error_msg == OTP_INVALID_MESSAGE:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail=error_msg
            )
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=error_msg)

    # Check if account is suspended
    if user.status == "suspended":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account suspended. Contact support.",
        )

    if _requires_mfa(db, user):
        challenge_type = "mfa_challenge" if user.mfa_enabled else "mfa_setup"
        return {
            "mfa_required": user.mfa_enabled,
            "mfa_setup_required": not user.mfa_enabled,
            "challenge_token": create_mfa_challenge_token(str(user.id), challenge_type),
        }

    return _issue_session(db, user, response)


@router.post("/mfa/setup")
def setup_mfa(body: MFASetupRequest, db: Session = Depends(get_db)):
    try:
        payload = verify_mfa_challenge_token(body.challenge_token)
    except JWTError as exc:
        raise HTTPException(
            status_code=401, detail="MFA setup session expired"
        ) from exc
    if payload.get("type") != "mfa_setup":
        raise HTTPException(status_code=403, detail="MFA setup is not authorized")
    user = db.query(User).filter(User.id == payload.get("sub")).first()
    if not user or user.status != "active" or not _requires_mfa(db, user):
        raise HTTPException(status_code=403, detail="MFA setup is not authorized")
    secret = pyotp.random_base32()
    user.mfa_secret_encrypted = data_encryption.encrypt_text(secret)
    db.commit()
    return {
        "secret": secret,
        "provisioning_uri": pyotp.TOTP(secret).provisioning_uri(
            name=user.secure_email or user.name or str(user.id), issuer_name="Sahajomy"
        ),
    }


@router.post("/mfa/verify")
def verify_mfa(
    body: MFAChallengeRequest,
    response: Response,
    db: Session = Depends(get_db),
):
    try:
        payload = verify_mfa_challenge_token(body.challenge_token)
    except JWTError as exc:
        raise HTTPException(status_code=401, detail="MFA session expired") from exc
    user = db.query(User).filter(User.id == payload.get("sub")).first()
    if not user or user.status != "active" or not user.mfa_secret_encrypted:
        raise HTTPException(status_code=403, detail="MFA verification is unavailable")
    secret = data_encryption.decrypt_text(user.mfa_secret_encrypted)
    if not pyotp.TOTP(secret).verify(body.code, valid_window=1):
        raise HTTPException(
            status_code=400, detail="The authenticator code is incorrect"
        )
    if payload.get("type") == "mfa_setup":
        user.mfa_enabled = True
        user.mfa_enrolled_at = datetime.utcnow()
        db.commit()
    elif not user.mfa_enabled:
        raise HTTPException(status_code=403, detail="MFA enrollment is incomplete")
    return _issue_session(db, user, response)


@router.post("/refresh")
def refresh_token(
    request: Request,
    response: Response,
    body: Optional[RefreshTokenRequest] = None,
    db: Session = Depends(get_db),
):
    """Exchange refresh token for a new access token."""
    raw_refresh_token = (body.refresh_token if body else None) or request.cookies.get(
        settings.REFRESH_COOKIE_NAME
    )
    if not raw_refresh_token:
        raise HTTPException(status_code=401, detail="Refresh token required")
    db_token = _find_active_refresh_token(db, raw_refresh_token)

    if not db_token:
        raise HTTPException(status_code=401, detail="Invalid or revoked refresh token")

    try:
        payload = verify_refresh_token(raw_refresh_token)
        user_id = payload.get("sub")
        role = payload.get("role")
        if not user_id or not role:
            raise HTTPException(status_code=401, detail="Invalid refresh token")
        if str(db_token.user_id) != str(user_id):
            db_token.revoked = True
            db.commit()
            raise HTTPException(status_code=401, detail="Invalid refresh token")

        user = db.query(User).filter(User.id == db_token.user_id).first()
        if not user:
            db_token.revoked = True
            db.commit()
            raise HTTPException(status_code=401, detail="Invalid refresh token")
        if user.status == "suspended":
            db_token.revoked = True
            db.commit()
            raise HTTPException(
                status_code=403, detail="Account suspended. Contact support."
            )
        if _requires_mfa(db, user) and not user.mfa_enabled:
            db_token.revoked = True
            db.commit()
            _clear_auth_cookies(response)
            raise HTTPException(status_code=403, detail="MFA enrollment is required")

        # Create new access token
        new_access = create_access_token(str(user.id), user.role)
        response_payload = {"access_token": new_access, "token_type": "bearer"}
        rotated_refresh = None

        # Rotate refresh token on each successful use.
        if settings.REFRESH_ROTATION_ENABLED:
            db_token.revoked = True
            new_refresh_token_val = create_refresh_token(str(user.id), user.role)
            rotated_refresh = new_refresh_token_val
            db.add(
                RefreshToken(
                    token=_hash_refresh_token(new_refresh_token_val),
                    user_id=user.id,
                    expires_at=datetime.utcnow()
                    + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS),
                )
            )
            db.commit()
            response_payload["refresh_token"] = new_refresh_token_val

        _set_auth_cookies(response, new_access, rotated_refresh)
        return response_payload

    except JWTError:
        db_token.revoked = True
        db.commit()
        raise HTTPException(status_code=401, detail="Invalid refresh token")


@router.post("/logout")
def logout(
    request: Request,
    response: Response,
    body: Optional[LogoutRequest] = None,
    db: Session = Depends(get_db),
):
    """Revoke refresh token."""
    raw_refresh_token = (body.refresh_token if body else None) or request.cookies.get(
        settings.REFRESH_COOKIE_NAME
    )
    if not raw_refresh_token:
        _clear_auth_cookies(response)
        return {"message": "Logged out successfully"}
    token_hash = _hash_refresh_token(raw_refresh_token)
    db_token = (
        db.query(RefreshToken)
        .filter(
            RefreshToken.token.in_([token_hash, raw_refresh_token]),
            RefreshToken.revoked.is_(False),
        )
        .order_by(RefreshToken.created_at.desc())
        .first()
    )

    if not db_token:
        _clear_auth_cookies(response)
        return {"message": "Logged out successfully"}

    db_token.revoked = True
    db.commit()
    _clear_auth_cookies(response)
    return {"message": "Logged out successfully"}


@router.get("/me")
def get_me(current_user: User = Depends(get_current_user_from_auth_deps)):
    """Get current authenticated user's profile."""
    email = (
        current_user.secure_email
        if hasattr(current_user, "secure_email") and current_user.secure_email
        else current_user.email
    )
    return {
        "id": str(current_user.id),
        "phone_number": current_user.secure_phone or current_user.phone_number,
        "email": email,
        "name": current_user.name,
        "role": current_user.role,
        "status": current_user.status,
        "is_verified": current_user.is_verified,
        "mfa_enabled": bool(current_user.mfa_enabled),
        "profile_image_url": current_user.profile_image_url,
        "cargo_operator_profile": _cargo_operator_profile_payload(current_user),
    }


@router.put("/me/profile-image")
def update_profile_image(
    body: ProfileImageUpdateRequest,
    current_user: User = Depends(get_current_user_from_auth_deps),
    db: Session = Depends(get_db),
):
    """Persist or clear the authenticated user's profile image URL."""
    current_user.profile_image_url = body.profile_image_url
    db.add(current_user)
    db.commit()
    db.refresh(current_user)
    return {
        "id": str(current_user.id),
        "profile_image_url": current_user.profile_image_url,
        "message": "Profile image updated successfully",
    }
