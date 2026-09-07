"""Stable display/reference IDs for logistics entities.

These helpers intentionally do not replace database UUIDs.  They generate
human-readable references from existing UUIDs and dates so legacy IDs, primary
keys, relationships, URLs, and API payloads remain backwards compatible.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

REFERENCE_PREFIXES = {
    "shipment_order": "SHP",
    "booking": "AIR",
    "air_booking": "AIR",
    "express_air_cargo_booking": "AIR",
    "sea_booking": "SEA",
    "container": "CNT",
    "sourcing_order": "ORD-TZ",
    "order": "ORD-TZ",
    "warehouse": "WH",
    "notification": "NTF",
    "invoice": "INV",
    "payment": "PAY",
    "batch": "BAT",
    "packing_list": "PL",
    "manual_cargo_intake": "MCI",
}


def _coerce_datetime(value: Any | None) -> datetime:
    if isinstance(value, datetime):
        return value
    if isinstance(value, str):
        try:
            return datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            pass
    return datetime.utcnow()


def _short_uuid(value: Any) -> str:
    raw = str(value or "").strip()
    try:
        raw = str(UUID(raw))
    except (ValueError, AttributeError, TypeError):
        pass
    compact = raw.replace("-", "").upper()
    return compact[:8] if compact else "UNKNOWN"


def get_reference_prefix(entity_type: str | None) -> str:
    """Return the professional reference prefix for a known logistics entity."""
    return REFERENCE_PREFIXES.get(str(entity_type or "").lower(), "REF")


def build_display_reference(
    entity_type: str | None,
    entity_id: Any,
    created_at: Any | None = None,
) -> str:
    """Build a stable, searchable display reference without changing storage IDs.

    Format: ``PREFIX-YYYY-UUID8`` (for example ``SHP-2026-0A1B2C3D``).
    The suffix is derived from the existing UUID, making the reference safe for
    old production records without migrations or sequence backfills.
    """
    year = _coerce_datetime(created_at).year
    return f"{get_reference_prefix(entity_type)}-{year}-{_short_uuid(entity_id)}"
