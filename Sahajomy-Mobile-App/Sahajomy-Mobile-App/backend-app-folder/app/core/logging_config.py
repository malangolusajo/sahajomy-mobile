"""
Centralized logging configuration for production environments.
This module provides structured logging with JSON formatting for easy parsing and monitoring.
"""

import json
import logging
import logging.handlers
import os
import sys
from datetime import datetime
from typing import Any, Dict

# Ensure log directory exists
LOG_DIR = os.getenv("LOG_DIR", "/app/logs")
os.makedirs(LOG_DIR, exist_ok=True)


class JSONFormatter(logging.Formatter):
    """Custom formatter that outputs log records as JSON."""

    def format(self, record: logging.LogRecord) -> str:
        # Create the base log record
        log_entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }

        # Add exception info if present
        if record.exc_info:
            log_entry["exception"] = self.formatException(record.exc_info)

        # Add extra fields if present
        if hasattr(record, "extra_data"):
            log_entry.update(record.extra_data)

        return json.dumps(log_entry, default=str)


def setup_logging(log_level: str = "WARNING") -> None:
    """
    Configure logging for the application.

    Args:
        log_level: Logging level ('DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL')
    """
    # Convert string level to logging constant
    level = getattr(logging, log_level.upper(), logging.WARNING)

    # Create formatters
    json_formatter = JSONFormatter()
    simple_formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )

    # Root logger configuration
    root_logger = logging.getLogger()
    root_logger.setLevel(level)

    # Clear any existing handlers
    root_logger.handlers.clear()

    # Console handler (for development and container logs)
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(level)
    console_handler.setFormatter(
        json_formatter if os.getenv("ENVIRONMENT") == "production" else simple_formatter
    )
    root_logger.addHandler(console_handler)

    # File handler for errors (rotates daily, keeps 30 days)
    error_handler = logging.handlers.TimedRotatingFileHandler(
        filename=os.path.join(LOG_DIR, "errors.log"),
        when="midnight",
        interval=1,
        backupCount=30,
        encoding="utf-8",
    )
    error_handler.setLevel(logging.WARNING)  # Only warnings and above
    error_handler.setFormatter(json_formatter)
    root_logger.addHandler(error_handler)

    # File handler for all logs (rotates daily, keeps 7 days)
    all_handler = logging.handlers.TimedRotatingFileHandler(
        filename=os.path.join(LOG_DIR, "application.log"),
        when="midnight",
        interval=1,
        backupCount=7,
        encoding="utf-8",
    )
    all_handler.setLevel(level)
    all_handler.setFormatter(json_formatter)
    root_logger.addHandler(all_handler)


def log_error(
    message: str,
    error_code: str = None,
    reference_id: str = None,
    details: Dict[str, Any] = None,
    **kwargs
) -> str:
    """
    Log an error with structured data and return a reference ID.

    Args:
        message: Error message
        error_code: Custom error code for categorization
        reference_id: Existing reference ID or generate new one
        details: Additional structured data to log
        **kwargs: Additional key-value pairs to include in log

    Returns:
        reference_id: The reference ID for this error
    """
    import uuid

    if not reference_id:
        reference_id = str(uuid.uuid4())[:8]

    extra_data = {
        "reference_id": reference_id,
        "error_code": error_code,
    }

    if details:
        extra_data["details"] = details

    if kwargs:
        extra_data.update(kwargs)

    # Create a custom log record with extra data
    logger = logging.getLogger(__name__)
    logger.warning(message, extra={"extra_data": extra_data})

    return reference_id


# Initialize logging based on environment
if __name__ == "__main__":
    # This will be called when the module is imported
    log_level = os.getenv("LOG_LEVEL", "WARNING")
    setup_logging(log_level)
