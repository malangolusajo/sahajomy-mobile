"""Single, guarded implementation for proxying private generated documents."""

from __future__ import annotations

import os
import re
from datetime import datetime
from typing import Iterable
from urllib.parse import urlparse

import cloudinary.utils
from app.core.cloudinary import configure_cloudinary
from app.core.config import settings
from app.core.safe_remote import MAX_REMOTE_DOCUMENT_BYTES, fetch_public_bytes
from fastapi import HTTPException
from fastapi.responses import StreamingResponse


def _allowed_document_hosts() -> set[str]:
    hosts = {"cloudinary.com", "sahajomy.co.tz"}
    app_host = (urlparse(settings.public_app_url).hostname or "").lower()
    if app_host:
        hosts.add(app_host)
    return hosts


def _private_download_url(document_url: str) -> str | None:
    parsed = urlparse(document_url)
    host = (parsed.hostname or "").lower()
    if host != "cloudinary.com" and not host.endswith(".cloudinary.com"):
        return None

    parts = [part for part in parsed.path.split("/") if part]
    resource_index = next(
        (
            index
            for index, part in enumerate(parts)
            if part in {"image", "video", "raw"}
        ),
        None,
    )
    if resource_index is None or len(parts) <= resource_index + 3:
        return None
    version_index = next(
        (
            index
            for index in range(resource_index + 2, len(parts))
            if re.fullmatch(r"v\d+", parts[index])
        ),
        None,
    )
    if version_index is None or version_index >= len(parts) - 1:
        return None

    public_id_with_ext = "/".join(parts[version_index + 1 :])
    if "." not in public_id_with_ext:
        return None
    _, file_format = public_id_with_ext.rsplit(".", 1)
    configure_cloudinary()
    try:
        return cloudinary.utils.private_download_url(
            public_id_with_ext,
            file_format,
            resource_type=parts[resource_index],
            type=parts[resource_index + 1],
            attachment=False,
            expires_at=int(datetime.utcnow().timestamp()) + 600,
        )
    except Exception:
        return None


def _fetch_candidates(document_url: str) -> Iterable[str]:
    raw_url = (document_url or "").strip()
    if not raw_url:
        return []
    candidates = [raw_url]
    parsed = urlparse(raw_url)
    parts = [part for part in parsed.path.split("/") if part]
    if len(parts) >= 4:
        first, second, repeated, filename = parts[-4:]
        if repeated == first and filename.startswith(f"{second}_"):
            repaired = parsed._replace(
                path="/" + "/".join(parts[:-2] + [filename])
            ).geturl()
            candidates.append(repaired)
    signed_url = _private_download_url(raw_url)
    if signed_url and signed_url not in candidates:
        candidates.append(signed_url)
    return candidates


def stream_safe_document(
    document_url: str, filename: str, *, inline: bool = False
) -> StreamingResponse:
    """Download only public, permitted PDF hosts with bounded data and no unsafe redirects."""
    candidates = _fetch_candidates(document_url)
    if not candidates:
        raise HTTPException(status_code=400, detail="Invalid document URL")

    last_error: Exception | None = None
    for candidate in candidates:
        try:
            content, content_type = fetch_public_bytes(
                candidate,
                max_bytes=MAX_REMOTE_DOCUMENT_BYTES,
                allowed_host_suffixes=_allowed_document_hosts(),
                allowed_content_prefixes=(
                    "application/pdf",
                    "application/octet-stream",
                ),
                timeout_seconds=20.0,
            )
            # Treat unknown binary content as a download, never as browser-rendered HTML.
            media_type = (
                "application/pdf"
                if content_type == "application/pdf"
                else "application/octet-stream"
            )
            safe_filename = (
                os.path.basename(filename).replace('"', "") or "document.pdf"
            )
            return StreamingResponse(
                iter([content]),
                media_type=media_type,
                headers={
                    "Content-Disposition": f'{"inline" if inline else "attachment"}; filename="{safe_filename}"'
                },
            )
        except Exception as exc:
            last_error = exc

    if isinstance(last_error, ValueError):
        raise HTTPException(
            status_code=400, detail="Document is not accessible"
        ) from last_error
    raise HTTPException(
        status_code=404, detail="Document is not accessible"
    ) from last_error
