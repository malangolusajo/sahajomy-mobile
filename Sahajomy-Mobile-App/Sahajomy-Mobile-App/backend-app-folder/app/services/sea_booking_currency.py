"""Currency snapshot helpers for container-sea_booking financial records."""

from app.models.container import SeaBooking
from app.models.finance import Payment, Receipt, SeaBookingInvoice
from sqlalchemy.orm import Session

SUPPORTED_SEA_BOOKING_CURRENCIES = {"TZS", "RMB", "USD"}


def normalize_sea_booking_currency(value: str | None) -> str | None:
    currency = (value or "").strip().upper()
    return currency if currency in SUPPORTED_SEA_BOOKING_CURRENCIES else None


def snapshot_sea_booking_currency(
    db: Session, sea_booking: SeaBooking
) -> str:
    """Return the sea_booking currency, creating a legacy snapshot only on use.

    New sea_bookings always have a snapshot. A legacy sea_booking can only be
    repaired from a currency already stored on one of its financial records.
    The current container is deliberately not used: it may have been edited
    after the original commercial agreement. Existing financial records are
    never rewritten here.
    """
    currency = normalize_sea_booking_currency(sea_booking.currency)
    if currency:
        return currency

    evidence = set()
    for model in (SeaBookingInvoice, Receipt, Payment):
        evidence.update(
            filter(
                None,
                (
                    normalize_sea_booking_currency(value)
                    for (value,) in db.query(model.currency)
                    .filter(model.sea_booking_id == sea_booking.id)
                    .all()
                ),
            )
        )

    if len(evidence) == 1:
        sea_booking.currency = evidence.pop()
        db.flush()
        return sea_booking.currency

    if len(evidence) > 1:
        raise ValueError(
            "Sea booking financial records contain conflicting currencies. "
            "Resolve the records before generating another document."
        )

    raise ValueError(
        "Sea booking currency is unresolved for this legacy record. "
        "Set a reviewed sea_booking currency before creating a financial record."
    )
