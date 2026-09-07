"""Service helpers for shipping mark generation and printable labels."""

from __future__ import annotations

from typing import Iterable, Optional

from app.models.shipping_mark import ShippingMark
from app.services.tracking import TrackingService  # NEW: Import tracking service
from sqlalchemy.orm import Session


def destination_region_code(region: str) -> str:
    normalized = (region or "UNK").strip().upper()
    letters = "".join(ch for ch in normalized if ch.isalpha())
    if len(letters) >= 3:
        return letters[:3]
    return (letters + "XXX")[:3]


def generate_shipping_mark_code(
    cargo_type: str, destination_region: str, booking_id: str
) -> str:
    type_prefix = "AIR" if cargo_type.upper() == "AIR" else "SEA"
    region_code = destination_region_code(destination_region)
    numeric_only = "".join(ch for ch in str(booking_id) if ch.isdigit())
    serial = int(numeric_only[-6:] or 0)
    return f"SJ-{type_prefix}-{region_code}-{serial:06d}"


def generate_qr_payload(booking_id: str, cargo_type: str = "BOOKING") -> str:
    """Return a stable, scanner-readable platform booking reference."""
    return f"SAHAJOMY:{cargo_type.strip().upper()}:{booking_id}"


def create_shipping_mark(
    db: Session,
    *,
    booking_id,
    cargo_type: str,
    customer_name: Optional[str],
    customer_phone: Optional[str],
    destination_region: str,
    packing_list_summary: Optional[str],
    carton_count: int,
    air_booking_id=None,
    sea_booking_id=None,
) -> ShippingMark:
    existing = (
        db.query(ShippingMark)
        .filter(
            ShippingMark.booking_id == booking_id,
            ShippingMark.cargo_type == cargo_type,
        )
        .first()
    )
    if existing:
        return existing

    code = generate_shipping_mark_code(cargo_type, destination_region, str(booking_id))
    mark = ShippingMark(
        booking_id=booking_id,
        shipping_mark_code=code,
        cargo_type=cargo_type,
        customer_name=customer_name,
        customer_phone=customer_phone,
        destination_region=destination_region,
        packing_list_summary=packing_list_summary,
        carton_count=max(carton_count or 1, 1),
        air_booking_id=air_booking_id,
        sea_booking_id=sea_booking_id,
    )
    db.add(mark)
    db.flush()

    # NEW: Create tracking event for shipping mark creation
    TrackingService.create_tracking_event(
        db,
        entity_type="shipping_mark",
        entity_id=str(mark.id),
        event_type="shipping_mark_created",
        description=f"Shipping mark {code} created for {'air' if air_booking_id else 'sea'} cargo",
        extra_data={
            "booking_id": str(booking_id),
            "cargo_type": cargo_type,
            "destination_region": destination_region,
            "carton_count": carton_count,
        },
    )

    return mark


def build_printable_label(
    mark: ShippingMark, issuer_name: Optional[str] = None
) -> dict:
    qr_payload = generate_qr_payload(str(mark.booking_id), mark.cargo_type)
    labels = [
        {
            "label_index": idx,
            "label_total": mark.carton_count,
            "carton_label": f"{idx}/{mark.carton_count}",
            "shipping_mark_code": mark.shipping_mark_code,
            "customer_name": mark.customer_name,
            "customer_phone": mark.customer_phone,
            "destination_region": mark.destination_region,
            "packing_list_summary": mark.packing_list_summary,
            "qr_payload": qr_payload,
        }
        for idx in range(1, (mark.carton_count or 1) + 1)
    ]

    return {
        # Kept as ``logo`` for backwards-compatible API clients. It now carries
        # the shipment owner's business name rather than platform branding.
        "logo": issuer_name or "Cargo Company",
        "issuer_name": issuer_name or "Cargo Company",
        "shipping_mark_code": mark.shipping_mark_code,
        "booking_id": str(mark.booking_id),
        "cargo_type": mark.cargo_type,
        "customer_name": mark.customer_name,
        "customer_phone": mark.customer_phone,
        "destination_region": mark.destination_region,
        "packing_list_summary": mark.packing_list_summary,
        "carton_count": mark.carton_count,
        "qr_payload": qr_payload,
        "labels": labels,
    }
