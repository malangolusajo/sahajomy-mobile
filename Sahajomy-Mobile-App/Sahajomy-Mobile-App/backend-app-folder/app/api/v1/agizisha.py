"""Public Agizisha product requests and sourcing-agent management endpoints.

Public responses deliberately use a narrow serializer. Internal batch data,
supplier data, CBM and shipping calculations never cross this API boundary.
"""

from datetime import datetime, timedelta
from typing import Literal, Optional
from uuid import UUID

from app.core.audit import log_action
from app.core.captcha import verify_agizisha_captcha
from app.core.cloudinary import build_optimized_cloudinary_image_url
from app.core.config import settings
from app.core.dependencies import get_optional_authenticated_user, get_sourcing_agent
from app.core.public_input import normalize_public_name, normalize_public_whatsapp
from app.database import get_db
from app.models.container import GoodsType
from app.models.sourcing import (
    AgizishaOrder,
    SourcingBatch,
    SourcingProduct,
    SourcingProductVariant,
)
from app.models.sourcing_agent import SourcingAgent
from app.models.user import User
from app.services.realtime_notifications import create_notification
from fastapi import APIRouter, Depends, Header, HTTPException, Query, Request, status
from pydantic import BaseModel, Field, field_validator
from sqlalchemy import String, cast, func, or_
from sqlalchemy.orm import Session, joinedload

public_router = APIRouter(prefix="/public/agizisha", tags=["Public Agizisha"])
agent_router = APIRouter(
    prefix="/sourcing_agent/agizisha-orders", tags=["Sourcing Agent Agizisha"]
)

AGIZISHA_STATUSES = {
    "NEW",
    "CONTACTED",
    "QUOTATION_SENT",
    "CONFIRMED",
    "COMPLETED",
    "CANCELLED",
}


def _active_assigned_agent(product: SourcingProduct) -> Optional[User]:
    """Return an eligible batch owner without exposing that owner publicly."""
    batch = product.batch
    agent = batch.agent if batch else None
    if (
        agent
        and agent.role == "sourcing_agent"
        and agent.is_active
        and agent.status == "active"
    ):
        return agent
    return None


def _safe_public_attributes(product: SourcingProduct) -> dict[str, str | list[str]]:
    """Flatten legacy and structured attributes without public implementation metadata."""
    attributes = (
        product.public_attributes if isinstance(product.public_attributes, dict) else {}
    )
    safe_attributes: dict[str, str | list[str]] = {}
    ordered_attributes = []
    for index, (key, raw_value) in enumerate(attributes.items()):
        if (
            not isinstance(key, str)
            or not key
            or len(key) > 60
            or any(char in key for char in "<>")
        ):
            continue

        label = key
        display_order = index
        if isinstance(raw_value, dict) and raw_value.get("attribute_type"):
            label = raw_value.get("label")
            if (
                not isinstance(label, str)
                or not label.strip()
                or len(label.strip()) > 60
                or any(char in label for char in "<>")
            ):
                continue
            label = label.strip()
            try:
                display_order = int(raw_value.get("display_order", index))
            except (TypeError, ValueError):
                display_order = index
            attribute_type = raw_value.get("attribute_type")
            raw_feature_value = raw_value.get("value")
            if attribute_type == "dimensions" and isinstance(raw_feature_value, dict):
                dimensions = [
                    raw_feature_value.get(part)
                    for part in ("length", "width", "height")
                ]
                if not all(
                    isinstance(part, str) and part.strip() for part in dimensions
                ):
                    continue
                unit = raw_value.get("unit")
                if (
                    not isinstance(unit, str)
                    or not unit.strip()
                    or len(unit.strip()) > 20
                ):
                    continue
                ordered_attributes.append(
                    (
                        display_order,
                        index,
                        label,
                        f"{' × '.join(part.strip() for part in dimensions)} {unit.strip()}",
                    )
                )
                continue
            if attribute_type == "number_unit":
                unit = raw_value.get("unit")
                if (
                    not isinstance(unit, str)
                    or not unit.strip()
                    or len(unit.strip()) > 20
                ):
                    continue
                if (
                    not isinstance(raw_feature_value, str)
                    or not raw_feature_value.strip()
                ):
                    continue
                ordered_attributes.append(
                    (
                        display_order,
                        index,
                        label,
                        f"{raw_feature_value.strip()} {unit.strip()}",
                    )
                )
                continue
            raw_value = raw_feature_value

        values = raw_value if isinstance(raw_value, list) else [raw_value]
        clean_values = [
            value.strip()
            for value in values
            if isinstance(value, str) and value.strip() and len(value.strip()) <= 100
        ][:30]
        if clean_values:
            ordered_attributes.append(
                (
                    display_order,
                    index,
                    label,
                    clean_values if isinstance(raw_value, list) else clean_values[0],
                )
            )
    for _, _, label, value in sorted(
        ordered_attributes, key=lambda item: (item[0], item[1])
    ):
        safe_attributes[label] = value
    return safe_attributes


def _public_image_urls(product: SourcingProduct) -> list[str]:
    urls = [product.image_url, *(product.additional_image_urls or [])]
    unique_urls: list[str] = []
    for url in urls:
        if isinstance(url, str) and url.strip() and url not in unique_urls:
            unique_urls.append(build_optimized_cloudinary_image_url(url))
    return unique_urls


def _public_attribute_image_map(product: SourcingProduct) -> dict[str, dict[str, str]]:
    """Expose only gallery images linked to valid public specification values."""
    safe_attributes = _safe_public_attributes(product)
    gallery_urls = _public_image_urls(product)
    gallery = set(gallery_urls)
    result: dict[str, dict[str, str]] = {}
    raw_attributes = (
        product.public_attributes if isinstance(product.public_attributes, dict) else {}
    )
    for key, option_map in (product.attribute_image_map or {}).items():
        raw_attribute = raw_attributes.get(key)
        label = key
        if isinstance(raw_attribute, dict) and raw_attribute.get("attribute_type"):
            label = str(raw_attribute.get("label") or "").strip()
        allowed = safe_attributes.get(label)
        if not isinstance(allowed, list) or not isinstance(option_map, dict):
            continue
        clean_map = {}
        for option, url in option_map.items():
            optimized_url = build_optimized_cloudinary_image_url(url)
            if option in allowed and optimized_url in gallery:
                clean_map[option] = optimized_url
        if clean_map:
            result[label] = clean_map
    # Legacy products predate explicit mappings. When their gallery order has
    # enough pictures, preserve the former agent-entered option/image order as
    # a safe fallback until the product is edited and mapped explicitly.
    for label, values in safe_attributes.items():
        if not isinstance(values, list) or len(gallery_urls) < len(values):
            continue
        option_map = result.setdefault(label, {})
        for index, option in enumerate(values):
            option_map.setdefault(option, gallery_urls[index])
    return result


def _selected_product_image(
    product: SourcingProduct, selected_options: dict
) -> str | None:
    attribute_images = _public_attribute_image_map(product)
    labels = list(_safe_public_attributes(product))
    labels.sort(
        key=lambda label: (
            0 if label.casefold().replace("colour", "color") == "color" else 1
        )
    )
    for label in labels:
        selected = selected_options.get(label)
        if selected and attribute_images.get(label, {}).get(selected):
            return attribute_images[label][selected]
    return build_optimized_cloudinary_image_url(product.image_url)


def _public_category(product: SourcingProduct) -> str | None:
    if product.goods_type and product.goods_type.name:
        return product.goods_type.name
    return None


def _public_shipping(product: SourcingProduct) -> dict:
    """Calculate a customer-safe shipping amount without exposing CBM rates."""
    batch = product.batch
    if not batch or batch.shipping_method == "FREE_SHIPPING":
        return {"is_free": True, "amount_per_unit": 0.0}

    amount = round(
        float(product.cbm_per_unit or 0) * float(batch.shipping_fee_per_cbm or 0),
        2,
    )
    return {"is_free": amount == 0, "amount_per_unit": amount}


def _public_agent_profile(profile: Optional[SourcingAgent]) -> Optional[dict]:
    """The narrow, deliberately public representation of an agent."""
    if not profile:
        return None
    return {
        "handle": profile.public_handle,
        "display_name": profile.full_name,
        "profile_photo": build_optimized_cloudinary_image_url(profile.profile_photo),
        "is_verified": True,
    }


def _public_agent_profile_map(
    db: Session, agent_ids: list[UUID]
) -> dict[UUID, SourcingAgent]:
    """Return public profiles only for active, verified, opted-in agents."""
    if not agent_ids:
        return {}
    rows = (
        db.query(SourcingAgent)
        .join(User, User.id == SourcingAgent.user_id)
        .filter(
            SourcingAgent.user_id.in_(agent_ids),
            SourcingAgent.status == "verified",
            SourcingAgent.is_verified.is_(True),
            SourcingAgent.is_public.is_(True),
            SourcingAgent.public_handle.isnot(None),
            User.role == "sourcing_agent",
            User.is_active.is_(True),
            User.status == "active",
        )
        .all()
    )
    return {row.user_id: row for row in rows}


def _public_product(
    product: SourcingProduct, agent_profiles: Optional[dict[UUID, SourcingAgent]] = None
) -> dict:
    """The allow-list for unauthenticated product data."""
    return {
        "id": str(product.id),
        "name": product.name,
        "description": product.description,
        "image_url": build_optimized_cloudinary_image_url(product.image_url),
        "image_urls": _public_image_urls(product),
        "category": _public_category(product),
        "attributes": _safe_public_attributes(product),
        "attribute_images": _public_attribute_image_map(product),
        "customer_price": round(float(product.price_per_unit or 0), 2),
        "shipping": _public_shipping(product),
        "currency": (product.batch.currency if product.batch else None) or "TZS",
        "minimum_order_quantity": product.minimum_order_quantity or 1,
        "variants": [
            {
                "id": str(variant.id),
                "option_values": variant.option_values or {},
                "customer_price": round(float(variant.price_per_unit), 2),
                "in_stock": bool(variant.is_active and variant.stock_quantity > 0),
            }
            for variant in product.variants
            if variant.is_active
        ],
        "agent": _public_agent_profile(
            (agent_profiles or {}).get(product.batch.agent_id)
            if product.batch
            else None
        ),
    }


def _agent_order(order: AgizishaOrder) -> dict:
    product = order.product
    return {
        "id": str(order.id),
        "product": {
            "id": str(product.id),
            "name": product.name,
            "image_url": _selected_product_image(product, order.selected_options or {}),
        },
        "customer_name": order.customer_name,
        "whatsapp_number": order.whatsapp_number,
        "quantity": order.quantity,
        "variant_id": (
            str(order.product_variant_id) if order.product_variant_id else None
        ),
        "quoted_unit_price": (
            float(order.quoted_unit_price)
            if order.quoted_unit_price is not None
            else None
        ),
        "selected_options": order.selected_options or {},
        "status": order.status,
        "created_at": order.created_at.isoformat() if order.created_at else None,
        "updated_at": order.updated_at.isoformat() if order.updated_at else None,
    }


class AgizishaOrderCreate(BaseModel):
    product_id: UUID
    variant_id: Optional[UUID] = None
    full_name: Optional[str] = Field(default=None, min_length=2, max_length=150)
    whatsapp_number: Optional[str] = Field(default=None, min_length=7, max_length=30)
    quantity: Optional[int] = Field(default=None, ge=1, le=100000)
    selected_options: dict[str, str] = Field(default_factory=dict)
    captcha_token: Optional[str] = Field(default=None, max_length=4096)

    @field_validator("full_name")
    @classmethod
    def normalize_name(cls, value: Optional[str]) -> Optional[str]:
        return normalize_public_name(value) if value is not None else None

    @field_validator("whatsapp_number")
    @classmethod
    def normalize_whatsapp(cls, value: Optional[str]) -> Optional[str]:
        return normalize_public_whatsapp(value) if value is not None else None

    @field_validator("selected_options")
    @classmethod
    def validate_selected_options(cls, value: dict[str, str]) -> dict[str, str]:
        if len(value) > 20:
            raise ValueError("Too many selected product options")
        normalized = {}
        for key, raw_option in value.items():
            option_key = str(key or "").strip()
            option = str(raw_option or "").strip()
            if (
                not option_key
                or not option
                or len(option_key) > 60
                or len(option) > 100
                or any(char in option_key or char in option for char in "<>")
            ):
                raise ValueError("Selected product options must be plain text")
            normalized[option_key] = option
        return normalized


class PublicAgizishaProductResponse(BaseModel):
    """Explicit allow-list for the unauthenticated product API."""

    id: str
    name: str
    description: Optional[str] = None
    image_url: Optional[str] = None
    image_urls: list[str] = Field(default_factory=list)
    category: Optional[str] = None
    attributes: dict[str, str | list[str]] = Field(default_factory=dict)
    attribute_images: dict[str, dict[str, str]] = Field(default_factory=dict)
    customer_price: float
    shipping: dict[str, bool | float]
    currency: str
    minimum_order_quantity: int
    variants: list[dict] = Field(default_factory=list)
    agent: Optional[dict] = None


class PublicAgizishaProductsResponse(BaseModel):
    products: list[PublicAgizishaProductResponse]
    matched_agents: list[dict] = Field(default_factory=list)
    empty_reason: Optional[str] = None


def _public_product_query(db: Session):
    """One visibility gate for all public marketplace product responses."""
    return (
        db.query(SourcingProduct)
        .options(
            joinedload(SourcingProduct.batch),
            joinedload(SourcingProduct.goods_type),
            joinedload(SourcingProduct.variants),
        )
        .join(SourcingBatch, SourcingProduct.batch_id == SourcingBatch.id)
        .join(User, User.id == SourcingBatch.agent_id)
        .join(SourcingAgent, SourcingAgent.user_id == User.id)
        .filter(
            SourcingBatch.status == "open",
            SourcingProduct.status == "published",
            User.role == "sourcing_agent",
            User.is_active.is_(True),
            User.status == "active",
            SourcingAgent.status == "verified",
            SourcingAgent.is_verified.is_(True),
        )
    )


def _matched_public_agents(db: Session, query: str) -> list[dict]:
    if not query:
        return []
    rows = (
        db.query(SourcingAgent)
        .join(User, User.id == SourcingAgent.user_id)
        .filter(
            SourcingAgent.status == "verified",
            SourcingAgent.is_verified.is_(True),
            SourcingAgent.is_public.is_(True),
            SourcingAgent.public_handle.isnot(None),
            User.role == "sourcing_agent",
            User.is_active.is_(True),
            User.status == "active",
            or_(
                SourcingAgent.full_name.ilike(f"%{query}%"),
                SourcingAgent.public_handle.ilike(f"%{query}%"),
            ),
        )
        .order_by(SourcingAgent.full_name.asc())
        .limit(12)
        .all()
    )
    return [_public_agent_profile(row) for row in rows]


def _products_with_public_agents(
    db: Session, products: list[SourcingProduct]
) -> list[dict]:
    profiles = _public_agent_profile_map(
        db, list({product.batch.agent_id for product in products if product.batch})
    )
    return [_public_product(product, profiles) for product in products]


class PublicAgizishaOrderResponse(BaseModel):
    id: str
    status: Literal["NEW"]
    message: str


class AgizishaOrderStatusUpdate(BaseModel):
    status: Literal[
        "NEW", "CONTACTED", "QUOTATION_SENT", "CONFIRMED", "COMPLETED", "CANCELLED"
    ]


def _agizisha_operator(
    current_user: User = Depends(get_sourcing_agent),
) -> User:
    """Allow an active sourcing agent or a super-admin governance override."""
    if current_user.role not in {"sourcing_agent", "super_admin"}:
        raise HTTPException(status_code=403, detail="Agizisha access required")
    return current_user


@public_router.get("/products", response_model=PublicAgizishaProductsResponse)
def list_public_agizisha_products(
    limit: int = Query(default=100, ge=1, le=100),
    q: Optional[str] = Query(default=None, min_length=2, max_length=100),
    agent_handle: Optional[str] = Query(default=None, min_length=3, max_length=60),
    db: Session = Depends(get_db),
):
    """Search verified-agent, published products without leaking private data."""
    search = (q or "").strip()
    query = _public_product_query(db)
    if agent_handle:
        query = query.filter(
            SourcingAgent.public_handle == agent_handle.strip().lower()
        )
    if search:
        query = query.filter(
            or_(
                SourcingProduct.name.ilike(f"%{search}%"),
                SourcingProduct.description.ilike(f"%{search}%"),
                SourcingProduct.public_attributes.cast(String).ilike(f"%{search}%"),
                SourcingProduct.goods_type.has(GoodsType.name.ilike(f"%{search}%")),
                SourcingAgent.full_name.ilike(f"%{search}%"),
                SourcingAgent.public_handle.ilike(f"%{search}%"),
            )
        )
    products = query.order_by(SourcingProduct.created_at.desc()).limit(limit).all()
    matched_agents = _matched_public_agents(db, search)
    empty_reason = (
        "agent_has_no_products" if search and matched_agents and not products else None
    )
    return {
        "products": _products_with_public_agents(db, products),
        "matched_agents": matched_agents,
        "empty_reason": empty_reason,
    }


@public_router.get(
    "/products/{product_id}", response_model=PublicAgizishaProductResponse
)
def get_public_agizisha_product(product_id: UUID, db: Session = Depends(get_db)):
    """Return one currently public product through the same strict serializer."""
    product = _public_product_query(db).filter(SourcingProduct.id == product_id).first()
    if not product:
        raise HTTPException(
            status_code=404, detail="This product is not currently available"
        )
    return _products_with_public_agents(db, [product])[0]


@public_router.get(
    "/products/{product_id}/related", response_model=PublicAgizishaProductsResponse
)
def list_related_public_agizisha_products(
    product_id: UUID,
    limit: int = Query(default=4, ge=1, le=8),
    db: Session = Depends(get_db),
):
    """Return safe alternatives from the same curated batch, then its categories."""
    product = _public_product_query(db).filter(SourcingProduct.id == product_id).first()
    if not product:
        raise HTTPException(
            status_code=404, detail="This product is not currently available"
        )

    related = (
        _public_product_query(db)
        .filter(
            SourcingProduct.batch_id == product.batch_id,
            SourcingProduct.id != product.id,
        )
        .order_by(SourcingProduct.created_at.desc())
        .limit(limit)
        .all()
    )
    seen_ids = {item.id for item in related}
    if product.goods_type_id and len(related) < limit:
        category_related = (
            _public_product_query(db)
            .filter(
                SourcingProduct.goods_type_id == product.goods_type_id,
                SourcingProduct.id != product.id,
            )
            .order_by(SourcingProduct.created_at.desc())
            .limit(limit)
            .all()
        )
        related.extend(item for item in category_related if item.id not in seen_ids)
    return {"products": _products_with_public_agents(db, related[:limit])}


@public_router.get("/agents")
def search_public_agizisha_agents(
    q: str = Query(min_length=2, max_length=80),
    limit: int = Query(default=12, ge=1, le=24),
    db: Session = Depends(get_db),
):
    """Search-first agent directory suitable for thousands of profiles."""
    query = q.strip()
    rows = (
        db.query(SourcingAgent)
        .join(User, User.id == SourcingAgent.user_id)
        .filter(
            SourcingAgent.status == "verified",
            SourcingAgent.is_verified.is_(True),
            SourcingAgent.is_public.is_(True),
            SourcingAgent.public_handle.isnot(None),
            User.role == "sourcing_agent",
            User.is_active.is_(True),
            User.status == "active",
            or_(
                SourcingAgent.full_name.ilike(f"%{query}%"),
                SourcingAgent.public_handle.ilike(f"%{query}%"),
                SourcingAgent.niche.ilike(f"%{query}%"),
                SourcingAgent.location.ilike(f"%{query}%"),
            ),
        )
        .order_by(SourcingAgent.full_name.asc())
        .limit(limit)
        .all()
    )
    return {"agents": [_public_agent_profile(row) for row in rows]}


@public_router.get("/agents/{handle}")
def get_public_agizisha_agent_storefront(handle: str, db: Session = Depends(get_db)):
    """Public, safe agent profile with currently open Agizisha products."""
    normalized_handle = handle.strip().lower()
    profile = (
        db.query(SourcingAgent)
        .join(User, User.id == SourcingAgent.user_id)
        .filter(
            SourcingAgent.public_handle == normalized_handle,
            SourcingAgent.status == "verified",
            SourcingAgent.is_verified.is_(True),
            SourcingAgent.is_public.is_(True),
            User.role == "sourcing_agent",
            User.is_active.is_(True),
            User.status == "active",
        )
        .first()
    )
    if not profile:
        raise HTTPException(
            status_code=404, detail="This sourcing agent is not publicly available"
        )

    products = (
        _public_product_query(db)
        .filter(SourcingBatch.agent_id == profile.user_id)
        .order_by(SourcingProduct.created_at.desc())
        .limit(100)
        .all()
    )
    storefront_agent = _public_agent_profile(profile) or {}
    storefront_agent.update(
        {
            "bio": profile.bio,
            "niche": profile.niche,
            "location": profile.location,
            "years_experience": profile.years_experience,
        }
    )
    return {
        "agent": storefront_agent,
        "products": [
            _public_product(product, {profile.user_id: profile}) for product in products
        ],
    }


def _validate_selected_options(
    payload: dict[str, str], product: SourcingProduct
) -> dict[str, str]:
    """Only persist choices which the product's saved public attributes allow."""
    attributes = _safe_public_attributes(product)
    selectable = {
        key: value for key, value in attributes.items() if isinstance(value, list)
    }
    unknown = set(payload) - set(selectable)
    if unknown:
        raise HTTPException(
            status_code=422, detail="One or more selected options are invalid"
        )
    for key, options in selectable.items():
        if len(options) > 1 and key not in payload:
            raise HTTPException(status_code=422, detail=f"Please select {key}")
        if key in payload and payload[key] not in options:
            raise HTTPException(status_code=422, detail=f"Invalid {key} selection")
    return payload


@public_router.post(
    "/orders",
    status_code=status.HTTP_201_CREATED,
    response_model=PublicAgizishaOrderResponse,
)
def create_agizisha_order(
    payload: AgizishaOrderCreate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_authenticated_user),
    workspace: Optional[str] = Header(None, alias="X-Sahajomy-Workspace"),
    company_header: Optional[str] = Header(None, alias="X-Sahajomy-Company"),
):
    """Create a public request and notify only the owning sourcing agent."""
    verify_agizisha_captcha(
        payload.captcha_token, request.client.host if request.client else None
    )

    product = (
        _public_product_query(db)
        .options(joinedload(SourcingProduct.batch).joinedload(SourcingBatch.agent))
        .filter(SourcingProduct.id == payload.product_id)
        .first()
    )
    if not product:
        raise HTTPException(
            status_code=404, detail="This product is not currently available"
        )
    selected_options = _validate_selected_options(payload.selected_options, product)
    variant = None
    if product.variants:
        if not payload.variant_id:
            raise HTTPException(
                status_code=422, detail="Please select an available product variant."
            )
        variant = next(
            (item for item in product.variants if item.id == payload.variant_id), None
        )
        if not variant or not variant.is_active or variant.stock_quantity <= 0:
            raise HTTPException(
                status_code=422, detail="Selected product variant is unavailable."
            )
        selected_variant_options = {
            key: selected_options.get(key) for key in (variant.option_values or {})
        }
        if variant.option_values != selected_variant_options:
            raise HTTPException(
                status_code=422,
                detail="Selected options do not match that product variant.",
            )
    elif payload.variant_id:
        raise HTTPException(
            status_code=422, detail="This product has no selectable variants."
        )
    if payload.quantity and payload.quantity < (product.minimum_order_quantity or 1):
        raise HTTPException(
            status_code=422,
            detail=(
                f"Minimum order quantity for this product is "
                f"{product.minimum_order_quantity or 1}"
            ),
        )

    # An authenticated identity becomes the customer only through the personal
    # workspace. The global role describes operational access, not whether the
    # person is acting as a buyer for this request.
    if current_user:
        acting_personally = workspace == "personal" and not company_header
        if not acting_personally:
            raise HTTPException(
                status_code=403,
                detail="Switch to My Sahajomy Account to place an Agizisha order.",
            )
        try:
            customer_name = normalize_public_name(current_user.name or "")
            account_phone = current_user.phone_number
            if not account_phone:
                account_phone = current_user.secure_phone
            whatsapp_number = normalize_public_whatsapp(account_phone or "")
        except ValueError as exc:
            raise HTTPException(
                status_code=422,
                detail="Your account needs a valid name and WhatsApp number before ordering.",
            ) from exc
    else:
        if not payload.full_name or not payload.whatsapp_number:
            raise HTTPException(
                status_code=422,
                detail="Full name and WhatsApp number are required for guest orders.",
            )
        customer_name = payload.full_name
        whatsapp_number = payload.whatsapp_number

    recent_attempts = (
        db.query(func.count(AgizishaOrder.id))
        .filter(
            AgizishaOrder.whatsapp_number == whatsapp_number,
            AgizishaOrder.created_at >= datetime.utcnow() - timedelta(hours=1),
        )
        .scalar()
        or 0
    )
    if recent_attempts >= settings.AGIZISHA_ORDER_MAX_PER_WHATSAPP_PER_HOUR:
        # Avoid confirming whether the number has submitted a particular order.
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many order requests. Please try again later.",
        )

    agent = _active_assigned_agent(product)
    order = AgizishaOrder(
        product_id=product.id,
        product_variant_id=variant.id if variant else None,
        sourcing_agent_id=agent.id if agent else None,
        customer_name=customer_name,
        whatsapp_number=whatsapp_number,
        quantity=payload.quantity,
        quoted_unit_price=(
            variant.price_per_unit if variant else product.price_per_unit
        ),
        selected_options=selected_options,
        status="NEW",
    )
    db.add(order)
    db.flush()

    if agent:
        log_action(
            db=db,
            action="AGIZISHA_ORDER_ASSIGNED",
            user_id=agent.id,
            entity_type="agizisha_order",
            entity_id=order.id,
            metadata={"product_id": str(product.id)},
        )
        create_notification(
            db=db,
            user_id=agent.id,
            notification_type="agizisha_order_created",
            message=(
                f"New Agizisha Order Received: {product.name} — "
                f"{order.customer_name} ({order.whatsapp_number})"
            ),
            priority="info",
            target_type="agizisha_order",
            target_id=order.id,
        )
    else:
        # Products should always inherit a batch owner. If legacy/bad data has
        # no eligible owner, retain the request and send it only to governance.
        super_admins = (
            db.query(User)
            .filter(
                User.role == "super_admin",
                User.is_active.is_(True),
                User.status == "active",
            )
            .all()
        )
        for super_admin in super_admins:
            create_notification(
                db=db,
                user_id=super_admin.id,
                notification_type="agizisha_order_unassigned",
                message=(
                    f"Unassigned Agizisha order: {product.name} — "
                    f"{order.customer_name} ({order.whatsapp_number})"
                ),
                priority="warning",
                target_type="agizisha_order",
                target_id=order.id,
            )

    log_action(
        db=db,
        action="AGIZISHA_ORDER_CREATED",
        entity_type="agizisha_order",
        entity_id=order.id,
        # Do not put the customer's phone number into the broad audit metadata.
        metadata={"product_id": str(product.id), "assigned": bool(agent)},
    )
    db.commit()
    db.refresh(order)

    return {
        "id": str(order.id),
        "status": order.status,
        "message": "Your order request has been sent. The sourcing team will contact you.",
    }


@agent_router.get("")
def list_my_agizisha_orders(
    order_status: Optional[str] = Query(default=None, alias="status"),
    limit: int = Query(default=100, ge=1, le=100),
    db: Session = Depends(get_db),
    agent: User = Depends(_agizisha_operator),
):
    if order_status and order_status not in AGIZISHA_STATUSES:
        raise HTTPException(status_code=400, detail="Invalid Agizisha order status")

    query = db.query(AgizishaOrder).options(joinedload(AgizishaOrder.product))
    if agent.role != "super_admin":
        query = query.filter(AgizishaOrder.sourcing_agent_id == agent.id)
    if order_status:
        query = query.filter(AgizishaOrder.status == order_status)

    orders = query.order_by(AgizishaOrder.created_at.desc()).limit(limit).all()
    return {"orders": [_agent_order(order) for order in orders]}


@agent_router.get("/{order_id}")
def get_my_agizisha_order(
    order_id: UUID,
    db: Session = Depends(get_db),
    agent: User = Depends(_agizisha_operator),
):
    query = (
        db.query(AgizishaOrder)
        .options(joinedload(AgizishaOrder.product))
        .filter(AgizishaOrder.id == order_id)
    )
    if agent.role != "super_admin":
        query = query.filter(AgizishaOrder.sourcing_agent_id == agent.id)
    order = query.first()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found or access denied")
    return _agent_order(order)


@agent_router.patch("/{order_id}/status")
def update_my_agizisha_order_status(
    order_id: UUID,
    payload: AgizishaOrderStatusUpdate,
    db: Session = Depends(get_db),
    agent: User = Depends(_agizisha_operator),
):
    query = db.query(AgizishaOrder).filter(AgizishaOrder.id == order_id)
    if agent.role != "super_admin":
        query = query.filter(AgizishaOrder.sourcing_agent_id == agent.id)
    order = query.first()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found or access denied")

    if order.status == payload.status:
        return {"order": _agent_order(order), "message": "Order status is unchanged"}

    previous_status = order.status
    order.status = payload.status
    log_action(
        db=db,
        action="AGIZISHA_ORDER_STATUS_UPDATED",
        user_id=agent.id,
        entity_type="agizisha_order",
        entity_id=order.id,
        metadata={"from": previous_status, "to": payload.status},
    )
    db.commit()
    db.refresh(order)
    return {"order": _agent_order(order), "message": "Order status updated"}
