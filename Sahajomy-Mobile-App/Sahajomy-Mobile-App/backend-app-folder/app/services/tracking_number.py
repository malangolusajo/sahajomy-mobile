from __future__ import annotations

import uuid
import zlib
from uuid import UUID


def _serial_from_key(key: str) -> str:
    value = zlib.crc32(key.encode("utf-8")) % 1_000_000
    return f"{value:06d}"


def _normalize_region(region: str | None) -> str:
    token = (region or "DAR").strip().upper()
    compact = "".join(ch for ch in token if ch.isalnum())
    if not compact:
        return "DAR"
    return compact[:3].ljust(3, "X")


def build_tracking_number(
    cargo_type: str, region: str | None, entity_id: UUID | str
) -> str:
    mode = "AIR" if str(cargo_type).upper() == "AIR" else "SEA"
    region_code = _normalize_region(region)
    serial = _serial_from_key(str(entity_id))
    return f"SJ-{mode}-{region_code}-{serial}"


def generate_unique_tracking_number(
    db,
    cargo_type: str,
    region: str | None,
    entity_id: UUID | str,
    max_attempts: int = 20,
) -> str:
    from app.models.air_cargo import ExpressAirCargoBooking
    from app.models.cargo_customs import ManualCargoIntake
    from app.models.shipment_orders import ShipmentOrder

    mode = "AIR" if str(cargo_type).upper() == "AIR" else "SEA"
    region_code = _normalize_region(region)
    base_key = str(entity_id)

    for attempt in range(max_attempts):
        serial = _serial_from_key(f"{base_key}:{attempt}")
        candidate = f"SJ-{mode}-{region_code}-{serial}"

        exists_air = (
            db.query(ExpressAirCargoBooking.id)
            .filter(ExpressAirCargoBooking.tracking_number == candidate)
            .first()
        )
        exists_order = (
            db.query(ShipmentOrder.id)
            .filter(ShipmentOrder.tracking_number == candidate)
            .first()
        )
        exists_manual_intake = (
            db.query(ManualCargoIntake.id)
            .filter(ManualCargoIntake.tracking_number == candidate)
            .first()
        )
        if not exists_air and not exists_order and not exists_manual_intake:
            return candidate

    raise ValueError("Unable to generate a unique tracking number")


def ensure_manual_intake_tracking_number(db, intake) -> str:
    """Assign the intake's immutable Sahajomy number exactly once."""
    if intake.tracking_number:
        return intake.tracking_number
    if not intake.id:
        intake.id = uuid.uuid4()
    intake.tracking_number = generate_unique_tracking_number(
        db,
        intake.cargo_type,
        intake.destination_city or intake.destination_country,
        intake.id,
    )
    return intake.tracking_number
