#!/usr/bin/env python3
"""Verify the migration-managed standardized Goods catalogue.

This command intentionally never inserts Goods Types. The Alembic rollout migration
is the only seed authority, preventing legacy deployment jobs from recreating aliases
as separate goods.
"""

from app.core.config import settings
from app.models import GoodsCategory, GoodsType
from app.services.standard_goods_catalog import CATALOG, CATEGORIES, STANDARD_VERSION
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker


def main() -> None:
    session = sessionmaker(bind=create_engine(settings.database_url))()
    try:
        category_count = (
            session.query(GoodsCategory)
            .filter(
                GoodsCategory.is_standard.is_(True),
                GoodsCategory.is_active.is_(True),
            )
            .count()
        )
        type_count = (
            session.query(GoodsType)
            .filter(
                GoodsType.is_customs_standard.is_(True),
                GoodsType.is_active.is_(True),
                GoodsType.hs_version == STANDARD_VERSION,
            )
            .count()
        )
        expected = (len(CATEGORIES), len(CATALOG))
        actual = (category_count, type_count)
        if actual != expected:
            raise RuntimeError(
                f"Goods catalogue is incomplete: found {actual}, expected {expected}. "
                "Run `alembic upgrade head`."
            )
        print(
            f"Goods catalogue verified: {type_count} canonical Goods Types in "
            f"{category_count} categories ({STANDARD_VERSION})."
        )
    finally:
        session.close()


if __name__ == "__main__":
    main()
