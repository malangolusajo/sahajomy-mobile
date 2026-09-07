# app/core/error_handlers.py
"""
Consistent error handling utilities for API endpoints.
"""

import logging
import uuid
from datetime import datetime
from typing import Any, Dict, Optional

from app.core.logging_config import log_error
from fastapi import HTTPException, status

logger = logging.getLogger(__name__)


def raise_error(
    status_code: int,
    message: str,
    error_code: Optional[str] = None,
    details: Optional[Any] = None,
    path: Optional[str] = None,
    method: Optional[str] = None,
) -> None:
    """
    Raise consistent HTTP exceptions with tracking info.

    Args:
        status_code: HTTP status code (400, 403, 404, etc.)
        message: User-friendly error message
        error_code: Optional custom error code for frontend handling
        details: Optional additional error details (for logging only)
        path: Request path for context
        method: HTTP method for context

    Raises:
        HTTPException: With consistent format
    """
    reference_id = str(uuid.uuid4())[:8]

    # Log the error internally with structured data
    log_error(
        message=message,
        error_code=error_code or f"http_{status_code}",
        reference_id=reference_id,
        details=details,
        path=path,
        method=method,
        status_code=status_code,
    )

    # Raise HTTP exception with just the message
    # The global exception handler will format it consistently
    raise HTTPException(status_code=status_code, detail=message)


def create_error_response(
    message: str,
    error_code: Optional[str] = None,
    reference_id: Optional[str] = None,
    status_code: int = 400,
    path: Optional[str] = None,
    method: Optional[str] = None,
) -> Dict:
    """
    Create a consistent error response dictionary.

    Use this when you need to return an error without raising an exception.
    """
    if not reference_id:
        reference_id = str(uuid.uuid4())[:8]

    # Log the error even when returning a response
    log_error(
        message=message,
        error_code=error_code or f"error_{status_code}",
        reference_id=reference_id,
        path=path,
        method=method,
        status_code=status_code,
    )

    return {
        "success": False,
        "message": message,
        "error_code": error_code or f"error_{status_code}",
        "reference_id": reference_id,
        "timestamp": datetime.utcnow().isoformat(),
    }


class APIError(Exception):
    """Custom exception for API errors that should be shown to users."""

    def __init__(
        self, message: str, status_code: int = 400, error_code: Optional[str] = None
    ):
        self.message = message
        self.status_code = status_code
        self.error_code = error_code
        super().__init__(self.message)
