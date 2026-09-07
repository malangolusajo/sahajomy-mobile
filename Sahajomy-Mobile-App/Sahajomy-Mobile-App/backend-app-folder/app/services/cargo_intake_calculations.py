"""Authoritative decimal-safe calculations for warehouse cargo intake."""

from decimal import Decimal
from typing import Iterable, Mapping

DEFAULT_AIR_VOLUMETRIC_DIVISOR = Decimal("6000")


def decimal_value(value) -> Decimal:
    return Decimal(str(value or 0))


def item_measurements(
    item: Mapping, divisor: Decimal = DEFAULT_AIR_VOLUMETRIC_DIVISOR
) -> dict:
    cartons = Decimal(int(item.get("carton_count") or 0))
    length = decimal_value(item.get("length_cm"))
    width = decimal_value(item.get("width_cm"))
    height = decimal_value(item.get("height_cm"))
    quantity = decimal_value(item.get("qty_per_carton"))
    per_carton_weight = item.get("gross_weight_per_carton_kg")
    explicit_total_weight = item.get("total_gross_weight_kg")
    direct_cbm = item.get("cbm_per_carton")
    # Suppliers often provide CBM per carton without dimensions. Preserve that
    # authoritative operational value; dimensions are only a calculation aid.
    cbm_per_carton = (
        decimal_value(direct_cbm)
        if direct_cbm is not None
        else (length * width * height) / Decimal("1000000")
    )
    total_cbm = cbm_per_carton * cartons
    if per_carton_weight is not None:
        total_weight = decimal_value(per_carton_weight) * cartons
    else:
        total_weight = decimal_value(explicit_total_weight)
    volumetric_per_carton = (length * width * height) / divisor
    return {
        "total_quantity": cartons * quantity,
        "cbm_per_carton": cbm_per_carton,
        "total_cbm": total_cbm,
        "total_gross_weight_kg": total_weight,
        "volumetric_weight_per_carton_kg": volumetric_per_carton,
        "total_volumetric_weight_kg": volumetric_per_carton * cartons,
    }


def intake_totals(
    items: Iterable[Mapping],
    cargo_type: str,
    divisor: Decimal = DEFAULT_AIR_VOLUMETRIC_DIVISOR,
) -> dict:
    calculated = [item_measurements(item, divisor) for item in items]
    total = lambda key: sum(
        (decimal_value(row.get(key)) for row in calculated), Decimal("0")
    )
    gross_weight = total("total_gross_weight_kg")
    volumetric_weight = total("total_volumetric_weight_kg")
    return {
        "total_cartons": sum(int(item.get("carton_count") or 0) for item in items),
        "total_quantity": total("total_quantity"),
        "total_cbm": total("total_cbm"),
        "total_gross_weight_kg": gross_weight,
        "total_volumetric_weight_kg": (
            volumetric_weight if cargo_type == "air" else None
        ),
        "chargeable_weight_kg": (
            max(gross_weight, volumetric_weight) if cargo_type == "air" else None
        ),
        "items": calculated,
    }


def freight_calculation(
    cargo_type: str, charge_basis: str, totals: Mapping, rate_amount
) -> dict:
    rate = decimal_value(rate_amount)
    if cargo_type == "air":
        billable = decimal_value(totals.get("chargeable_weight_kg"))
        unit = "kg"
    elif charge_basis == "cbm":
        billable = decimal_value(totals.get("total_cbm"))
        unit = "CBM"
    elif charge_basis == "metric_ton":
        billable = decimal_value(totals.get("total_gross_weight_kg")) / Decimal("1000")
        unit = "MT"
    elif charge_basis == "flat":
        billable = Decimal("1")
        unit = "flat"
    else:
        billable = Decimal("0")
        unit = "custom"
    return {
        "billable_quantity": billable,
        "billable_unit": unit,
        "shipping_charge": billable * rate,
    }
