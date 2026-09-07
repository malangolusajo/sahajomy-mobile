from __future__ import annotations

import hmac
import ipaddress
import logging
import time
from typing import Dict, Tuple

from app.core.config import settings
from app.core.redis import redis_client
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response

logger = logging.getLogger(__name__)


def _client_ip(request: Request) -> str:
    peer = request.client.host if request.client else "unknown"
    try:
        trusted = any(
            ipaddress.ip_address(peer) in ipaddress.ip_network(cidr)
            for cidr in settings.TRUSTED_PROXY_CIDRS
        )
    except ValueError:
        trusted = False
    if trusted:
        forwarded = request.headers.get("x-forwarded-for", "").split(",", 1)[0].strip()
        try:
            return str(ipaddress.ip_address(forwarded)) if forwarded else peer
        except ValueError:
            return peer
    return peer


class CSRFMiddleware(BaseHTTPMiddleware):
    """Double-submit protection for browser requests authenticated by cookies."""

    SAFE_METHODS = {"GET", "HEAD", "OPTIONS", "TRACE"}
    LOGIN_PATHS = {"/api/v1/auth/send-otp", "/api/v1/auth/verify-otp"}

    async def dispatch(self, request: Request, call_next):
        uses_cookie_auth = bool(
            request.cookies.get(settings.ACCESS_COOKIE_NAME)
            or request.cookies.get(settings.REFRESH_COOKIE_NAME)
        ) and not request.headers.get("authorization", "").lower().startswith("bearer ")
        if (
            request.method not in self.SAFE_METHODS
            and request.url.path not in self.LOGIN_PATHS
            and uses_cookie_auth
        ):
            cookie_token = request.cookies.get(settings.CSRF_COOKIE_NAME, "")
            header_token = request.headers.get("x-csrf-token", "")
            if not cookie_token or not hmac.compare_digest(cookie_token, header_token):
                logger.warning(
                    "security_csrf_rejected",
                    extra={
                        "extra_data": {
                            "security_event": "csrf_rejected",
                            "client_ip": _client_ip(request),
                            "path": request.url.path,
                        }
                    },
                )
                return Response(status_code=403, content="CSRF validation failed.")
        return await call_next(request)


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        response: Response = await call_next(request)

        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("X-Frame-Options", "DENY")
        response.headers.setdefault("Referrer-Policy", "no-referrer")
        response.headers.setdefault(
            "Content-Security-Policy",
            "default-src 'self'; base-uri 'self'; frame-ancestors 'none'; "
            "object-src 'none'; form-action 'self';",
        )
        response.headers.setdefault(
            # Warehouse scanning uses the camera only from Sahajomy's own UI.
            "Permissions-Policy",
            "camera=(self), microphone=(), geolocation=()",
        )

        if settings.ENVIRONMENT == "production":
            response.headers.setdefault(
                "Strict-Transport-Security", "max-age=31536000; includeSubDomains"
            )

        return response


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Simple rate limiter for sensitive endpoints.

    Uses Redis if available, falls back to in-memory counters (per process).
    """

    def __init__(self, app, limits: Dict[str, Tuple[int, int]]):
        super().__init__(app)
        self.limits = limits
        self.local_counters: Dict[str, Tuple[int, float]] = {}

    async def dispatch(self, request: Request, call_next):
        path = request.url.path
        matched = None
        for prefix, rule in self.limits.items():
            if path.startswith(prefix):
                matched = rule
                break

        if not matched:
            return await call_next(request)

        limit, window = matched
        client_ip = _client_ip(request)
        key = f"rl:{client_ip}:{path}"

        if redis_client:
            current = await redis_client.incr(key)
            if current == 1:
                await redis_client.expire(key, window)
            if current > limit:
                logger.warning(
                    "security_rate_limit_exceeded",
                    extra={
                        "extra_data": {
                            "security_event": "rate_limit",
                            "client_ip": client_ip,
                            "path": path,
                        }
                    },
                )
                return Response(
                    status_code=429, content="Too many requests. Please slow down."
                )
        else:
            count, expires_at = self.local_counters.get(key, (0, 0))
            now = time.time()
            if now > expires_at:
                count = 0
                expires_at = now + window
            count += 1
            self.local_counters[key] = (count, expires_at)
            if count > limit:
                logger.warning(
                    "security_rate_limit_exceeded",
                    extra={
                        "extra_data": {
                            "security_event": "rate_limit",
                            "client_ip": client_ip,
                            "path": path,
                        }
                    },
                )
                return Response(
                    status_code=429, content="Too many requests. Please slow down."
                )

        return await call_next(request)
