"""Shared rate lookup, calculation, and safe GoodsType matching for air cargo."""

from decimal import ROUND_HALF_UP, Decimal
from difflib import SequenceMatcher
from typing import Optional
from uuid import UUID

from app.models.air_cargo import AirCargoRate
from app.models.container import GoodsType, GoodsTypeAlias
from app.services.goods_standardization import normalize_goods_alias
from fastapi import HTTPException
from sqlalchemy.orm import Session

DEFAULT_AIR_CARGO_ROUTE = "China → Africa"

NORMAL_GOODS_NOTICE = (
    "Normal Goods means products with no powder, battery, liquid, or chemical. "
    "Do not select Normal Goods if the shipment contains any of these items."
)
CERTIFICATION_NOTICE = (
    "Import certification is required for food, medicines, cosmetics, fruits, "
    "perfumes, and supplements. These goods cannot use the 1–3 day Express "
    "service until the required permit has been obtained."
)


def get_air_cargo_goods_policy(goods_type_name: str) -> dict:
    """Return customer-facing safety and certification rules for a Goods Type.

    The master catalogue contains granular names, so certification rules use the
    supplied rate-card product families rather than relying on a single exact
    catalogue label.
    """
    normalized = normalize_goods_name(goods_type_name)
    is_normal_goods = normalized in {"normalgoods", "normalhkgoods"}
    requires_certification = any(
        keyword in normalized
        for keyword in (
            "food",
            "medicine",
            "cosmetic",
            "fruit",
            "perfume",
            "supplement",
        )
    )
    return {
        "is_normal_goods": is_normal_goods,
        "requires_certification": requires_certification,
        "normal_goods_notice": NORMAL_GOODS_NOTICE if is_normal_goods else None,
        "certification_notice": (
            CERTIFICATION_NOTICE if requires_certification else None
        ),
    }


# Transcribed from the supplied Streetcode 2026 China–Tanzania air-cargo card.
# Aliases are matching hints only; the persisted rate always points to an
# existing GoodsType and never recreates the source description.
AIR_CARGO_2026_RATE_CARD = [
    {
        "name": "Normal/HK Goods",
        "aliases": ["normal goods"],
        "method": "Express",
        "pricing_type": "per_kg",
        "price": 14,
        "transit": "1–3 Days",
    },
    {
        "name": "Normal Goods",
        "aliases": ["normal goods"],
        "method": "Cargo",
        "pricing_type": "per_kg",
        "price": 12.5,
        "transit": "5–7 Days",
        "restrictions": "Published card lists USD 12–13/kg; confirm the final rate with the cargo team.",
    },
    {
        "name": "Laptops less 3.8kg",
        "aliases": ["laptop desktop", "laptop"],
        "method": "Express",
        "pricing_type": "per_unit",
        "price": 50,
        "transit": "1–3 Days",
        "condition": "Under 3.8 kg",
        "maximum_weight_kg": 3.8,
    },
    {
        "name": "Laptops more 3.8kg",
        "aliases": ["laptop desktop", "laptop"],
        "method": "Express",
        "pricing_type": "per_kg",
        "price": 14,
        "transit": "1–3 Days",
        "condition": "Over 3.8 kg",
        "minimum_weight_kg": 3.81,
    },
    {
        "name": "Smart phones, Cameras",
        "aliases": ["smart phone", "camera", "photography equipment"],
        "method": "Express",
        "pricing_type": "per_unit",
        "price": 20,
        "transit": "1–3 Days",
    },
    {
        "name": "Documents",
        "aliases": ["documents"],
        "method": "Express",
        "pricing_type": "per_unit",
        "price": 20,
        "transit": "1–3 Days",
    },
    {
        "name": "Tablets for Adults",
        "aliases": ["tablet"],
        "method": "Express",
        "pricing_type": "per_unit",
        "price": 30,
        "transit": "1–3 Days",
    },
    {
        "name": "Tablets for Kids",
        "aliases": ["kids tablet"],
        "method": "Express",
        "pricing_type": "per_kg",
        "price": 15,
        "transit": "1–3 Days",
    },
    {
        "name": "Desktops, Play Stations",
        "aliases": ["laptop desktop", "heavy games", "light games"],
        "method": "Express",
        "pricing_type": "per_kg",
        "price": 14,
        "transit": "1–3 Days",
    },
    {
        "name": "Speakers, Professional cameras",
        "aliases": ["music equipment", "photography equipment"],
        "method": "Express",
        "pricing_type": "per_kg",
        "price": 14,
        "transit": "1–3 Days",
    },
    {
        "name": "Smart watch, AirPods",
        "aliases": ["watches wall clocks", "mobile accessories"],
        "method": "Express",
        "pricing_type": "per_kg",
        "price": 14,
        "transit": "1–3 Days",
    },
    {
        "name": "Cellular phones, Routers",
        "aliases": ["cheap mobile phone", "smart phone"],
        "method": "HK",
        "pricing_type": "per_kg",
        "price": 13.5,
        "transit": "14 Days",
    },
    {
        "name": "Custom Declared Goods",
        "aliases": ["custom declared goods"],
        "method": "HK",
        "pricing_type": "per_kg",
        "price": 13.5,
        "transit": "14 Days",
        "restrictions": "USD 100 customs declaration charge applies.",
    },
    {
        "name": "Other HK Goods with External batteries",
        "aliases": ["battery", "mobile battery", "car battery"],
        "method": "HK",
        "pricing_type": "per_kg",
        "price": 13.5,
        "transit": "14 Days",
    },
    {
        "name": "Food, Medicines, Cosmetics",
        "aliases": ["cosmetics", "medical machines", "hospital items", "food stuff"],
        "method": "HK",
        "pricing_type": "per_kg",
        "price": 14,
        "transit": "14 Days",
        "restrictions": "Import certification permit required; not eligible for 1–3 day Express.",
    },
    {
        "name": "Fruits, Perfumes, Supplements",
        "aliases": ["perfume", "fish food"],
        "method": "HK",
        "pricing_type": "per_kg",
        "price": 14,
        "transit": "14 Days",
        "restrictions": "Import certification permit required; not eligible for 1–3 day Express.",
    },
]


def normalize_goods_name(value: str) -> str:
    """Compare user supplied names without case, whitespace, or punctuation."""
    return normalize_goods_alias(value)


def find_similar_goods_type(
    db: Session, requested_name: str
) -> tuple[Optional[GoodsType], float]:
    """Return a strong existing GoodsType match, never create one implicitly."""
    normalized = normalize_goods_name(requested_name)
    if not normalized:
        return None, 0.0

    alias = (
        db.query(GoodsTypeAlias)
        .filter(GoodsTypeAlias.normalized_alias == normalized)
        .first()
    )
    if alias and alias.goods_type.is_active and alias.goods_type.is_customs_standard:
        return alias.goods_type, 1.0

    candidates = (
        db.query(GoodsType)
        .filter(
            GoodsType.is_active.is_(True),
            GoodsType.is_customs_standard.is_(True),
        )
        .order_by(GoodsType.name.asc())
        .all()
    )
    best, best_score = None, 0.0
    for candidate in candidates:
        candidate_normalized = normalize_goods_name(candidate.name)
        if not candidate_normalized:
            continue
        if normalized == candidate_normalized:
            return candidate, 1.0
        score = SequenceMatcher(None, normalized, candidate_normalized).ratio()
        if normalized in candidate_normalized or candidate_normalized in normalized:
            score = max(
                score,
                min(len(normalized), len(candidate_normalized))
                / max(len(normalized), len(candidate_normalized)),
            )
        if score > best_score:
            best, best_score = candidate, score
    return (best, best_score) if best_score >= 0.72 else (None, best_score)


def serialize_rate(rate: AirCargoRate) -> dict:
    return {
        "id": str(rate.id),
        "cargo_admin_id": str(rate.cargo_admin_id) if rate.cargo_admin_id else None,
        "goods_type_id": str(rate.goods_type_id),
        "goods_type_name": rate.goods_type.name if rate.goods_type else None,
        "route": rate.route,
        "shipping_method": rate.shipping_method,
        "pricing_type": rate.pricing_type,
        "price": float(rate.price),
        "currency": rate.currency,
        "transit_time": rate.transit_time,
        "restrictions": rate.restrictions,
        "condition_label": rate.condition_label or None,
        "minimum_weight_kg": (
            float(rate.minimum_weight_kg)
            if rate.minimum_weight_kg is not None
            else None
        ),
        "maximum_weight_kg": (
            float(rate.maximum_weight_kg)
            if rate.maximum_weight_kg is not None
            else None
        ),
        "is_active": bool(rate.is_active),
        "goods_policy": get_air_cargo_goods_policy(
            rate.goods_type.name if rate.goods_type else ""
        ),
    }


def calculate_rate_total(
    rate: AirCargoRate, *, weight_kg: float, quantity: float = 1
) -> Decimal:
    if weight_kg <= 0:
        raise HTTPException(status_code=400, detail="Weight must be greater than 0 KG")
    if quantity <= 0:
        raise HTTPException(
            status_code=400, detail="Quantity must be greater than zero"
        )
    if (
        rate.minimum_weight_kg is not None
        and Decimal(str(weight_kg)) < rate.minimum_weight_kg
    ):
        raise HTTPException(
            status_code=400,
            detail="Selected rate does not apply below its minimum weight",
        )
    if (
        rate.maximum_weight_kg is not None
        and Decimal(str(weight_kg)) > rate.maximum_weight_kg
    ):
        raise HTTPException(
            status_code=400,
            detail="Selected rate does not apply above its maximum weight",
        )
    multiplier = Decimal(str(weight_kg if rate.pricing_type == "per_kg" else quantity))
    return (Decimal(rate.price) * multiplier).quantize(
        Decimal("0.01"), rounding=ROUND_HALF_UP
    )


def get_matching_rate(
    db: Session,
    *,
    rate_id: str,
    goods_type_id: str,
    weight_kg: float,
    cargo_admin_id: str | None = None,
) -> AirCargoRate:
    try:
        rate_uuid = UUID(str(rate_id))
    except (TypeError, ValueError) as exc:
        raise HTTPException(
            status_code=400, detail="Invalid air cargo rate selected"
        ) from exc
    rate = (
        db.query(AirCargoRate)
        .filter(
            AirCargoRate.id == rate_uuid,
            AirCargoRate.goods_type_id == goods_type_id,
            AirCargoRate.is_active.is_(True),
        )
        .first()
    )
    if not rate:
        raise HTTPException(
            status_code=400,
            detail="Selected air cargo rate is unavailable for this goods type",
        )
    if cargo_admin_id and str(rate.cargo_admin_id or "") != str(cargo_admin_id):
        raise HTTPException(
            status_code=409,
            detail="The selected rate does not belong to the selected cargo provider.",
        )
    calculate_rate_total(rate, weight_kg=weight_kg)
    return rate
