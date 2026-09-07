"""Validation and synonym matching for the HS-aligned goods catalogue."""

import re
from difflib import SequenceMatcher

from app.models.container import GoodsType, GoodsTypeAlias
from fastapi import HTTPException
from sqlalchemy.orm import Session

HS_VERSION = "HS 2022"
HS_LEVELS = {"chapter", "heading", "subheading", "multiple"}
ENGLISH_CATALOG_NAME = re.compile(r"^[A-Za-z0-9][A-Za-z0-9 &(),/'-]*$")


def normalize_goods_alias(value: str) -> str:
    return re.sub(r"[^a-z0-9]", "", (value or "").lower())


def canonical_key(value: str) -> str:
    return re.sub(r"[^A-Z0-9]+", "_", (value or "").upper()).strip("_")


def validate_english_catalog_name(value: str, *, label: str = "Goods Type") -> str:
    name = " ".join((value or "").split()).strip()
    if not name or not ENGLISH_CATALOG_NAME.fullmatch(name):
        raise HTTPException(
            status_code=422,
            detail=f"{label} names must use standardized English letters and terms.",
        )
    return name


def validate_hs_reference(reference: str, level: str) -> tuple[str, str]:
    normalized_level = (level or "").strip().lower()
    normalized_reference = (reference or "").replace("–", "-").strip()
    if normalized_level not in HS_LEVELS:
        raise HTTPException(
            status_code=422, detail="Choose a valid HS classification level."
        )

    expected_lengths = {"chapter": {2}, "heading": {4}, "subheading": {6}}
    if normalized_level in expected_lengths:
        if (
            not normalized_reference.isdigit()
            or len(normalized_reference) not in expected_lengths[normalized_level]
        ):
            raise HTTPException(
                status_code=422,
                detail=f"An HS {normalized_level} must contain exactly {next(iter(expected_lengths[normalized_level]))} digits.",
            )
    elif not re.fullmatch(r"\d{2,6}(?:[/-]\d{2,6})+", normalized_reference):
        raise HTTPException(
            status_code=422,
            detail="A multiple HS reference must contain official numeric chapters/headings separated by / or -.",
        )
    return normalized_reference, normalized_level


def find_catalog_conflict(
    db: Session,
    name: str,
    *,
    exclude_id=None,
    similarity_threshold: float = 0.86,
) -> GoodsType | None:
    normalized = normalize_goods_alias(name)
    alias = (
        db.query(GoodsTypeAlias)
        .filter(GoodsTypeAlias.normalized_alias == normalized)
        .first()
    )
    if alias and str(alias.goods_type_id) != str(exclude_id or ""):
        return alias.goods_type

    query = db.query(GoodsType).filter(GoodsType.is_customs_standard.is_(True))
    if exclude_id:
        query = query.filter(GoodsType.id != exclude_id)
    best = None
    best_score = 0.0
    for candidate in query.all():
        candidate_name = normalize_goods_alias(candidate.name)
        if not candidate_name:
            continue
        score = SequenceMatcher(None, normalized, candidate_name).ratio()
        if normalized in candidate_name or candidate_name in normalized:
            score = max(
                score,
                min(len(normalized), len(candidate_name))
                / max(len(normalized), len(candidate_name)),
            )
        if score > best_score:
            best, best_score = candidate, score
    return best if best_score >= similarity_threshold else None
