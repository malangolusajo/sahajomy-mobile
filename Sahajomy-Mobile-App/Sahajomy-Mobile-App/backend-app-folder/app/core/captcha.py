"""Optional Cloudflare Turnstile verification for public conversion forms."""

import httpx
from app.core.config import settings
from fastapi import HTTPException, status


def verify_agizisha_captcha(token: str | None, remote_ip: str | None) -> None:
    """Verify a Turnstile token when the feature is enabled.

    The feature intentionally fails closed: enabling it without a configured
    secret or without a browser-issued token blocks public submissions.
    """
    if not settings.AGIZISHA_CAPTCHA_REQUIRED:
        return

    if not token:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Verification is required before submitting an order",
        )
    if not settings.AGIZISHA_TURNSTILE_SECRET_KEY:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Order verification is temporarily unavailable",
        )

    try:
        response = httpx.post(
            "https://challenges.cloudflare.com/turnstile/v0/siteverify",
            data={
                "secret": settings.AGIZISHA_TURNSTILE_SECRET_KEY,
                "response": token,
                "remoteip": remote_ip or "",
            },
            timeout=5.0,
        )
        verified = response.is_success and bool(response.json().get("success"))
    except (httpx.HTTPError, ValueError):
        verified = False

    if not verified:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Verification failed. Please try again.",
        )
