"""Helpers for building public-facing application URLs."""

from app.core.config import settings


def build_public_url(path: str) -> str:
    safe_path = path if str(path).startswith("/") else f"/{path}"
    return f"{settings.public_app_url}{safe_path}"


def build_shared_batch_link(token: str) -> str:
    return build_public_url(f"/shared/{token}")
