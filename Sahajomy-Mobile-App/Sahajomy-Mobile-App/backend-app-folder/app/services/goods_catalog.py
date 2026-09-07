"""Canonical read helpers for the platform-wide goods catalogue."""

from app.models.container import GoodsCategory
from sqlalchemy.orm import Session, joinedload


def list_active_goods_categories(db: Session) -> list[GoodsCategory]:
    """Return the one Super-Admin-managed catalogue used by every role."""
    return (
        db.query(GoodsCategory)
        .options(joinedload(GoodsCategory.goods_types))
        .filter(
            GoodsCategory.is_active.is_(True),
            GoodsCategory.is_standard.is_(True),
        )
        .order_by(GoodsCategory.name.asc())
        .all()
    )


def serialize_goods_catalog(db: Session) -> list[dict]:
    return [
        {
            "id": str(category.id),
            "name": category.name,
            "description": category.description,
            "canonical_key": category.canonical_key,
            "standard_version": category.standard_version,
            "goods_types": [
                {
                    "id": str(goods_type.id),
                    "name": goods_type.name,
                    "description": goods_type.description,
                    "canonical_key": goods_type.canonical_key,
                    "hs_reference": goods_type.hs_reference,
                    "hs_level": goods_type.hs_level,
                    "hs_version": goods_type.hs_version,
                    "customs_description": goods_type.customs_description,
                    "is_hazardous": bool(goods_type.is_hazardous),
                    "requires_special_handling": bool(
                        goods_type.requires_special_handling
                    ),
                }
                for goods_type in sorted(
                    category.goods_types,
                    key=lambda item: (item.name or "").casefold(),
                )
                if goods_type.is_active and goods_type.is_customs_standard
            ],
        }
        for category in list_active_goods_categories(db)
    ]


def serialize_active_goods_types(db: Session) -> list[dict]:
    """Flatten the canonical catalogue without creating a second definition."""
    return [
        {
            **goods_type,
            "category_id": category["id"],
            "category_name": category["name"],
            "category_key": category["canonical_key"],
        }
        for category in serialize_goods_catalog(db)
        for goods_type in category["goods_types"]
    ]
