"""Safe, centralized normalization for existing China warehouse addresses."""

import re

from app.models.container import Warehouse

_YIWU = re.compile(r"义乌")


def normalize_china_warehouse_address(raw: str | None) -> dict:
    """Return only high-confidence values and preserve the original text.

    This deliberately recognizes no broad geographic guesses. New localities
    must be added as explicit, reviewed rules rather than inferred at booking.
    """
    original = re.sub(r"\s+", "", raw or "")
    result = {
        "original": original or None,
        "province": None,
        "city": None,
        "district": None,
        "street": None,
        "detailed_address": original or None,
        "status": "unstructured" if original else "invalid",
        "source": "auto",
    }
    if _YIWU.search(original):
        result.update(
            province="浙江省",
            city="金华市",
            district="义乌市",
            detailed_address=original.replace("义乌市", "", 1) or original,
            status="auto_structured",
        )
    return result


def is_china_warehouse(warehouse: Warehouse) -> bool:
    """Whether this is a China forwarding warehouse, without trusting UI input."""
    return bool(
        (warehouse.country_code or "").upper() == "CN"
        or "china" in (warehouse.country or "").lower()
        or "中国" in (warehouse.country or "")
        or warehouse.china_original_address
        or warehouse.china_province
    )


def normalize_warehouse_china_address(warehouse: Warehouse) -> bool:
    """Fill only missing, unconfirmed fields from a legacy address.

    The return value indicates a persistent change.  Manually configured
    values (``china_address_source == 'manual'``) are never rewritten.
    """
    if not is_china_warehouse(warehouse):
        return False
    original = (
        warehouse.china_original_address or warehouse.address or warehouse.location
    )
    parsed = normalize_china_warehouse_address(original)
    changed = False
    if original and not warehouse.china_original_address:
        warehouse.china_original_address = parsed["original"]
        changed = True
    if not warehouse.china_receiver_name and warehouse.contact_name_1:
        warehouse.china_receiver_name = warehouse.contact_name_1
        changed = True
    if not warehouse.china_mobile and warehouse.contact_phone_1:
        warehouse.china_mobile = warehouse.contact_phone_1
        changed = True
    if warehouse.china_address_source != "manual":
        for field, value in (
            ("china_province", parsed["province"]),
            ("china_city", parsed["city"]),
            ("china_district", parsed["district"]),
            ("china_street", parsed["street"]),
            ("china_detailed_address", parsed["detailed_address"]),
        ):
            if value and not getattr(warehouse, field):
                setattr(warehouse, field, value)
                changed = True
        if changed:
            warehouse.china_address_source = "auto"
            warehouse.china_address_status = parsed["status"]
    if not warehouse.china_address_status:
        warehouse.china_address_status = parsed["status"]
        changed = True
    return changed


def china_address_ready(warehouse: Warehouse) -> bool:
    """Whether the latest saved China address can be used for forwarding.

    Older warehouse records sometimes store the receiver inside the manually
    maintained detailed-address block instead of the dedicated receiver
    column.  Keep requiring the structured location and mobile fields, but do
    not reject an otherwise complete address that a cargo admin has explicitly
    updated.  Automatically imported addresses still require a separate
    receiver so incomplete legacy data cannot become bookable by accident.
    """
    return bool(
        warehouse.china_mobile
        and warehouse.china_province
        and warehouse.china_city
        and warehouse.china_detailed_address
        and (
            warehouse.china_receiver_name or warehouse.china_address_source == "manual"
        )
    )
