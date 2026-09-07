"""Validation helpers for uploaded image bytes."""

from app.core.config import settings
from app.core.malware_scan import scan_upload_bytes
from fastapi import HTTPException

_IMAGE_TYPES = {
    "jpeg": ("image/jpeg", "jpg"),
    "png": ("image/png", "png"),
    "webp": ("image/webp", "webp"),
    "gif": ("image/gif", "gif"),
}


def _detect_image_type(content: bytes) -> str | None:
    """Identify supported image formats from their standardized signatures."""
    if content.startswith(b"\xff\xd8\xff"):
        return "jpeg"
    if content.startswith(b"\x89PNG\r\n\x1a\n"):
        return "png"
    if content.startswith((b"GIF87a", b"GIF89a")):
        return "gif"
    if len(content) >= 12 and content[:4] == b"RIFF" and content[8:12] == b"WEBP":
        return "webp"
    return None


def validated_image_format(
    content: bytes, declared_type: str, *, allow_gif: bool = False
) -> tuple[str, str]:
    """Verify image bytes rather than trusting a browser-provided MIME type."""
    scan_upload_bytes(content)
    detected = _detect_image_type(content)
    allowed = set(settings.ALLOWED_IMAGE_TYPES)
    if allow_gif:
        allowed.add("image/gif")
    if detected not in _IMAGE_TYPES:
        raise HTTPException(
            status_code=400, detail="Uploaded file is not a supported image."
        )
    media_type, extension = _IMAGE_TYPES[detected]
    if media_type not in allowed or declared_type != media_type:
        raise HTTPException(
            status_code=400,
            detail="Image content does not match the declared file type.",
        )
    return media_type, extension
