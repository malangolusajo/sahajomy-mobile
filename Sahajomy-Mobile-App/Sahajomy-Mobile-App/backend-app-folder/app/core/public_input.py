"""Validation helpers for unauthenticated customer contact inputs."""

from app.core.validation import validate_and_format_phone


def normalize_public_name(value: str) -> str:
    """Normalize a human name and reject control characters or markup."""
    value = " ".join((value or "").split())
    if len(value) < 2 or len(value) > 150 or any(ord(char) < 32 for char in value):
        raise ValueError("Please provide your full name")
    # React escapes content, but values are also used in notification/email
    # paths. Rejecting markup protects future renderers as well.
    if "<" in value or ">" in value:
        raise ValueError("Name contains unsupported characters")
    return value


def normalize_public_whatsapp(value: str) -> str:
    """Return a validated, canonical E.164 WhatsApp number."""
    is_valid, formatted = validate_and_format_phone((value or "").strip())
    if not is_valid:
        raise ValueError("Please provide a valid WhatsApp number")
    return formatted
