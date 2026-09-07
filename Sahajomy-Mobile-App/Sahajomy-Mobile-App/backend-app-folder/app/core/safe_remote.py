"""Guarded outbound HTTP helpers for user-controlled remote URLs."""

from __future__ import annotations

import ipaddress
import socket
from typing import Iterable, Optional
from urllib.parse import urlparse

import httpx

MAX_REMOTE_IMAGE_BYTES = 10 * 1024 * 1024
MAX_REMOTE_DOCUMENT_BYTES = 20 * 1024 * 1024


def _host_is_allowed(host: str, allowed_host_suffixes: Optional[Iterable[str]]) -> bool:
    if not allowed_host_suffixes:
        return True
    normalized = host.lower().rstrip(".")
    return any(
        normalized == suffix.lower().rstrip(".")
        or normalized.endswith(f".{suffix.lower().rstrip('.')}")
        for suffix in allowed_host_suffixes
    )


def validate_public_http_url(
    raw_url: str, *, allowed_host_suffixes: Optional[Iterable[str]] = None
) -> str:
    """Return a safe public HTTP(S) URL or raise ValueError.

    DNS is resolved before every request (including redirects) and every
    resolved address must be globally routable. This blocks loopback, private,
    link-local, multicast, and non-public-address SSRF targets.
    """
    parsed = urlparse((raw_url or "").strip())
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        raise ValueError("Only absolute HTTP(S) URLs are allowed")
    if parsed.username or parsed.password:
        raise ValueError("URLs containing credentials are not allowed")
    if not _host_is_allowed(parsed.hostname, allowed_host_suffixes):
        raise ValueError("The URL host is not allowed")

    try:
        addresses = {info[4][0] for info in socket.getaddrinfo(parsed.hostname, None)}
    except socket.gaierror as exc:
        raise ValueError("The URL host could not be resolved") from exc

    if not addresses:
        raise ValueError("The URL host could not be resolved")
    for address in addresses:
        try:
            address_value = ipaddress.ip_address(address)
        except ValueError as exc:
            raise ValueError("The URL host resolved to an invalid address") from exc
        if not address_value.is_global:
            raise ValueError("The URL must resolve to a public address")
    return parsed.geturl()


def fetch_public_bytes(
    raw_url: str,
    *,
    max_bytes: int,
    allowed_host_suffixes: Optional[Iterable[str]] = None,
    allowed_content_prefixes: Optional[tuple[str, ...]] = None,
    timeout_seconds: float = 10.0,
    max_redirects: int = 3,
    user_agent: str = "Sahajomy-Remote-Fetcher/1.0",
) -> tuple[bytes, str]:
    """Fetch a bounded public resource while validating every redirect."""
    current_url = raw_url
    with httpx.Client(timeout=timeout_seconds, follow_redirects=False) as client:
        for _ in range(max_redirects + 1):
            safe_url = validate_public_http_url(
                current_url, allowed_host_suffixes=allowed_host_suffixes
            )
            with client.stream(
                "GET", safe_url, headers={"User-Agent": user_agent}
            ) as response:
                if response.is_redirect:
                    location = response.headers.get("location")
                    if not location:
                        raise ValueError("Remote server returned an invalid redirect")
                    current_url = str(response.url.join(location))
                    continue
                response.raise_for_status()

                content_type = (
                    response.headers.get("content-type", "").split(";", 1)[0].lower()
                )
                if allowed_content_prefixes and not any(
                    content_type.startswith(prefix)
                    for prefix in allowed_content_prefixes
                ):
                    raise ValueError("Remote resource has an unsupported content type")

                declared_length = response.headers.get("content-length")
                if declared_length and int(declared_length) > max_bytes:
                    raise ValueError("Remote resource is too large")

                chunks: list[bytes] = []
                total = 0
                for chunk in response.iter_bytes():
                    total += len(chunk)
                    if total > max_bytes:
                        raise ValueError("Remote resource is too large")
                    chunks.append(chunk)
                return b"".join(chunks), content_type

    raise ValueError("Too many redirects while fetching remote resource")
