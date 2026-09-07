"""
OTP Service Module for Sahajomy Platform
Handles OTP generation, storage, and verification
"""

import logging
import secrets
import string
from datetime import datetime, timedelta
from typing import Optional

from app.core.audit import log_action
from app.core.config import settings
from app.core.email_service import send_verification_email, validate_email
from app.core.encryption import data_encryption
from app.core.validation import validate_and_format_phone
from app.models.user import AuthProvider, OTPVerification, User
from fastapi import HTTPException, status
from sqlalchemy import or_
from sqlalchemy.orm import Session

OTP_INVALID_MESSAGE = "The code you entered is incorrect. Please try again."
OTP_EXPIRED_MESSAGE = "This OTP has expired. Please request a new code."
logger = logging.getLogger(__name__)


def generate_otp(length: int = 6) -> str:
    """Generate a random OTP code."""
    return "".join(secrets.choice(string.digits) for _ in range(length))


def check_rate_limit(
    phone_number: str, db: Session, max_requests: int = 3, time_window_minutes: int = 10
) -> bool:
    """
    Check if the phone number has exceeded the rate limit for OTP requests.

    Args:
        phone_number: User's phone number
        db: Database session
        max_requests: Maximum number of requests allowed in the time window
        time_window_minutes: Time window in minutes

    Returns:
        bool: True if within rate limit, False if exceeded
    """
    cutoff_time = datetime.utcnow() - timedelta(minutes=time_window_minutes)

    recent_requests = (
        db.query(OTPVerification)
        .filter(
            or_(
                OTPVerification.phone_hash == data_encryption.hash_phone(phone_number),
                OTPVerification.phone_number == phone_number,
            ),
            OTPVerification.created_at >= cutoff_time,
        )
        .count()
    )

    return recent_requests < max_requests


def send_otp_to_user(
    phone_number: str, name: Optional[str], email: Optional[str], db: Session
) -> dict:
    """
    Handle sending OTP to user based on whether they are new or existing.

    Args:
        phone_number: User's phone number
        name: User's name (for new users)
        email: User's email
        db: Database session

    Returns:
        dict: Response message
    """
    # Validate and format phone number
    is_valid_phone, formatted_phone = validate_and_format_phone(phone_number)
    if not is_valid_phone:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                "Invalid phone number format. Please provide a valid phone "
                "number with country code."
            ),
        )

    # Use formatted phone number for all operations
    phone_number = formatted_phone

    # Rate limiting check - use phone hash for rate limiting as well
    phone_hash = data_encryption.hash_phone(phone_number)

    if not check_rate_limit(phone_number, db):
        logger.warning(
            "security_otp_rate_limit_exceeded",
            extra={
                "extra_data": {
                    "security_event": "otp_abuse",
                    "phone_hash_prefix": phone_hash[:12],
                }
            },
        )
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many OTP requests. Please wait before trying again.",
        )

    # Look up user by phone hash first (new secure method)
    user = db.query(User).filter(User.phone_hash == phone_hash).first()

    # If not found by hash, try plain text phone (backward compatibility)
    if not user:
        user = db.query(User).filter(User.phone_number == phone_number).first()
        # If found via plain text, migrate to encrypted fields
        if user and user.phone_number and not user.phone_hash:
            user.phone_encrypted = data_encryption.encrypt_phone(user.phone_number)
            user.phone_hash = data_encryption.hash_phone(user.phone_number)
            db.commit()
            db.refresh(user)

    # If user exists but they're providing name/email, it's an error
    if user and name:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                "Unable to process registration details. Please use the sign-in "
                "flow for existing accounts."
            ),
        )

    if not user:
        # New user registration - require name and email
        if not name or not email:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Name and email are required for new user registration.",
            )

        # Validate email format
        if not validate_email(email):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=(
                    "Invalid email format or disposable email address. Please "
                    "provide a valid email address."
                ),
            )

        # Check for duplicate email using hash (secure method)
        email_hash = data_encryption.hash_email(email)
        existing_user_by_email = (
            db.query(User).filter(User.email_hash == email_hash).first()
        )

        # Backward compatibility: also check plain text email
        if not existing_user_by_email:
            existing_user_by_email = db.query(User).filter(User.email == email).first()
            # If found via plain text, migrate to encrypted fields
            if (
                existing_user_by_email
                and existing_user_by_email.email
                and not existing_user_by_email.email_hash
            ):
                existing_user_by_email.email_encrypted = data_encryption.encrypt_email(
                    existing_user_by_email.email
                )
                existing_user_by_email.email_hash = data_encryption.hash_email(
                    existing_user_by_email.email
                )
                db.commit()
                db.refresh(existing_user_by_email)

        if existing_user_by_email:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=(
                    "Unable to use this email for registration. Please sign in "
                    "or use a different email."
                ),
            )

        # Create new user with encrypted fields
        user = User(
            phone_encrypted=data_encryption.encrypt_phone(phone_number),
            phone_hash=phone_hash,
            name=name,
            email_encrypted=data_encryption.encrypt_email(email),
            email_hash=email_hash,
            auth_provider=AuthProvider.OTP,
            is_active=True,
            is_verified=False,
            is_admin=False,
            role="customer",  # Default role for new users
        )
        db.add(user)
        db.commit()
        db.refresh(user)

        # Log new user registration
        log_action(
            db=db,
            action="USER_REGISTERED",
            user_id=user.id,
            entity_type="user",
            entity_id=user.id,
            metadata={
                "phone_number": data_encryption.mask_phone(phone_number),
                "email": data_encryption.mask_email(email),
                "registration_method": "otp",
            },
        )

    # If user exists but doesn't have an email, they need to provide it
    elif not user.email and not user.email_encrypted:
        if not email:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=(
                    "Email is required for this user. Please provide your email "
                    "to continue."
                ),
            )
        # Validate email format
        if not validate_email(email):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid email format."
            )
        # Check for duplicate email using hash
        email_hash = data_encryption.hash_email(email)
        existing_user_by_email = (
            db.query(User).filter(User.email_hash == email_hash).first()
        )

        # Backward compatibility check
        if not existing_user_by_email:
            existing_user_by_email = db.query(User).filter(User.email == email).first()
            if (
                existing_user_by_email
                and existing_user_by_email.email
                and not existing_user_by_email.email_hash
            ):
                existing_user_by_email.email_encrypted = data_encryption.encrypt_email(
                    existing_user_by_email.email
                )
                existing_user_by_email.email_hash = data_encryption.hash_email(
                    existing_user_by_email.email
                )
                db.commit()
                db.refresh(existing_user_by_email)

        if existing_user_by_email and existing_user_by_email.id != user.id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=(
                    "Unable to use this email for registration. Please sign in "
                    "or use a different email."
                ),
            )
        # Update the user's email with encrypted fields
        user.email_encrypted = data_encryption.encrypt_email(email)
        user.email_hash = email_hash
        db.commit()
        db.refresh(user)

    # Removed status check here to allow suspended users to receive OTPs
    # The verification will handle the suspended status check

    otp_code = generate_otp()
    expires_at = datetime.utcnow() + timedelta(minutes=settings.OTP_EXPIRE_MINUTES)

    otp_record = OTPVerification(
        phone_hash=phone_hash,
        user_id=user.id,
        otp_code_hash=data_encryption.hash_otp(phone_number, otp_code),
        expires_at=expires_at,
        verified=False,
    )
    db.add(otp_record)
    db.commit()

    # Ensure user has an email before attempting to send
    # Check both plain text and encrypted email fields
    user_email = user.secure_email or user.email
    if not user_email:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="User does not have an email address associated with their account.",
        )

    # Send OTP via email
    email_sent = send_verification_email(
        recipient_email=user_email,
        recipient_name=user.name or "User",
        otp_code=otp_code,
    )

    if not email_sent:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=(
                "Failed to send OTP via email. Please verify your email "
                "settings or try again later."
            ),
        )

    # Log OTP request
    log_action(
        db=db,
        action="OTP_REQUESTED",
        user_id=user.id,
        entity_type="user",
        entity_id=user.id,
        metadata={
            "phone_number": data_encryption.mask_phone(phone_number),
            "email": data_encryption.mask_email(user_email),
        },
    )

    return {
        "message": "OTP sent successfully via email",
        "expires_in_minutes": settings.OTP_EXPIRE_MINUTES,
        "masked_email": data_encryption.mask_email(user_email),
    }


def verify_otp(
    phone_number: str, otp_code: str, db: Session
) -> tuple[bool, Optional[User], Optional[str]]:
    """
    Verify OTP code and return user info if successful.

    Args:
        phone_number: User's phone number
        otp_code: OTP code to verify
        db: Database session

    Returns:
        tuple: (success, user, error_message)
    """
    from sqlalchemy import desc

    # Normalize to E.164 so the lookup matches the format used when the OTP
    # record was stored by send_otp_to_user (users may type local formats).
    is_valid_phone, formatted_phone = validate_and_format_phone(phone_number)
    if not is_valid_phone:
        return False, None, OTP_INVALID_MESSAGE
    phone_number = formatted_phone

    phone_hash = data_encryption.hash_phone(phone_number)
    otp_hash = data_encryption.hash_otp(phone_number, otp_code)

    # New OTPs are keyed hashes. The plaintext branch supports only records
    # created before this migration and naturally disappears as they expire.
    otp_record = (
        db.query(OTPVerification)
        .filter(
            OTPVerification.phone_hash == phone_hash,
            OTPVerification.otp_code_hash == otp_hash,
            OTPVerification.verified.is_(False),
        )
        .order_by(desc(OTPVerification.created_at))  # Get the most recent one
        .first()
    )

    if not otp_record:
        otp_record = (
            db.query(OTPVerification)
            .filter(
                OTPVerification.phone_number == phone_number,
                OTPVerification.otp_code == otp_code,
                OTPVerification.verified.is_(False),
            )
            .order_by(desc(OTPVerification.created_at))
            .first()
        )

    if not otp_record:
        return False, None, OTP_INVALID_MESSAGE

    if otp_record.expires_at <= datetime.utcnow():
        return False, None, OTP_EXPIRED_MESSAGE

    # Mark OTP as verified immediately to prevent reuse
    otp_record.verified = True
    db.add(otp_record)

    # Get the user associated with this OTP
    user = db.query(User).filter(User.id == otp_record.user_id).first()
    if not user:
        # This should not happen if OTP was created correctly with a user_id.
        return False, None, "User not found associated with this OTP"

    if user.status == "suspended":
        return False, None, "Account suspended. Contact support."

    # Update user verification status
    user.is_verified = True
    db.commit()

    # Log successful OTP verification
    log_action(
        db=db,
        action="OTP_VERIFIED",
        user_id=user.id,
        entity_type="user",
        entity_id=user.id,
        metadata={"phone_number": data_encryption.mask_phone(phone_number)},
    )

    return True, user, None
