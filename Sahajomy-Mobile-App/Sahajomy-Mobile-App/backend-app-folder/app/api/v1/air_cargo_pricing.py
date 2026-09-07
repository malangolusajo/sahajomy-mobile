"""Rate administration and approval APIs for the existing air-cargo workflow."""

from datetime import datetime
from typing import Literal, Optional

from app.core.audit import log_action
from app.core.dependencies import get_cargo_admin, get_super_admin
from app.database import get_db
from app.models.air_cargo import AirCargoGoodsTypeRequest, AirCargoRate
from app.models.container import GoodsType
from app.models.user import User
from app.services.air_cargo_pricing import (
    AIR_CARGO_2026_RATE_CARD,
    DEFAULT_AIR_CARGO_ROUTE,
    find_similar_goods_type,
    normalize_goods_name,
    serialize_rate,
)
from app.services.goods_catalog import serialize_active_goods_types
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, joinedload

cargo_admin_router = APIRouter(prefix="/cargo_admin", tags=["air-cargo-pricing"])
super_admin_router = APIRouter(prefix="/super_admin", tags=["air-cargo-pricing"])


class AirCargoRatePayload(BaseModel):
    goods_type_id: str
    route: str = Field(default=DEFAULT_AIR_CARGO_ROUTE, min_length=3, max_length=120)
    shipping_method: str = Field(..., min_length=2, max_length=50)
    pricing_type: Literal["per_kg", "per_unit"]
    price: float = Field(..., gt=0)
    currency: Literal["USD", "TZS", "RMB"] = "USD"
    transit_time: str = Field(..., min_length=2, max_length=80)
    restrictions: Optional[str] = Field(default=None, max_length=2000)
    condition_label: Optional[str] = Field(default=None, max_length=150)
    minimum_weight_kg: Optional[float] = Field(default=None, gt=0)
    maximum_weight_kg: Optional[float] = Field(default=None, gt=0)
    is_active: bool = True


class AirCargoRateUpdate(BaseModel):
    route: Optional[str] = Field(default=None, min_length=3, max_length=120)
    shipping_method: Optional[str] = Field(default=None, min_length=2, max_length=50)
    pricing_type: Optional[Literal["per_kg", "per_unit"]] = None
    price: Optional[float] = Field(default=None, gt=0)
    currency: Optional[Literal["USD", "TZS", "RMB"]] = None
    transit_time: Optional[str] = Field(default=None, min_length=2, max_length=80)
    restrictions: Optional[str] = Field(default=None, max_length=2000)
    condition_label: Optional[str] = Field(default=None, max_length=150)
    minimum_weight_kg: Optional[float] = Field(default=None, gt=0)
    maximum_weight_kg: Optional[float] = Field(default=None, gt=0)
    is_active: Optional[bool] = None


class GoodsTypeRequestPayload(BaseModel):
    name: str = Field(..., min_length=2, max_length=150)
    source: str = Field(default="Air Cargo Rate Setup", min_length=2, max_length=100)


class GoodsTypeRequestReview(BaseModel):
    status: Literal["approved", "rejected"]
    goods_type_id: Optional[str] = None
    review_note: Optional[str] = Field(default=None, max_length=2000)


def _clean_rate_fields(payload: AirCargoRatePayload | AirCargoRateUpdate) -> dict:
    fields = payload.model_dump(exclude_unset=True)
    for name in (
        "route",
        "shipping_method",
        "transit_time",
        "restrictions",
        "condition_label",
    ):
        if name in fields and isinstance(fields[name], str):
            fields[name] = fields[name].strip() or None
    if "condition_label" in fields and fields["condition_label"] is None:
        fields["condition_label"] = ""
    minimum = fields.get("minimum_weight_kg")
    maximum = fields.get("maximum_weight_kg")
    if minimum is not None and maximum is not None and minimum > maximum:
        raise HTTPException(
            status_code=422, detail="Minimum weight cannot exceed maximum weight"
        )
    return fields


def _rate_or_404(db: Session, rate_id: str, admin_id) -> AirCargoRate:
    rate = (
        db.query(AirCargoRate)
        .options(joinedload(AirCargoRate.goods_type))
        .filter(
            AirCargoRate.id == rate_id,
            AirCargoRate.cargo_admin_id == admin_id,
        )
        .first()
    )
    if not rate:
        raise HTTPException(status_code=404, detail="Air cargo rate not found")
    return rate


def _request_response(request: AirCargoGoodsTypeRequest) -> dict:
    return {
        "id": str(request.id),
        "requested_name": request.requested_name,
        "source": request.source,
        "status": request.status,
        "suggested_goods_type": (
            {
                "id": str(request.suggested_goods_type.id),
                "name": request.suggested_goods_type.name,
            }
            if request.suggested_goods_type
            else None
        ),
        "resolved_goods_type": (
            {
                "id": str(request.resolved_goods_type.id),
                "name": request.resolved_goods_type.name,
            }
            if request.resolved_goods_type
            else None
        ),
        "review_note": request.review_note,
        "created_at": request.created_at,
        "reviewed_at": request.reviewed_at,
    }


@cargo_admin_router.get("/air-cargo-rates/goods-types")
def list_rate_goods_types(
    db: Session = Depends(get_db), admin: User = Depends(get_cargo_admin)
):
    del admin
    return serialize_active_goods_types(db)


@cargo_admin_router.get("/air-cargo-rates")
def list_air_cargo_rates(
    include_inactive: bool = False,
    db: Session = Depends(get_db),
    admin: User = Depends(get_cargo_admin),
):
    query = db.query(AirCargoRate).options(joinedload(AirCargoRate.goods_type))
    query = query.filter(AirCargoRate.cargo_admin_id == admin.id)
    if not include_inactive:
        query = query.filter(AirCargoRate.is_active.is_(True))
    return [
        serialize_rate(rate)
        for rate in query.order_by(AirCargoRate.created_at.desc()).all()
    ]


@cargo_admin_router.post("/air-cargo-rates", status_code=201)
def create_air_cargo_rate(
    body: AirCargoRatePayload,
    db: Session = Depends(get_db),
    admin: User = Depends(get_cargo_admin),
):
    fields = _clean_rate_fields(body)
    goods_type = db.query(GoodsType).filter(GoodsType.id == body.goods_type_id).first()
    if not goods_type:
        raise HTTPException(status_code=404, detail="Goods type not found")
    fields["goods_type_id"] = goods_type.id
    fields["cargo_admin_id"] = admin.id
    rate = AirCargoRate(**fields)
    db.add(rate)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=409,
            detail="Air Cargo rate already exists for this Goods Type, route, shipping method, and condition.",
        ) from exc
    db.refresh(rate)
    log_action(
        db,
        "AIR_CARGO_RATE_CREATED",
        admin.id,
        "air_cargo_rate",
        rate.id,
        {"goods_type_id": str(goods_type.id)},
    )
    db.commit()
    return serialize_rate(rate)


@cargo_admin_router.patch("/air-cargo-rates/{rate_id}")
def update_air_cargo_rate(
    rate_id: str,
    body: AirCargoRateUpdate,
    db: Session = Depends(get_db),
    admin: User = Depends(get_cargo_admin),
):
    rate = _rate_or_404(db, rate_id, admin.id)
    fields = _clean_rate_fields(body)
    prospective_minimum = fields.get("minimum_weight_kg", rate.minimum_weight_kg)
    prospective_maximum = fields.get("maximum_weight_kg", rate.maximum_weight_kg)
    if (
        prospective_minimum is not None
        and prospective_maximum is not None
        and prospective_minimum > prospective_maximum
    ):
        raise HTTPException(
            status_code=422, detail="Minimum weight cannot exceed maximum weight"
        )
    for name, value in fields.items():
        setattr(rate, name, value)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=409,
            detail="Air Cargo rate already exists for this combination.",
        ) from exc
    db.refresh(rate)
    log_action(db, "AIR_CARGO_RATE_UPDATED", admin.id, "air_cargo_rate", rate.id, {})
    db.commit()
    return serialize_rate(rate)


@cargo_admin_router.delete("/air-cargo-rates/{rate_id}")
def deactivate_air_cargo_rate(
    rate_id: str,
    db: Session = Depends(get_db),
    admin: User = Depends(get_cargo_admin),
):
    rate = _rate_or_404(db, rate_id, admin.id)
    rate.is_active = False
    db.commit()
    log_action(
        db, "AIR_CARGO_RATE_DEACTIVATED", admin.id, "air_cargo_rate", rate.id, {}
    )
    db.commit()
    return {"message": "Air cargo rate deactivated"}


@cargo_admin_router.post("/air-cargo-rates/import-2026-card")
def import_supplied_2026_rate_card(
    db: Session = Depends(get_db),
    admin: User = Depends(get_cargo_admin),
):
    """Apply the supplied rate card only where it maps to an existing GoodsType."""
    goods_types = db.query(GoodsType).all()
    by_normalized_name = {
        normalize_goods_name(goods_type.name): goods_type for goods_type in goods_types
    }
    created, already_configured, pending_review = 0, 0, []

    for card_rate in AIR_CARGO_2026_RATE_CARD:
        goods_type = next(
            (
                by_normalized_name.get(normalize_goods_name(alias))
                for alias in card_rate["aliases"]
                if by_normalized_name.get(normalize_goods_name(alias))
            ),
            None,
        )
        if not goods_type:
            goods_type, _ = find_similar_goods_type(db, card_rate["name"])
        if not goods_type:
            normalized_name = normalize_goods_name(card_rate["name"])
            request = (
                db.query(AirCargoGoodsTypeRequest)
                .filter(
                    AirCargoGoodsTypeRequest.normalized_name == normalized_name,
                    AirCargoGoodsTypeRequest.status == "pending",
                )
                .first()
            )
            if not request:
                db.add(
                    AirCargoGoodsTypeRequest(
                        requested_name=card_rate["name"],
                        normalized_name=normalized_name,
                        source="Air Cargo Price Card 2026",
                    )
                )
            pending_review.append(card_rate["name"])
            continue

        condition_label = card_rate.get("condition", "")
        existing = (
            db.query(AirCargoRate)
            .filter(
                AirCargoRate.goods_type_id == goods_type.id,
                AirCargoRate.cargo_admin_id == admin.id,
                AirCargoRate.route == DEFAULT_AIR_CARGO_ROUTE,
                AirCargoRate.shipping_method == card_rate["method"],
                AirCargoRate.pricing_type == card_rate["pricing_type"],
                AirCargoRate.condition_label == condition_label,
            )
            .first()
        )
        if existing:
            already_configured += 1
            continue
        db.add(
            AirCargoRate(
                cargo_admin_id=admin.id,
                goods_type_id=goods_type.id,
                route=DEFAULT_AIR_CARGO_ROUTE,
                shipping_method=card_rate["method"],
                pricing_type=card_rate["pricing_type"],
                price=card_rate["price"],
                currency="USD",
                transit_time=card_rate["transit"],
                restrictions=card_rate.get("restrictions"),
                condition_label=condition_label,
                minimum_weight_kg=card_rate.get("minimum_weight_kg"),
                maximum_weight_kg=card_rate.get("maximum_weight_kg"),
            )
        )
        created += 1

    db.commit()
    log_action(
        db,
        "AIR_CARGO_2026_RATE_CARD_IMPORTED",
        admin.id,
        "air_cargo_rate",
        None,
        {
            "created": created,
            "already_configured": already_configured,
            "pending_review": pending_review,
        },
    )
    db.commit()
    return {
        "message": "2026 rate card processed against existing Goods Types.",
        "created_rates": created,
        "already_configured": already_configured,
        "pending_goods_type_review": pending_review,
    }


@cargo_admin_router.post("/air-cargo-goods-type-requests", status_code=201)
def request_missing_goods_type(
    body: GoodsTypeRequestPayload,
    db: Session = Depends(get_db),
    admin: User = Depends(get_cargo_admin),
):
    del admin
    name = body.name.strip()
    normalized_name = normalize_goods_name(name)
    match, score = find_similar_goods_type(db, name)
    if match:
        return {
            "message": "Existing Goods Type matched; no request was created.",
            "matched_goods_type": {
                "id": str(match.id),
                "name": match.name,
                "similarity": round(score, 2),
            },
        }
    request = (
        db.query(AirCargoGoodsTypeRequest)
        .filter(
            AirCargoGoodsTypeRequest.normalized_name == normalized_name,
            AirCargoGoodsTypeRequest.status == "pending",
        )
        .first()
    )
    if request:
        return {
            "message": "A review request already exists.",
            "request": _request_response(request),
        }
    request = AirCargoGoodsTypeRequest(
        requested_name=name,
        normalized_name=normalized_name,
        source=body.source.strip(),
    )
    db.add(request)
    db.commit()
    db.refresh(request)
    return {
        "message": "Goods Type request submitted for Super Admin review.",
        "request": _request_response(request),
    }


@super_admin_router.get("/air-cargo-goods-type-requests")
def list_air_cargo_goods_type_requests(
    status: Optional[Literal["pending", "approved", "rejected"]] = None,
    db: Session = Depends(get_db),
    admin: User = Depends(get_super_admin),
):
    del admin
    query = db.query(AirCargoGoodsTypeRequest).options(
        joinedload(AirCargoGoodsTypeRequest.suggested_goods_type),
        joinedload(AirCargoGoodsTypeRequest.resolved_goods_type),
    )
    if status:
        query = query.filter(AirCargoGoodsTypeRequest.status == status)
    return [
        _request_response(row)
        for row in query.order_by(AirCargoGoodsTypeRequest.created_at.desc()).all()
    ]


@super_admin_router.patch("/air-cargo-goods-type-requests/{request_id}")
def review_air_cargo_goods_type_request(
    request_id: str,
    body: GoodsTypeRequestReview,
    db: Session = Depends(get_db),
    admin: User = Depends(get_super_admin),
):
    request = (
        db.query(AirCargoGoodsTypeRequest)
        .filter(AirCargoGoodsTypeRequest.id == request_id)
        .first()
    )
    if not request:
        raise HTTPException(status_code=404, detail="Goods Type request not found")
    if body.status == "approved":
        if not body.goods_type_id:
            raise HTTPException(
                status_code=422, detail="Choose an existing Goods Type before approving"
            )
        goods_type = (
            db.query(GoodsType).filter(GoodsType.id == body.goods_type_id).first()
        )
        if not goods_type:
            raise HTTPException(status_code=404, detail="Goods type not found")
        request.resolved_goods_type_id = goods_type.id
    request.status = body.status
    request.review_note = body.review_note.strip() if body.review_note else None
    request.reviewed_by_id = admin.id
    request.reviewed_at = datetime.utcnow()
    db.commit()
    db.refresh(request)
    log_action(
        db,
        "AIR_CARGO_GOODS_TYPE_REQUEST_REVIEWED",
        admin.id,
        "air_cargo_goods_type_request",
        request.id,
        {"status": body.status},
    )
    db.commit()
    return _request_response(request)
