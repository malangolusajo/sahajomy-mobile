# app/models/error.py
"""
Error response models for API endpoints.
"""

from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, ConfigDict


class ErrorResponse(BaseModel):
    """Standard error response format."""

    success: bool = False
    message: str
    error_code: Optional[str] = None
    reference_id: Optional[str] = None
    timestamp: Optional[datetime] = None
    details: Optional[Any] = None

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "success": False,
                "message": "Invalid phone number format",
                "error_code": "invalid_phone",
                "reference_id": "a3f5g7h2",
                "timestamp": "2024-01-15T10:30:45.123Z",
            }
        }
    )
