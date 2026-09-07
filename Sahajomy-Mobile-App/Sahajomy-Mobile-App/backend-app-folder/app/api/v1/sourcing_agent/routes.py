"""
Sourcing Agent API.
Can: create batches, upload products, book CBM, share batch link, track shipment, view commission,
     book express air cargo.
Cannot: create containers, set CBM pricing, mark goods collected/held, see other agents' batches.
"""

import json
import logging
import math
import os
import re
import secrets
import tempfile
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from io import BytesIO
from typing import Any, Dict, List, Literal, Optional
from urllib.parse import urlparse
from uuid import UUID

import cloudinary.utils
import httpx
from app.core.audit import log_action
from app.core.cloudinary import (
    build_optimized_cloudinary_image_url,
    configure_cloudinary,
    upload_to_cloudinary,
)
from app.core.config import settings
from app.core.dependencies import get_sourcing_agent
from app.core.reference_ids import build_display_reference
from app.core.upload_validation import validated_image_format
from app.core.url_builder import build_shared_batch_link
from app.core.utils import generate_invoice_number, generate_receipt_number
from app.database import get_db
from app.models.air_cargo import AirCargoRate, ExpressAirCargoBooking
from app.models.container import (
    Container,
    GoodsType,
    GoodsTypeAttributeTemplate,
    SeaBooking,
    SeaBookingGoods,
)
from app.models.finance import AuditLog, CommissionSettings, Notification, Receipt
from app.models.packing_list import PackingList, PackingListItem
from app.models.sourcing import (
    BatchShareToken,
    SourcingBatch,
    SourcingOrder,
    SourcingOrderItem,
    SourcingProduct,
    SourcingProductVariant,
)
from app.models.sourcing_agent import SourcingAgent
from app.models.user import User
from app.schemas.packing_list import (
    GeneratePackingListResponse,
    PackingListCreate,
    PackingListItemCreate,
    PackingListItemResponse,
    PackingListItemUpdate,
    PackingListResponse,
    PackingListSummaryResponse,
)
from app.services.air_cargo_pricing import (
    DEFAULT_AIR_CARGO_ROUTE,
    calculate_rate_total,
    get_air_cargo_goods_policy,
    get_matching_rate,
    serialize_rate,
)
from app.services.booking_notifications import notify_container_booking_created
from app.services.china_warehouse_address import is_china_warehouse
from app.services.company_service_governance import (
    company_service_is_bookable,
    require_company_service_bookable,
)
from app.services.customer_china_addresses import (
    copy_ready_address,
    ensure_customer_china_address,
    prepare_user_air_china_address,
)
from app.services.document_branding import (
    operator_document_branding,
    sourcing_agent_document_branding,
)
from app.services.document_download import stream_safe_document
from app.services.document_generation_service import DocumentGenerationService
from app.services.instagram import InstagramService
from app.services.packing_list_service import PackingListService
from app.services.shipment_orders_service import (
    ensure_shipment_order_for_air_booking,
    ensure_shipment_order_for_sea_booking,
)
from app.services.shipping_mark import (
    build_printable_label,
    create_shipping_mark,
    generate_shipping_mark_code,
)
from app.services.tracking import TrackingService
from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field, HttpUrl, field_validator, model_validator
from sqlalchemy import func
from sqlalchemy.orm import Session, joinedload

# Configure logging
logger = logging.getLogger(__name__)

router = APIRouter(prefix="/sourcing_agent", tags=["Sourcing Agent"])

# Initialize services
instagram_service = InstagramService()
configure_cloudinary()


def _get_booked_cbm_map(db: Session, container_ids: list[str]) -> dict[str, float]:
    if not container_ids:
        return {}

    rows = (
        db.query(
            SeaBooking.container_id,
            func.coalesce(func.sum(SeaBooking.cbm_booked), 0).label("booked_cbm"),
        )
        .filter(SeaBooking.container_id.in_(container_ids))
        .group_by(SeaBooking.container_id)
        .all()
    )
    return {
        str(container_id): float(booked_cbm or 0) for container_id, booked_cbm in rows
    }


def _build_document_fetch_candidates(document_url: str) -> List[str]:
    """Return candidate URLs, including a repair path for legacy bad public IDs."""
    raw_url = (document_url or "").strip()
    if not raw_url:
        return []

    candidates = [raw_url]
    parsed = urlparse(raw_url)
    path_parts = [part for part in (parsed.path or "").split("/") if part]

    if len(path_parts) >= 4:
        first, second, repeated, filename = path_parts[-4:]
        has_legacy_duplication = repeated == first and filename.startswith(f"{second}_")
        if has_legacy_duplication:
            repaired_parts = path_parts[:-2] + [filename]
            repaired_path = "/" + "/".join(repaired_parts)
            repaired_url = parsed._replace(path=repaired_path).geturl()
            if repaired_url not in candidates:
                candidates.append(repaired_url)

    cloudinary_signed_url = _build_cloudinary_private_download_url(raw_url)
    if cloudinary_signed_url and cloudinary_signed_url not in candidates:
        candidates.append(cloudinary_signed_url)

    return candidates


def _build_cloudinary_private_download_url(document_url: str) -> Optional[str]:
    parsed = urlparse((document_url or "").strip())
    host = (parsed.hostname or "").lower()
    if not (host == "cloudinary.com" or host.endswith(".cloudinary.com")):
        return None

    path_parts = [part for part in (parsed.path or "").split("/") if part]
    resource_index = next(
        (
            idx
            for idx, part in enumerate(path_parts)
            if part in {"image", "video", "raw"}
        ),
        None,
    )
    if resource_index is None or len(path_parts) <= resource_index + 3:
        return None

    delivery_type = path_parts[resource_index + 1]
    version_index = next(
        (
            idx
            for idx in range(resource_index + 2, len(path_parts))
            if re.fullmatch(r"v\d+", path_parts[idx])
        ),
        None,
    )
    if version_index is None or version_index >= len(path_parts) - 1:
        return None

    public_id_with_ext = "/".join(path_parts[version_index + 1 :])
    if "." not in public_id_with_ext:
        return None
    _, file_format = public_id_with_ext.rsplit(".", 1)

    configure_cloudinary()
    try:
        return cloudinary.utils.private_download_url(
            public_id_with_ext,
            file_format,
            resource_type=path_parts[resource_index],
            type=delivery_type,
            attachment=False,
            expires_at=int(datetime.utcnow().timestamp()) + 600,
        )
    except Exception:
        return None


def _normalize_social_link(value: Optional[str], platform: str) -> Optional[str]:
    raw = (value or "").strip()
    if not raw:
        return None
    if raw.startswith("http://") or raw.startswith("https://"):
        return raw
    username = raw.lstrip("@")
    if not username:
        return None
    if platform == "instagram":
        return f"https://instagram.com/{username}"
    if platform == "tiktok":
        return f"https://www.tiktok.com/@{username}"
    return None


def _resolve_order_customer_name(order: SourcingOrder) -> str:
    if order.customer and order.customer.name:
        return order.customer.name
    if order.guest and order.guest.name:
        return order.guest.name
    return "Unknown customer"


def _compact_names(names: set[str], max_names: int = 3) -> str:
    if not names:
        return "Unknown customer"
    ordered = sorted({name.strip() for name in names if str(name).strip()})
    if not ordered:
        return "Unknown customer"
    if len(ordered) <= max_names:
        return ", ".join(ordered)
    shown = ", ".join(ordered[:max_names])
    return f"{shown} +{len(ordered) - max_names} more"


def _get_or_create_order_receipt(
    db: Session,
    order: SourcingOrder,
    issued_by=None,
) -> Receipt:
    receipt = (
        db.query(Receipt)
        .filter(Receipt.order_id == order.id)
        .order_by(Receipt.generated_at.desc())
        .first()
    )
    if receipt:
        if receipt.currency is None:
            receipt.currency = order.currency or (
                order.batch.currency if order.batch else None
            )
        if receipt.amount is None:
            receipt.amount = order.total_product_amount or 0
        if not order.receipt_number:
            order.receipt_number = receipt.receipt_number
        if hasattr(order, "receipt_token") and not order.receipt_token:
            order.receipt_token = receipt.receipt_token
        return receipt

    receipt_number = order.receipt_number or generate_receipt_number()
    receipt = Receipt(
        order_id=order.id,
        receipt_number=receipt_number,
        receipt_token=secrets.token_urlsafe(32),
        amount=order.total_product_amount or 0,
        currency=order.currency or (order.batch.currency if order.batch else None),
        status="issued",
        issued_by=issued_by,
    )
    db.add(receipt)
    db.flush()

    order.receipt_number = receipt.receipt_number
    if hasattr(order, "receipt_token"):
        order.receipt_token = receipt.receipt_token
    return receipt


def _latest_invoice_log_for_orders(db: Session, order_ids: list) -> dict[str, dict]:
    if not order_ids:
        return {}

    logs = (
        db.query(AuditLog)
        .filter(
            AuditLog.entity_type == "sourcing_order",
            AuditLog.entity_id.in_(order_ids),
            AuditLog.action == "ORDER_INVOICE_GENERATED",
        )
        .order_by(AuditLog.created_at.desc())
        .all()
    )

    latest_by_order: dict[str, dict] = {}
    for log in logs:
        key = str(log.entity_id)
        if key in latest_by_order:
            continue
        payload = log.extra_data if isinstance(log.extra_data, dict) else {}
        latest_by_order[key] = payload
    return latest_by_order


def _build_packing_list_payload(db: Session, packing_list: PackingList) -> dict:
    batch = (
        db.query(SourcingBatch)
        .options(joinedload(SourcingBatch.agent))
        .filter(SourcingBatch.id == packing_list.batch_id)
        .first()
    )

    orders = (
        db.query(SourcingOrder)
        .options(
            joinedload(SourcingOrder.customer),
            joinedload(SourcingOrder.guest),
            joinedload(SourcingOrder.items).joinedload(SourcingOrderItem.product),
        )
        .filter(SourcingOrder.batch_id == packing_list.batch_id)
        .all()
    )

    item_name_to_people: dict[str, set[str]] = defaultdict(set)
    item_name_to_order_refs: dict[str, set[str]] = defaultdict(set)
    for order in orders:
        customer_name = _resolve_order_customer_name(order)
        order_ref = build_display_reference(
            "sourcing_order", order.id, order.created_at
        )
        for order_item in order.items:
            product_name = (
                order_item.product.name
                if order_item.product and order_item.product.name
                else None
            )
            if not product_name:
                continue
            key = product_name.strip().lower()
            if key:
                item_name_to_people[key].add(customer_name)
                item_name_to_order_refs[key].add(order_ref)

    agent_profile = (
        db.query(SourcingAgent).filter(SourcingAgent.user_id == batch.agent_id).first()
        if batch
        else None
    )
    if agent_profile and agent_profile.full_name:
        agent_name = agent_profile.full_name
    elif batch and batch.agent and batch.agent.name:
        agent_name = batch.agent.name
    else:
        agent_name = "Unknown sourcing agent"

    agent_phone = (
        (agent_profile.whatsapp or agent_profile.phone)
        if agent_profile
        else (batch.agent.phone_number if batch and batch.agent else None)
    )

    payload_items = []
    for item in packing_list.items:
        key = (item.item_name or "").strip().lower()
        payload_items.append(
            {
                "id": item.id,
                "item_name": item.item_name,
                "item_picture": item.item_picture,
                "price_per_piece": float(item.price_per_piece),
                "item_code": item.item_code,
                "cartons": item.cartons,
                "items_per_carton": item.items_per_carton,
                "cbm_per_carton": (
                    float(item.cbm_per_carton)
                    if item.cbm_per_carton is not None
                    else None
                ),
                "kilogram_per_carton": (
                    float(item.kilogram_per_carton)
                    if item.kilogram_per_carton is not None
                    else None
                ),
                "total_quantity": item.total_quantity,
                "total_amount": (
                    float(item.total_amount) if item.total_amount is not None else None
                ),
                "total_cbm": (
                    float(item.total_cbm) if item.total_cbm is not None else None
                ),
                "total_kilogram": (
                    float(item.total_kilogram)
                    if item.total_kilogram is not None
                    else None
                ),
                "ordered_by": _compact_names(item_name_to_people.get(key, set())),
                "order_references": sorted(item_name_to_order_refs.get(key, set())),
                "created_at": item.created_at,
                "updated_at": item.updated_at,
            }
        )

    return {
        "id": packing_list.id,
        "batch_id": packing_list.batch_id,
        "created_by": packing_list.created_by,
        "name": packing_list.name,
        "description": packing_list.description,
        "qr_code_url": packing_list.qr_code_url,
        "reference": build_display_reference(
            "packing_list", packing_list.id, packing_list.created_at
        ),
        "batch_title": batch.title if batch else None,
        "batch_status": batch.status if batch else None,
        "currency": (batch.currency if batch and batch.currency else "TZS"),
        "agent_details": {
            "name": agent_name,
            "phone_or_whatsapp": agent_phone,
            "instagram": (
                _normalize_social_link(agent_profile.instagram, "instagram")
                if agent_profile
                else None
            ),
            "tiktok": (
                _normalize_social_link(agent_profile.tiktok, "tiktok")
                if agent_profile
                else None
            ),
        },
        "issuer": sourcing_agent_document_branding(db, batch.agent),
        "created_at": packing_list.created_at,
        "updated_at": packing_list.updated_at,
        "items": payload_items,
    }


def _export_packing_list_document(
    db: Session, packing_list: PackingList, export_format: str
) -> tuple[bytes, str, str]:
    payload = _build_packing_list_payload(db, packing_list)
    generated_at = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")
    reference = payload.get("reference") or str(packing_list.id)
    safe_ref = str(reference).replace(" ", "-")
    metadata = {
        "issuer": payload.get("issuer") or payload.get("agent_details") or {},
        "reference": reference,
        "batch_title": payload.get("batch_title"),
        "status": payload.get("batch_status"),
        "currency": payload.get("currency") or "TZS",
        "agent_name": (payload.get("agent_details") or {}).get("name"),
        "agent_phone_or_whatsapp": (payload.get("agent_details") or {}).get(
            "phone_or_whatsapp"
        ),
        "instagram": (payload.get("agent_details") or {}).get("instagram"),
        "tiktok": (payload.get("agent_details") or {}).get("tiktok"),
        "generated_at": generated_at,
    }
    items_data = [
        {
            "item_name": item.get("item_name"),
            "item_code": item.get("item_code"),
            "item_picture": item.get("item_picture"),
            "price_per_piece": item.get("price_per_piece"),
            "cartons": item.get("cartons"),
            "items_per_carton": item.get("items_per_carton"),
            "total_quantity": item.get("total_quantity"),
            "total_amount": item.get("total_amount"),
            "total_cbm": item.get("total_cbm"),
            "total_kilogram": item.get("total_kilogram"),
            "ordered_by": item.get("ordered_by"),
            "order_references": item.get("order_references") or [],
            "notes": "",
        }
        for item in payload.get("items") or []
    ]

    if export_format == "pdf":
        content = DocumentGenerationService.generate_packing_list_pdf_detailed(
            metadata, items_data
        )
        filename = f"packing-list-{safe_ref}.pdf"
        media_type = "application/pdf"
    else:
        content = DocumentGenerationService.generate_packing_list_excel_detailed(
            metadata, items_data
        )
        filename = f"packing-list-{safe_ref}.xlsx"
        media_type = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"

    return content, filename, media_type


# ─── Enhanced Schemas with Validation ───────────────────


class BatchCreate(BaseModel):
    title: str = Field(..., min_length=3, max_length=200)
    description: Optional[str] = Field(None, max_length=1000)
    currency: str = Field("TZS")
    shipping_method: str = Field("PER_CBM")
    shipping_fee_per_cbm: Optional[float] = Field(None, ge=0, le=100000000)

    @field_validator("title")
    @classmethod
    def validate_title(cls, v):
        if not v.strip():
            raise ValueError("Title cannot be empty")
        return v.strip()

    @field_validator("currency")
    @classmethod
    def validate_currency(cls, v):
        supported_currencies = {"TZS", "RMB", "USD"}
        currency_code = (v or "TZS").upper()
        if currency_code not in supported_currencies:
            raise ValueError(f"Currency must be one of {supported_currencies}")
        return currency_code

    @field_validator("shipping_method")
    @classmethod
    def validate_shipping_method(cls, v):
        shipping_method = str(v or "PER_CBM").upper()
        if shipping_method not in {"PER_CBM", "FREE_SHIPPING"}:
            raise ValueError("Shipping method must be PER_CBM or FREE_SHIPPING")
        return shipping_method

    @model_validator(mode="after")
    def validate_shipping_fee_per_cbm(self):
        if self.shipping_method == "FREE_SHIPPING":
            self.shipping_fee_per_cbm = 0.0
            return self
        if self.shipping_fee_per_cbm is None or self.shipping_fee_per_cbm <= 0:
            raise ValueError("Shipping fee per CBM must be greater than 0")
        self.shipping_fee_per_cbm = round(float(self.shipping_fee_per_cbm), 2)
        return self


class BatchUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=3, max_length=200)
    description: Optional[str] = Field(None, max_length=1000)

    @field_validator("title")
    @classmethod
    def validate_title(cls, v):
        if v is not None and not v.strip():
            raise ValueError("Title cannot be empty")
        return v.strip() if v else v


def _normalize_public_attributes(value: Dict[str, Any]) -> Dict[str, Any]:
    if not isinstance(value, dict) or len(value) > 20:
        raise ValueError("Provide up to 20 public product attributes")

    normalized = {}
    attribute_names = set()
    for raw_key, raw_value in value.items():
        key = str(raw_key or "").strip()
        if (
            not key
            or key.startswith("_")
            or len(key) > 60
            or any(char in key for char in "<>")
        ):
            raise ValueError("Attribute names must be plain text under 60 characters")

        if isinstance(raw_value, dict) and raw_value.get("attribute_type"):
            normalized_custom = _normalize_structured_product_attribute(key, raw_value)
            comparable_name = _comparable_attribute_name(normalized_custom["label"])
            if comparable_name in attribute_names:
                raise ValueError(
                    "Product features cannot use duplicate attribute names"
                )
            attribute_names.add(comparable_name)
            normalized[key] = normalized_custom
            continue

        values = raw_value if isinstance(raw_value, list) else [raw_value]
        if not values or len(values) > 30:
            raise ValueError(f"{key} must have between 1 and 30 values")

        clean_values = []
        for raw_option in values:
            option = str(raw_option or "").strip()
            if not option or len(option) > 100 or any(char in option for char in "<>"):
                raise ValueError(f"{key} contains an invalid value")
            if option not in clean_values:
                clean_values.append(option)
        comparable_name = _comparable_attribute_name(key)
        if comparable_name in attribute_names:
            raise ValueError("Product features cannot use duplicate attribute names")
        attribute_names.add(comparable_name)
        normalized[key] = (
            clean_values if isinstance(raw_value, list) else clean_values[0]
        )
    return normalized


CUSTOM_ATTRIBUTE_TYPES = {
    "text",
    "number",
    "number_unit",
    "color",
    "select",
    "multiselect",
    "boolean",
    "dimensions",
}


def _comparable_attribute_name(value: Any) -> str:
    """Normalize obvious spelling variants so Color/colour cannot be duplicated."""
    normalized = re.sub(r"[^a-z0-9]", "", str(value or "").casefold())
    return normalized.replace("colour", "color")


def _clean_attribute_text(value: Any, field_name: str, max_length: int = 100) -> str:
    clean_value = str(value or "").strip()
    if (
        not clean_value
        or len(clean_value) > max_length
        or any(char in clean_value for char in "<>")
    ):
        raise ValueError(f"{field_name} must be plain text")
    return clean_value


def _normalize_structured_product_attribute(
    key: str, value: Dict[str, Any]
) -> Dict[str, Any]:
    """Validate one custom feature stored in the existing JSONB attribute field."""
    label = _clean_attribute_text(value.get("label") or key, "Attribute name", 60)
    attribute_type = str(value.get("attribute_type") or "").strip().lower()
    if attribute_type not in CUSTOM_ATTRIBUTE_TYPES:
        raise ValueError("Unsupported product feature type")

    raw_feature_value = value.get("value")
    unit = value.get("unit")
    normalized: Dict[str, Any] = {
        "label": label,
        "attribute_type": attribute_type,
        "is_custom": True,
        "display_order": int(value.get("display_order", 0)),
    }
    if normalized["display_order"] < 0 or normalized["display_order"] > 1000:
        raise ValueError("Product feature display order is invalid")

    if attribute_type in {"text", "select"}:
        normalized["value"] = _clean_attribute_text(raw_feature_value, label)
    elif attribute_type in {"color", "multiselect"}:
        values = (
            raw_feature_value
            if isinstance(raw_feature_value, list)
            else [raw_feature_value]
        )
        if not values or len(values) > 30:
            raise ValueError(f"{label} must have between 1 and 30 values")
        normalized_values = []
        for item in values:
            clean_item = _clean_attribute_text(item, label)
            if clean_item not in normalized_values:
                normalized_values.append(clean_item)
        normalized["value"] = normalized_values
    elif attribute_type in {"number", "number_unit"}:
        numeric_value = _clean_attribute_text(raw_feature_value, label)
        try:
            if not math.isfinite(float(numeric_value)):
                raise ValueError
        except (TypeError, ValueError):
            raise ValueError(f"{label} must be a valid number")
        normalized["value"] = numeric_value
        if attribute_type == "number_unit":
            normalized["unit"] = _clean_attribute_text(unit, f"{label} unit", 20)
    elif attribute_type == "boolean":
        if isinstance(raw_feature_value, bool):
            normalized["value"] = "Yes" if raw_feature_value else "No"
        elif str(raw_feature_value or "").strip().casefold() in {"yes", "true"}:
            normalized["value"] = "Yes"
        elif str(raw_feature_value or "").strip().casefold() in {"no", "false"}:
            normalized["value"] = "No"
        else:
            raise ValueError(f"{label} must be Yes or No")
    else:  # dimensions
        if not isinstance(raw_feature_value, dict):
            raise ValueError(f"{label} must include length, width, and height")
        dimensions = {}
        for dimension in ("length", "width", "height"):
            dimension_value = _clean_attribute_text(
                raw_feature_value.get(dimension), f"{label} {dimension}"
            )
            try:
                if not math.isfinite(float(dimension_value)):
                    raise ValueError
            except (TypeError, ValueError):
                raise ValueError(f"{label} {dimension} must be a valid number")
            dimensions[dimension] = dimension_value
        normalized["value"] = dimensions
        normalized["unit"] = _clean_attribute_text(unit, f"{label} unit", 20)

    return normalized


def _attribute_value(value: Any) -> Any:
    """Read structured custom values while preserving legacy template values."""
    if isinstance(value, dict) and value.get("attribute_type"):
        return value.get("value")
    return value


def _normalize_attribute_image_map(
    value: Dict[str, Any],
    public_attributes: Dict[str, Any],
    image_url: str,
    additional_image_urls: List[str],
) -> Dict[str, Dict[str, str]]:
    """Keep only valid selectable-feature values linked to this product's gallery."""
    if not isinstance(value, dict) or len(value) > 20:
        raise ValueError("Provide image links for up to 20 product features")
    gallery = {
        str(url).strip()
        for url in [image_url, *(additional_image_urls or [])]
        if str(url or "").strip()
    }
    normalized: Dict[str, Dict[str, str]] = {}
    total_links = 0
    for raw_key, raw_options in value.items():
        key = str(raw_key or "").strip()
        allowed_values = _attribute_value(public_attributes.get(key))
        if key not in public_attributes or not isinstance(allowed_values, list):
            raise ValueError(
                "Specification images must use a selectable product feature"
            )
        if not isinstance(raw_options, dict) or len(raw_options) > 30:
            raise ValueError(f"{key} has invalid specification image links")
        allowed = {str(option).strip() for option in allowed_values}
        option_map: Dict[str, str] = {}
        for raw_option, raw_url in raw_options.items():
            option = str(raw_option or "").strip()
            url = str(raw_url or "").strip()
            if not option or option not in allowed:
                raise ValueError(f"Invalid {key} image option")
            if not url:
                continue
            if len(url) > 2048 or url not in gallery:
                raise ValueError(
                    "Specification images must come from this product's gallery"
                )
            option_map[option] = url
            total_links += 1
            if total_links > 200:
                raise ValueError("Provide up to 200 specification image links")
        if option_map:
            normalized[key] = option_map
    return normalized


def _serialized_attribute_image_map(
    product: SourcingProduct,
) -> Dict[str, Dict[str, str]]:
    return {
        key: {
            option: build_optimized_cloudinary_image_url(url)
            for option, url in option_map.items()
        }
        for key, option_map in (product.attribute_image_map or {}).items()
        if isinstance(option_map, dict)
    }


class ProductVariantInput(BaseModel):
    option_values: Dict[str, str] = Field(default_factory=dict)
    price_per_unit: float = Field(..., gt=0, le=100000000)
    stock_quantity: int = Field(..., ge=0, le=100000000)
    is_active: bool = True

    @field_validator("option_values")
    @classmethod
    def validate_option_values(cls, value):
        normalized = {}
        for key, raw_value in (value or {}).items():
            clean_key = str(key or "").strip()
            clean_value = str(raw_value or "").strip()
            if (
                not clean_key
                or not clean_value
                or len(clean_key) > 60
                or len(clean_value) > 100
            ):
                raise ValueError("Variant options must be plain text")
            normalized[clean_key] = clean_value
        return normalized


class ProductCreate(BaseModel):
    goods_type_id: UUID
    name: str = Field(..., min_length=1, max_length=200)
    description: Optional[str] = Field(None, max_length=1000)
    cbm_per_unit: Optional[float] = Field(None, ge=0, le=1000000)
    price_per_unit: float = Field(..., gt=0, le=100000000)
    minimum_order_quantity: int = Field(1, ge=1, le=100000000)
    image_url: str = Field(..., description="Permanent Cloudinary URL")
    additional_image_urls: List[str] = Field(default_factory=list, max_length=7)
    public_attributes: Dict[str, Any] = Field(default_factory=dict)
    attribute_image_map: Dict[str, Dict[str, str]] = Field(default_factory=dict)
    variants: List[ProductVariantInput] = Field(default_factory=list, max_length=100)
    status: Literal["draft", "published"] = "draft"

    @field_validator("image_url")
    @classmethod
    def validate_image_url(cls, v):
        if not v.startswith(("http://", "https://")):
            raise ValueError("Invalid image URL format")
        # Optional: Check if it's a Cloudinary URL
        if "cloudinary.com" not in v and settings.ENVIRONMENT == "production":
            logger.warning(f"Non-Cloudinary image URL used: {v}")
        return v

    @field_validator("additional_image_urls")
    @classmethod
    def validate_additional_image_urls(cls, value):
        normalized = []
        for image_url in value or []:
            image_url = str(image_url or "").strip()
            if not image_url.startswith(("http://", "https://")):
                raise ValueError("Additional images must use valid HTTP(S) URLs")
            if image_url not in normalized:
                normalized.append(image_url)
        return normalized

    @field_validator("public_attributes")
    @classmethod
    def validate_public_attributes(cls, value):
        return _normalize_public_attributes(value)


class ProductUpdate(BaseModel):
    name: Optional[str] = Field(default=None, min_length=1, max_length=200)
    description: Optional[str] = Field(default=None, max_length=1000)
    cbm_per_unit: Optional[float] = Field(default=None, ge=0, le=1000000)
    price_per_unit: Optional[float] = Field(default=None, gt=0, le=100000000)
    minimum_order_quantity: Optional[int] = Field(default=None, ge=1, le=100000000)
    image_url: Optional[str] = None
    additional_image_urls: Optional[List[str]] = Field(default=None, max_length=7)
    public_attributes: Optional[Dict[str, Any]] = None
    attribute_image_map: Optional[Dict[str, Dict[str, str]]] = None
    variants: Optional[List[ProductVariantInput]] = Field(default=None, max_length=100)
    status: Optional[Literal["draft", "published", "archived"]] = None

    @field_validator("public_attributes")
    @classmethod
    def validate_public_attributes(cls, value):
        return _normalize_public_attributes(value) if value is not None else value


def _template_payload(template: GoodsTypeAttributeTemplate) -> dict:
    return {
        "id": str(template.id),
        "key": template.key,
        "label": template.label,
        "field_type": template.field_type,
        "allowed_values": template.allowed_values or [],
        "is_required": bool(template.is_required),
        "customer_visible": bool(template.customer_visible),
        "is_variant_option": bool(template.is_variant_option),
        "sort_order": template.sort_order,
    }


def _require_verified_sourcing_profile(db: Session, agent_id: UUID) -> SourcingAgent:
    profile = (
        db.query(SourcingAgent)
        .filter(
            SourcingAgent.user_id == agent_id,
            SourcingAgent.status == "verified",
            SourcingAgent.is_verified.is_(True),
        )
        .first()
    )
    if not profile:
        raise HTTPException(
            status_code=403,
            detail="A verified sourcing-agent registration is required to manage Agizisha products.",
        )
    return profile


def _validate_product_builder_data(
    db: Session,
    goods_type_id: UUID,
    public_attributes: Dict[str, Any],
    variants: List[ProductVariantInput],
) -> tuple[GoodsType, list[GoodsTypeAttributeTemplate]]:
    """Validate dynamic values against the selected product type's templates."""
    goods_type = (
        db.query(GoodsType)
        .filter(GoodsType.id == goods_type_id, GoodsType.is_active.is_(True))
        .first()
    )
    if not goods_type:
        raise HTTPException(
            status_code=422, detail="Selected Goods Type is unavailable."
        )

    templates = (
        db.query(GoodsTypeAttributeTemplate)
        .filter(
            GoodsTypeAttributeTemplate.goods_type_id == goods_type.id,
            GoodsTypeAttributeTemplate.is_active.is_(True),
        )
        .order_by(
            GoodsTypeAttributeTemplate.sort_order, GoodsTypeAttributeTemplate.created_at
        )
        .all()
    )
    by_key = {template.key: template for template in templates}
    for template in templates:
        value = _attribute_value(public_attributes.get(template.key))
        if template.is_required and (value is None or value == "" or value == []):
            raise HTTPException(
                status_code=422, detail=f"{template.label} is required."
            )
        if value is None:
            continue
        values = value if isinstance(value, list) else [value]
        allowed = {str(item) for item in (template.allowed_values or [])}
        if template.field_type in {"select", "multiselect"} and allowed:
            if any(str(item) not in allowed for item in values):
                raise HTTPException(
                    status_code=422, detail=f"Invalid {template.label} value."
                )
        if template.is_variant_option and not isinstance(value, list):
            raise HTTPException(
                status_code=422,
                detail=f"{template.label} must provide selectable options.",
            )

    variant_keys = {
        template.key for template in templates if template.is_variant_option
    }
    seen_combinations = set()
    for variant in variants:
        option_keys = set(variant.option_values)
        if option_keys != variant_keys:
            raise HTTPException(
                status_code=422,
                detail="Each variant must include every configured variant option.",
            )
        for key, selected in variant.option_values.items():
            choices = _attribute_value(public_attributes.get(key, []))
            choices = choices if isinstance(choices, list) else [choices]
            if selected not in choices:
                label = by_key.get(key).label if by_key.get(key) else key
                raise HTTPException(
                    status_code=422, detail=f"Invalid {label} variant selection."
                )
        signature = tuple(sorted(variant.option_values.items()))
        if signature in seen_combinations:
            raise HTTPException(status_code=422, detail="Duplicate product variant.")
        seen_combinations.add(signature)
    if (
        variant_keys
        and variants
        and not all(variant.stock_quantity >= 0 for variant in variants)
    ):
        raise HTTPException(status_code=422, detail="Variant stock cannot be negative.")
    return goods_type, templates


def _replace_product_variants(
    db: Session, product: SourcingProduct, variants: List[ProductVariantInput]
) -> None:
    db.query(SourcingProductVariant).filter(
        SourcingProductVariant.product_id == product.id
    ).delete(synchronize_session=False)
    for variant in variants:
        db.add(
            SourcingProductVariant(
                product_id=product.id,
                option_values=variant.option_values,
                price_per_unit=variant.price_per_unit,
                stock_quantity=variant.stock_quantity,
                is_active=variant.is_active,
            )
        )


class InstagramImportRequest(BaseModel):
    instagram_url: HttpUrl
    consent: bool = Field(..., description="Must confirm ownership")
    image_index: Optional[int] = Field(
        0, ge=0, description="Carousel image index (0-based)"
    )

    @field_validator("consent")
    @classmethod
    def validate_consent(cls, v):
        if not v:
            raise ValueError("You must confirm you own the rights to this image")
        return v

    @field_validator("instagram_url")
    @classmethod
    def validate_instagram_url(cls, v):
        url_str = str(v)
        if (
            "instagram.com/p/" not in url_str
            and "instagram.com/reel/" not in url_str
            and "instagram.com/tv/" not in url_str
        ):
            raise ValueError("Invalid Instagram URL. Must be a post, reel, or TV URL")
        return v


class BookCBMRequest(BaseModel):
    container_id: str
    cbm_amount: float = Field(..., gt=0, le=100000)
    destination_city: str = Field(..., min_length=2, max_length=120)
    destination_country: Optional[str] = Field(None, min_length=2, max_length=100)

    @field_validator("cbm_amount")
    @classmethod
    def validate_cbm(cls, v):
        if v <= 0:
            raise ValueError("CBM must be greater than 0")
        return round(v, 2)


class ShareTokenRequest(BaseModel):
    expires_days: Optional[int] = Field(30, ge=1, le=365)
    max_views: Optional[int] = Field(None, ge=1, le=1000)


class InstagramImportResponse(BaseModel):
    success: bool
    image_url: str
    public_id: str
    instagram_username: str
    message: str


# ─── Batch Management ────────────────────────────────────


@router.get("/batches")
def list_my_batches(
    status: Optional[str] = None,
    skip: int = 0,
    limit: int = 20,
    db: Session = Depends(get_db),
    agent: User = Depends(get_sourcing_agent),
):
    """List only this agent's own batches with pagination."""
    try:
        q = (
            db.query(SourcingBatch)
            .options(
                joinedload(SourcingBatch.products).joinedload(
                    SourcingProduct.goods_type
                )
            )
            .filter(SourcingBatch.agent_id == agent.id)
        )

        if status:
            if status not in ["draft", "open", "closed", "completed"]:
                raise HTTPException(status_code=400, detail="Invalid status")
            q = q.filter(SourcingBatch.status == status)

        total = q.count()
        batches = (
            q.order_by(SourcingBatch.created_at.desc()).offset(skip).limit(limit).all()
        )

        return {
            "total": total,
            "skip": skip,
            "limit": limit,
            "batches": [_batch_summary(b) for b in batches],
        }
    except Exception as e:
        logger.error(f"Error listing batches: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/batches/closed")
def get_closed_batches(
    db: Session = Depends(get_db),
    agent: User = Depends(get_sourcing_agent),
):
    """Get closed batches for container booking."""
    try:
        batches = (
            db.query(SourcingBatch)
            .filter(
                SourcingBatch.agent_id == agent.id, SourcingBatch.status == "closed"
            )
            .all()
        )

        result = []
        for batch in batches:
            try:
                # Calculate total CBM from orders
                total_cbm = (
                    db.query(func.sum(SourcingOrderItem.total_cbm))
                    .join(SourcingOrder, SourcingOrderItem.order_id == SourcingOrder.id)
                    .filter(SourcingOrder.batch_id == batch.id)
                    .scalar()
                    or 0
                )

                result.append(
                    {
                        "id": str(batch.id),
                        "title": batch.title,
                        "description": batch.description,
                        "total_cbm": float(total_cbm) if total_cbm else 0.0,
                    }
                )
            except Exception as e:
                logger.warning(f"Error calculating CBM for batch {batch.id}: {str(e)}")
                # Fallback: return batch with 0 CBM instead of failing completely
                result.append(
                    {
                        "id": str(batch.id),
                        "title": batch.title,
                        "description": batch.description,
                        "total_cbm": 0.0,
                    }
                )

        return result
    except Exception as e:
        logger.error(f"Error getting closed batches: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/batches/{batch_id}")
def get_batch_detail(
    batch_id: str,
    db: Session = Depends(get_db),
    agent: User = Depends(get_sourcing_agent),
):
    """Get detailed batch information including financials."""
    try:
        batch = _get_my_batch(db, batch_id, agent.id)

        total_revenue = (
            db.query(func.sum(SourcingOrder.total_product_amount))
            .filter(SourcingOrder.batch_id == batch.id)
            .scalar()
            or 0
        )

        commission_setting = (
            db.query(CommissionSettings)
            .order_by(CommissionSettings.effective_from.desc())
            .first()
        )
        commission_rate = (
            float(commission_setting.commission_percentage)
            if commission_setting
            else settings.DEFAULT_COMMISSION_PERCENTAGE
        )

        commission_amount = float(total_revenue) * (commission_rate / 100)
        net_earnings = float(total_revenue) - commission_amount

        return {
            "id": str(batch.id),
            "issuer": sourcing_agent_document_branding(db, agent),
            "title": batch.title,
            "description": batch.description,
            "currency": batch.currency or "TZS",
            "shipping_fee_per_cbm": float(batch.shipping_fee_per_cbm or 0),
            "shipping_method": batch.shipping_method or "PER_CBM",
            "status": batch.status,
            "created_at": batch.created_at.isoformat() if batch.created_at else None,
            "total_revenue": round(float(total_revenue), 2),
            "commission_amount": round(commission_amount, 2),
            "net_earnings": round(net_earnings, 2),
            "product_count": len(batch.products),
            "order_count": len(batch.orders),
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting batch detail: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.patch("/batches/{batch_id}")
def update_batch(
    batch_id: str,
    body: BatchUpdate,
    db: Session = Depends(get_db),
    agent: User = Depends(get_sourcing_agent),
):
    """Update editable batch fields (title/description)."""
    try:
        batch = _get_my_batch(db, batch_id, agent.id)

        if batch.status == "completed":
            raise HTTPException(
                status_code=400,
                detail="Completed batches cannot be edited",
            )

        has_updates = False
        if body.title is not None and body.title != batch.title:
            batch.title = body.title
            has_updates = True

        if body.description is not None:
            normalized_description = body.description.strip() or None
            if normalized_description != batch.description:
                batch.description = normalized_description
                has_updates = True

        if not has_updates:
            return {"message": "No changes detected", "batch": _batch_summary(batch)}

        log_action(
            db=db,
            action="batch_updated",
            user_id=agent.id,
            entity_type="batch",
            entity_id=batch.id,
            metadata={
                "title": batch.title,
                "description": batch.description,
            },
        )

        db.commit()
        db.refresh(batch)
        return {"message": "Batch updated successfully", "batch": _batch_summary(batch)}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating batch: {str(e)}")
        db.rollback()
        raise HTTPException(status_code=500, detail="Failed to update batch")


@router.get("/batches/{batch_id}/orders")
def list_batch_orders(
    batch_id: str,
    skip: int = 0,
    limit: int = 20,
    db: Session = Depends(get_db),
    agent: User = Depends(get_sourcing_agent),
):
    """List orders for a specific batch with pagination."""
    try:
        batch = _get_my_batch(db, batch_id, agent.id)

        total = (
            db.query(SourcingOrder).filter(SourcingOrder.batch_id == batch.id).count()
        )
        orders = (
            db.query(SourcingOrder)
            .options(
                joinedload(SourcingOrder.customer),
                joinedload(SourcingOrder.guest),
                joinedload(SourcingOrder.items).joinedload(SourcingOrderItem.product),
            )
            .filter(SourcingOrder.batch_id == batch.id)
            .order_by(SourcingOrder.created_at.desc())
            .offset(skip)
            .limit(limit)
            .all()
        )

        return {
            "total": total,
            "skip": skip,
            "limit": limit,
            "orders": [
                {
                    "id": str(o.id),
                    "order_reference": build_display_reference(
                        "sourcing_order", o.id, o.created_at
                    ),
                    "customer_id": str(o.customer_id) if o.customer_id else None,
                    "guest_id": str(o.guest_id) if o.guest_id else None,
                    "customer_name": _resolve_order_customer_name(o),
                    "customer_phone": (
                        o.customer.phone_number
                        if o.customer and o.customer.phone_number
                        else (
                            o.guest.phone_number
                            if o.guest and o.guest.phone_number
                            else None
                        )
                    ),
                    "submitted_by": o.submitted_by,
                    "total_product_amount": round(
                        float(o.total_product_amount or 0), 2
                    ),
                    "currency": o.currency or batch.currency or "TZS",
                    "status": o.delivery_status,
                    "payment_status": o.payment_status,
                    "created_at": o.created_at.isoformat() if o.created_at else None,
                    "items": [
                        {
                            "id": str(item.id),
                            "product_id": str(item.product_id),
                            "product_name": (
                                item.product.name
                                if item.product and item.product.name
                                else "Unnamed product"
                            ),
                            "quantity": int(item.quantity or 0),
                            "unit_price": round(float(item.unit_price or 0), 2),
                            "total_price": round(float(item.total_price or 0), 2),
                            "total_cbm": round(float(item.total_cbm or 0), 4),
                            "currency": item.currency or o.currency or batch.currency,
                        }
                        for item in o.items
                    ],
                }
                for o in orders
            ],
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error listing orders: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/batches")
def create_batch(
    body: BatchCreate,
    db: Session = Depends(get_db),
    agent: User = Depends(get_sourcing_agent),
):
    """Create a new sourcing batch. Products define their own goods types."""
    try:
        batch = SourcingBatch(
            agent_id=agent.id,
            title=body.title.strip(),
            description=body.description.strip() if body.description else None,
            currency=body.currency,
            shipping_method=body.shipping_method,
            shipping_fee_per_cbm=body.shipping_fee_per_cbm,
            status="draft",
        )
        db.add(batch)
        db.flush()

        # Log creation
        log_action(
            db=db,
            action="batch_created",
            user_id=agent.id,
            entity_type="batch",
            entity_id=batch.id,
            metadata={"title": batch.title},
        )

        db.commit()
        db.refresh(batch)

        return {
            "id": str(batch.id),
            "title": batch.title,
            "currency": batch.currency or "TZS",
            "shipping_fee_per_cbm": float(batch.shipping_fee_per_cbm or 0),
            "shipping_method": batch.shipping_method or "PER_CBM",
            "status": batch.status,
            "warnings": [],
            "message": "Batch created successfully",
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating batch: {str(e)}")
        db.rollback()
        raise HTTPException(status_code=500, detail="Failed to create batch")


# ─── Products & Image Handling ───────────────────────────


@router.post(
    "/batches/{batch_id}/products/import-instagram",
    response_model=InstagramImportResponse,
)
async def import_instagram_image(
    batch_id: str,
    request: InstagramImportRequest,
    db: Session = Depends(get_db),
    agent: User = Depends(get_sourcing_agent),
):
    """
    Import image from user's own Instagram post
    Requires explicit consent confirmation
    """
    try:
        # Verify batch ownership
        batch = _get_my_batch(db, batch_id, agent.id)

        if batch.status == "closed":
            raise HTTPException(
                status_code=400, detail="Cannot add images to a closed batch"
            )

        # Process Instagram image
        result = await instagram_service.download_and_upload_image(
            str(request.instagram_url), str(agent.id), request.image_index or 0
        )

        # Log the action
        log_action(
            db=db,
            action="instagram_image_imported",
            user_id=agent.id,
            entity_type="batch",
            entity_id=batch.id,
            metadata={
                "instagram_url": str(request.instagram_url),
                "instagram_username": result["instagram_username"],
                "cloudinary_public_id": result["public_id"],
            },
        )

        db.commit()

        return InstagramImportResponse(
            success=True,
            image_url=build_optimized_cloudinary_image_url(result["image_url"]),
            public_id=result["public_id"],
            instagram_username=result["instagram_username"],
            message="Image successfully imported from Instagram",
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Instagram import error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to import image: {str(e)}")


@router.post("/batches/{batch_id}/products/upload")
async def upload_product_image(
    batch_id: str,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    agent: User = Depends(get_sourcing_agent),
):
    """
    Upload product image directly (alternative to Instagram import)
    """
    try:
        # Verify batch ownership
        batch = _get_my_batch(db, batch_id, agent.id)

        if batch.status == "closed":
            raise HTTPException(
                status_code=400, detail="Cannot upload images to a closed batch"
            )

        # Validate file type
        if file.content_type not in settings.ALLOWED_IMAGE_TYPES:
            raise HTTPException(
                status_code=400,
                detail=f"File type not allowed. Allowed: {settings.ALLOWED_IMAGE_TYPES}",
            )

        # Check file size (convert MB to bytes)
        max_size = settings.MAX_IMAGE_SIZE_MB * 1024 * 1024
        file.file.seek(0, 2)  # Seek to end
        file_size = file.file.tell()
        file.file.seek(0)  # Reset position

        if file_size > max_size:
            raise HTTPException(
                status_code=400,
                detail=f"File too large. Max size: {settings.MAX_IMAGE_SIZE_MB}MB",
            )

        content = await file.read()
        _, file_extension = validated_image_format(content, file.content_type)

        # Save temporarily
        with tempfile.NamedTemporaryFile(
            delete=False, suffix=f".{file_extension}"
        ) as tmp:
            tmp.write(content)
            tmp_path = tmp.name

        try:
            # Upload to Cloudinary
            result = upload_to_cloudinary(tmp_path, str(agent.id), "direct_upload")

            return {
                "success": True,
                "image_url": build_optimized_cloudinary_image_url(result["secure_url"]),
                "public_id": result["public_id"],
                "message": "Image uploaded successfully",
            }
        finally:
            # Clean up temp file
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"File upload error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to upload image: {str(e)}")


@router.post("/batches/{batch_id}/products")
def add_product(
    batch_id: str,
    body: ProductCreate,
    db: Session = Depends(get_db),
    agent: User = Depends(get_sourcing_agent),
):
    """Add a product to a batch with pre-uploaded image URL"""
    try:
        batch = _get_my_batch(db, batch_id, agent.id)
        _require_verified_sourcing_profile(db, agent.id)

        if batch.status == "closed":
            raise HTTPException(
                status_code=400, detail="Cannot add products to a closed batch"
            )

        if batch.shipping_method == "PER_CBM" and (
            body.cbm_per_unit is None or body.cbm_per_unit <= 0
        ):
            raise HTTPException(
                status_code=400,
                detail="CBM per unit is required for per-CBM shipping batches",
            )

        _validate_product_builder_data(
            db, body.goods_type_id, body.public_attributes, body.variants
        )
        try:
            attribute_image_map = _normalize_attribute_image_map(
                body.attribute_image_map,
                body.public_attributes,
                body.image_url,
                body.additional_image_urls,
            )
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
        product = SourcingProduct(
            batch_id=batch.id,
            goods_type_id=body.goods_type_id,
            name=body.name.strip(),
            description=body.description.strip() if body.description else None,
            cbm_per_unit=(
                0 if batch.shipping_method == "FREE_SHIPPING" else body.cbm_per_unit
            ),
            price_per_unit=body.price_per_unit,
            minimum_order_quantity=body.minimum_order_quantity,
            image_url=body.image_url,
            additional_image_urls=body.additional_image_urls,
            public_attributes=body.public_attributes,
            attribute_image_map=attribute_image_map,
            status=body.status,
            published_at=datetime.utcnow() if body.status == "published" else None,
        )
        db.add(product)
        db.flush()
        _replace_product_variants(db, product, body.variants)

        log_action(
            db=db,
            action="product_added",
            user_id=agent.id,
            entity_type="product",
            entity_id=product.id,
            metadata={"batch_id": batch_id, "product_name": body.name},
        )

        db.commit()
        db.refresh(product)

        return {
            "id": str(product.id),
            "name": product.name,
            "price_per_unit": float(product.price_per_unit),
            "cbm_per_unit": float(product.cbm_per_unit or 0),
            "minimum_order_quantity": product.minimum_order_quantity,
            "goods_type_id": str(product.goods_type_id),
            "status": product.status,
            "image_url": build_optimized_cloudinary_image_url(product.image_url),
            "additional_image_urls": [
                build_optimized_cloudinary_image_url(url)
                for url in (product.additional_image_urls or [])
            ],
            "public_attributes": product.public_attributes or {},
            "attribute_image_map": _serialized_attribute_image_map(product),
            "variants": [
                {
                    "id": str(variant.id),
                    "option_values": variant.option_values or {},
                    "price_per_unit": float(variant.price_per_unit),
                    "stock_quantity": variant.stock_quantity,
                    "is_active": variant.is_active,
                }
                for variant in product.variants
            ],
            "message": "Product added successfully",
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error adding product: {str(e)}")
        db.rollback()
        raise HTTPException(status_code=500, detail="Failed to add product")


@router.get("/batches/{batch_id}/products")
def list_products(
    batch_id: str,
    db: Session = Depends(get_db),
    agent: User = Depends(get_sourcing_agent),
):
    """List all products in a batch"""
    try:
        batch = _get_my_batch(db, batch_id, agent.id)

        products = (
            db.query(SourcingProduct)
            .options(
                joinedload(SourcingProduct.variants),
                joinedload(SourcingProduct.goods_type),
            )
            .filter(SourcingProduct.batch_id == batch.id)
            .order_by(SourcingProduct.created_at.desc())
            .all()
        )
        return [
            {
                "id": str(p.id),
                "name": p.name,
                "description": p.description,
                "cbm_per_unit": float(p.cbm_per_unit),
                "price_per_unit": float(p.price_per_unit),
                "minimum_order_quantity": p.minimum_order_quantity,
                "goods_type_id": str(p.goods_type_id) if p.goods_type_id else None,
                "goods_type_name": p.goods_type.name if p.goods_type else None,
                "status": p.status,
                "image_url": build_optimized_cloudinary_image_url(p.image_url),
                "additional_image_urls": [
                    build_optimized_cloudinary_image_url(url)
                    for url in (p.additional_image_urls or [])
                ],
                "public_attributes": p.public_attributes or {},
                "attribute_image_map": _serialized_attribute_image_map(p),
                "variants": [
                    {
                        "id": str(variant.id),
                        "option_values": variant.option_values or {},
                        "price_per_unit": float(variant.price_per_unit),
                        "stock_quantity": variant.stock_quantity,
                        "is_active": variant.is_active,
                    }
                    for variant in p.variants
                ],
                "created_at": p.created_at.isoformat() if p.created_at else None,
            }
            for p in products
        ]
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error listing products: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/goods/types/{goods_type_id}/attribute-templates")
def list_goods_type_attribute_templates(
    goods_type_id: UUID,
    db: Session = Depends(get_db),
    agent: User = Depends(get_sourcing_agent),
):
    """Expose admin-configured dynamic fields to the reusable agent builder."""
    templates = (
        db.query(GoodsTypeAttributeTemplate)
        .filter(
            GoodsTypeAttributeTemplate.goods_type_id == goods_type_id,
            GoodsTypeAttributeTemplate.is_active.is_(True),
        )
        .order_by(
            GoodsTypeAttributeTemplate.sort_order, GoodsTypeAttributeTemplate.created_at
        )
        .all()
    )
    return {"templates": [_template_payload(template) for template in templates]}


@router.patch("/batches/{batch_id}/products/{product_id}")
def update_product(
    batch_id: str,
    product_id: UUID,
    body: ProductUpdate,
    db: Session = Depends(get_db),
    agent: User = Depends(get_sourcing_agent),
):
    """Update only an owned product; variant replacement is guarded by requests."""
    batch = _get_my_batch(db, batch_id, agent.id)
    _require_verified_sourcing_profile(db, agent.id)
    product = (
        db.query(SourcingProduct)
        .options(joinedload(SourcingProduct.agizisha_orders))
        .filter(SourcingProduct.id == product_id, SourcingProduct.batch_id == batch.id)
        .first()
    )
    if not product:
        raise HTTPException(status_code=404, detail="Product not found in this batch")

    updates = body.model_dump(exclude_unset=True)
    if "public_attributes" in updates or "variants" in updates:
        attributes = updates.get("public_attributes", product.public_attributes or {})
        variants = updates.get("variants")
        if variants is None:
            variants = [
                ProductVariantInput(
                    option_values=item.option_values or {},
                    price_per_unit=float(item.price_per_unit),
                    stock_quantity=item.stock_quantity,
                    is_active=item.is_active,
                )
                for item in product.variants
            ]
        _validate_product_builder_data(db, product.goods_type_id, attributes, variants)
        if "variants" in updates and product.agizisha_orders:
            raise HTTPException(
                status_code=400,
                detail="Variants with customer requests cannot be replaced.",
            )
        product.public_attributes = attributes
        if "variants" in updates:
            _replace_product_variants(db, product, variants)

    next_attributes = updates.get("public_attributes", product.public_attributes or {})
    next_image_url = updates.get("image_url", product.image_url)
    next_additional_images = updates.get(
        "additional_image_urls", product.additional_image_urls or []
    )
    try:
        product.attribute_image_map = _normalize_attribute_image_map(
            updates.get("attribute_image_map", product.attribute_image_map or {}),
            next_attributes,
            next_image_url,
            next_additional_images,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    if updates.get("status") == "published":
        # The public Agizisha query separately requires an open batch. Keep
        # visibility independent from saving the product into a draft batch.
        product.published_at = product.published_at or datetime.utcnow()
    for field in (
        "name",
        "description",
        "cbm_per_unit",
        "price_per_unit",
        "minimum_order_quantity",
        "image_url",
        "additional_image_urls",
        "status",
    ):
        if field in updates:
            setattr(product, field, updates[field])
    db.commit()
    db.refresh(product)
    return {
        "id": str(product.id),
        "status": product.status,
        "message": "Product updated successfully",
    }


@router.delete("/batches/{batch_id}/products/{product_id}")
def delete_product(
    batch_id: str,
    product_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_sourcing_agent),
):
    """Delete an un-ordered product from a batch owned by the agent or a super admin."""
    try:
        batch = _get_manageable_batch(db, batch_id, current_user)
        if batch.status == "completed":
            raise HTTPException(
                status_code=400, detail="Completed batches cannot be changed"
            )

        product = (
            db.query(SourcingProduct)
            .filter(
                SourcingProduct.id == product_id,
                SourcingProduct.batch_id == batch.id,
            )
            .first()
        )
        if not product:
            raise HTTPException(
                status_code=404, detail="Product not found in this batch"
            )

        if (
            db.query(SourcingOrderItem)
            .filter(SourcingOrderItem.product_id == product.id)
            .first()
        ):
            raise HTTPException(
                status_code=400,
                detail="This product has customer order records and cannot be deleted",
            )

        product_name = product.name
        db.delete(product)
        log_action(
            db=db,
            action="product_deleted",
            user_id=current_user.id,
            entity_type="product",
            entity_id=product.id,
            metadata={"batch_id": str(batch.id), "product_name": product_name},
        )
        db.commit()
        return {"message": "Product deleted successfully"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting product: {str(e)}")
        db.rollback()
        raise HTTPException(status_code=500, detail="Failed to delete product")


@router.delete("/batches/{batch_id}")
def delete_batch(
    batch_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_sourcing_agent),
):
    """Delete a batch only when it has no customer-submitted orders."""
    try:
        batch = _get_manageable_batch(db, batch_id, current_user)
        if batch.status == "completed":
            raise HTTPException(
                status_code=400, detail="Completed batches cannot be deleted"
            )

        order_count = (
            db.query(SourcingOrder).filter(SourcingOrder.batch_id == batch.id).count()
        )
        if order_count:
            raise HTTPException(
                status_code=400,
                detail="This batch has customer orders and cannot be deleted",
            )

        batch_title = batch.title
        log_action(
            db=db,
            action="batch_deleted",
            user_id=current_user.id,
            entity_type="batch",
            entity_id=batch.id,
            metadata={"title": batch_title},
        )
        db.delete(batch)
        db.commit()
        return {"message": "Batch deleted successfully"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting batch: {str(e)}")
        db.rollback()
        raise HTTPException(status_code=500, detail="Failed to delete batch")


# ─── Share Tokens (for guests) ───────────────────────────


@router.post("/batches/{batch_id}/share")
def generate_share_token(
    batch_id: str,
    body: ShareTokenRequest,
    db: Session = Depends(get_db),
    agent: User = Depends(get_sourcing_agent),
):
    """Generate a secure share link for guests to view batch and place orders."""
    try:
        batch = _get_my_batch(db, batch_id, agent.id)

        token_val = secrets.token_urlsafe(32)
        expires_at = None
        if body.expires_days:
            expires_at = datetime.utcnow() + timedelta(days=body.expires_days)

        share_token = BatchShareToken(
            batch_id=batch.id,
            token=token_val,
            expires_at=expires_at,
            max_views=body.max_views,
        )
        db.add(share_token)

        log_action(
            db=db,
            action="share_token_generated",
            user_id=agent.id,
            entity_type="batch",
            entity_id=batch.id,
            metadata={"expires_days": body.expires_days},
        )

        db.commit()

        share_path = f"/shared/{token_val}"
        share_full_url = build_shared_batch_link(token_val)

        return {
            "share_token": token_val,
            "share_path": share_path,
            "share_url": share_full_url,
            "expires_at": expires_at.isoformat() if expires_at else None,
            "message": "Share link generated successfully",
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error generating share token: {str(e)}")
        db.rollback()
        raise HTTPException(status_code=500, detail="Failed to generate share link")


# ─── Container SeaBooking ───────────────────────────────


@router.get("/containers/available")
def browse_available_containers(
    db: Session = Depends(get_db),
    agent: User = Depends(get_sourcing_agent),
):
    """Browse available operator containers with comparison info."""
    try:
        containers = (
            db.query(Container)
            .filter(Container.status.in_(["open", "nearly_full"]))
            .all()
        )
        containers = [
            container
            for container in containers
            if company_service_is_bookable(
                db,
                operator_id=container.admin_id,
                service_type="shared_container",
            )
        ]
        booked_cbm_map = _get_booked_cbm_map(
            db, [str(container.id) for container in containers]
        )

        return [
            {
                "id": str(c.id),
                "container_size": c.container_size,
                "available_cbm": max(
                    float(c.max_cbm or 0)
                    - booked_cbm_map.get(str(c.id), float(c.booked_cbm or 0)),
                    0,
                ),
                "fill_percentage": round(
                    (
                        (
                            (
                                booked_cbm_map.get(str(c.id), float(c.booked_cbm or 0))
                                / float(c.max_cbm)
                            )
                            * 100
                        )
                        if c.max_cbm and float(c.max_cbm) > 0
                        else 0
                    ),
                    2,
                ),
                "price_per_cbm": float(c.price_per_cbm),
                "currency": c.currency or "TZS",
                "status": c.status,
                "operator": (
                    c.admin.name if c.admin and c.admin.name else "Cargo Company"
                ),
                "operator_name": (
                    c.admin.name if c.admin and c.admin.name else "Cargo Company"
                ),
                "route": (
                    f"{c.route.origin} → {c.route.destination}"
                    if c.route
                    else "Route not assigned"
                ),
                "destination_country": (
                    c.destination_warehouse.country
                    if c.destination_warehouse and c.destination_warehouse.country
                    else None
                ),
            }
            for c in containers
        ]
    except Exception as e:
        logger.error(f"Error listing containers: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/containers")
def browse_containers(
    db: Session = Depends(get_db),
    agent: User = Depends(get_sourcing_agent),
):
    """Browse available containers with operator info."""
    try:
        containers = (
            db.query(Container)
            .filter(Container.status.in_(["open", "nearly_full"]))
            .all()
        )
        containers = [
            container
            for container in containers
            if company_service_is_bookable(
                db,
                operator_id=container.admin_id,
                service_type="shared_container",
            )
        ]
        booked_cbm_map = _get_booked_cbm_map(
            db, [str(container.id) for container in containers]
        )

        return [
            {
                "id": str(c.id),
                "container_size": c.container_size,
                "available_cbm": max(
                    float(c.max_cbm or 0)
                    - booked_cbm_map.get(str(c.id), float(c.booked_cbm or 0)),
                    0,
                ),
                "fill_percentage": round(
                    (
                        (
                            (
                                booked_cbm_map.get(str(c.id), float(c.booked_cbm or 0))
                                / float(c.max_cbm)
                            )
                            * 100
                        )
                        if c.max_cbm and float(c.max_cbm) > 0
                        else 0
                    ),
                    2,
                ),
                "price_per_cbm": float(c.price_per_cbm),
                "currency": c.currency or "TZS",
                "status": c.status,
                "operator": (
                    c.admin.name if c.admin and c.admin.name else "Cargo Company"
                ),
                "operator_name": (
                    c.admin.name if c.admin and c.admin.name else "Cargo Company"
                ),
                "route": (
                    f"{c.route.origin} → {c.route.destination}"
                    if c.route
                    else "Route not assigned"
                ),
                "destination_country": (
                    c.destination_warehouse.country
                    if c.destination_warehouse and c.destination_warehouse.country
                    else None
                ),
            }
            for c in containers
        ]
    except Exception as e:
        logger.error(f"Error browsing containers: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/sea-bookings")
def get_agent_sea_bookings(
    db: Session = Depends(get_db),
    agent: User = Depends(get_sourcing_agent),
):
    """Get every sea_booking owned by the agent with its booked currency."""
    try:
        sea_bookings = (
            db.query(SeaBooking)
            .filter(SeaBooking.user_id == agent.id)
            .order_by(SeaBooking.created_at.desc())
            .all()
        )

        result = []
        for r in sea_bookings:
            c = r.container
            result.append(
                {
                    "id": str(r.id),
                    "booking_reference": f"BK-{str(r.id)[:8]}",
                    "container_id": str(r.container_id),
                    "batch_id": str(r.source_id) if r.source_id else None,
                    "source_type": r.source_type,
                    "cbm_booked": float(r.cbm_booked),
                    "logistics_charge": float(r.logistics_charge),
                    # A sea_booking retains the currency in effect when it was booked;
                    # never let a later container currency change relabel its amount.
                    "currency": r.currency or (c.currency if c else None) or "TZS",
                    "payment_status": r.payment_status,
                    "goods_status": r.goods_status,
                    "created_at": r.created_at.isoformat() if r.created_at else None,
                    "container": (
                        {
                            "operator": c.admin.name if c and c.admin else "Unknown",
                            "route": (
                                f"{c.route.origin} → {c.route.destination}"
                                if c and c.route
                                else "Unknown"
                            ),
                            "status": c.status if c else "unknown",
                            "currency": c.currency or "TZS",
                            "departure_date": (
                                c.departure_date.isoformat()
                                if c and c.departure_date
                                else None
                            ),
                            "estimated_arrival_date": (
                                c.estimated_arrival_date.isoformat()
                                if c and c.estimated_arrival_date
                                else None
                            ),
                            "arrival_date": (
                                c.arrival_date.isoformat()
                                if c and c.arrival_date
                                else None
                            ),
                        }
                        if c
                        else None
                    ),
                }
            )

        return result
    except Exception as e:
        logger.error(f"Error getting agent packing lists: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to get packing lists")


@router.post(
    "/batches/{batch_id}/generate-packing-list",
    response_model=GeneratePackingListResponse,
)
def generate_packing_list_from_closed_batch(
    batch_id: str,
    db: Session = Depends(get_db),
    agent: User = Depends(get_sourcing_agent),
):
    """
    Generate a complete packing list from all orders in a closed batch.
    Creates both database records and downloadable documents (Excel/PDF).

    Args:
        batch_id: ID of the closed sourcing batch

    Returns:
        Dictionary containing packing list details and document URLs
    """
    try:
        # Verify the batch belongs to this agent and is closed
        batch = _get_my_batch(db, batch_id, agent.id)
        if batch.status != "closed":
            raise HTTPException(
                status_code=400, detail="Batch must be closed to generate packing list"
            )

        # Generate packing list from closed batch
        result = PackingListService.generate_packing_list_from_closed_batch(
            db=db, batch_id=batch_id, agent_id=str(agent.id)
        )

        return result

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error generating packing list from batch {batch_id}: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to generate packing list")


@router.get("/container-receipts")
def get_receipts(
    db: Session = Depends(get_db),
    agent: User = Depends(get_sourcing_agent),
):
    """Get all receipts for this agent."""
    try:
        from app.models.container import ContainerReceipt

        receipts = (
            db.query(ContainerReceipt)
            .filter(ContainerReceipt.agent_id == agent.id)
            .all()
        )

        return [
            {
                "id": str(receipt.id),
                "container_id": str(receipt.container_id),
                "date": receipt.date,
                "amount": receipt.amount,
                "currency": receipt.currency,
                "status": receipt.status,
                "payment_date": receipt.payment_date,
                "payment_reference": receipt.payment_reference,
                "payment_method": receipt.payment_method,
                "payment_status": receipt.payment_status,
                "notes": receipt.notes,
            }
            for receipt in receipts
        ]
    except Exception as e:
        logger.error(f"Error getting receipts: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/routes")
def get_routes(
    db: Session = Depends(get_db),
    agent: User = Depends(get_sourcing_agent),
):
    """Get all active routes."""
    try:
        from app.models.container import Route

        routes = db.query(Route).filter(Route.is_active).all()

        return [
            {
                "id": str(route.id),
                "name": f"{route.origin} → {route.destination}",
            }
            for route in routes
        ]
    except Exception as e:
        logger.error(f"Error getting routes: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/batches/{batch_id}/book-cbm")
def book_cbm_for_batch(
    batch_id: str,
    body: BookCBMRequest,
    db: Session = Depends(get_db),
    agent: User = Depends(get_sourcing_agent),
):
    """Book CBM in a chosen container for this batch. Calculates logistics charge."""
    try:
        batch = _get_my_batch(db, batch_id, agent.id)

        if batch.status != "closed":
            raise HTTPException(
                status_code=400, detail="Batch must be closed before booking CBM"
            )

        container = (
            db.query(Container)
            .filter(
                Container.id == body.container_id,
                Container.status.in_(["open", "nearly_full"]),
            )
            .with_for_update()
            .first()
        )

        if not container:
            raise HTTPException(status_code=404, detail="Container not available")
        require_company_service_bookable(
            db,
            operator_id=container.admin_id,
            service_type="shared_container",
        )

        current_booked_cbm = (
            db.query(func.coalesce(func.sum(SeaBooking.cbm_booked), 0))
            .filter(SeaBooking.container_id == container.id)
            .scalar()
            or 0
        )
        current_booked_cbm = float(current_booked_cbm)
        current_available_cbm = max(float(container.max_cbm) - current_booked_cbm, 0)

        if current_available_cbm < body.cbm_amount:
            raise HTTPException(
                status_code=400,
                detail=f"Insufficient space. Available: {current_available_cbm:.2f} CBM",
            )

        logistics_charge = float(container.price_per_cbm) * body.cbm_amount
        sea_booking_currency = (container.currency or "TZS").upper()

        sea_booking = SeaBooking(
            container_id=container.id,
            user_id=agent.id,
            source_type="batch",
            source_id=batch.id,
            cbm_booked=body.cbm_amount,
            logistics_charge=logistics_charge,
            currency=sea_booking_currency,
            payment_status="pending",
            goods_status="ready",
        )
        if not container.origin_warehouse or not is_china_warehouse(
            container.origin_warehouse
        ):
            raise HTTPException(
                status_code=409,
                detail="The selected sea service has no ready China forwarding warehouse.",
            )
        address = ensure_customer_china_address(
            db,
            customer=agent,
            warehouse=container.origin_warehouse,
            cargo_mode="sea",
            destination_country=(
                container.destination_warehouse.country
                if container.destination_warehouse
                and container.destination_warehouse.country
                else body.destination_country or "Destination country"
            ),
            destination_city=body.destination_city,
        )
        sea_booking.customer_china_address_id = address.id
        db.add(sea_booking)
        db.flush()

        # SeaBooking cargo metadata is derived from the products in this batch.
        product_goods_type_ids = [
            goods_type_id
            for (goods_type_id,) in (
                db.query(SourcingProduct.goods_type_id)
                .filter(
                    SourcingProduct.batch_id == batch.id,
                    SourcingProduct.goods_type_id.isnot(None),
                )
                .distinct()
                .all()
            )
        ]
        for goods_type_id in product_goods_type_ids:
            db.add(
                SeaBookingGoods(
                    sea_booking_id=sea_booking.id,
                    goods_type_id=goods_type_id,
                )
            )

        # Update container fill and status
        container.booked_cbm = current_booked_cbm + body.cbm_amount
        fill_pct = float(container.booked_cbm) / float(container.max_cbm) * 100
        if float(container.booked_cbm) >= float(container.max_cbm):
            container.status = "full"
        elif fill_pct >= 80:
            container.status = "nearly_full"

        shipment_order = ensure_shipment_order_for_sea_booking(db, sea_booking)

        TrackingService.create_tracking_event(
            db=db,
            entity_type="sea_booking",
            entity_id=str(sea_booking.id),
            event_type="sea_booking_created",
            description=(
                f"Batch-linked CBM sea booking created for {body.cbm_amount} CBM "
                f"from batch {batch_id}"
            ),
            triggered_by=str(agent.id),
            extra_data={
                "container_id": str(container.id),
                "cbm_booked": float(sea_booking.cbm_booked),
                "logistics_charge": float(sea_booking.logistics_charge),
                "currency": sea_booking.currency,
                "source_type": "batch",
                "batch_id": str(batch.id),
                "payment_status": sea_booking.payment_status,
            },
        )

        log_action(
            db=db,
            action="cbm_booked",
            user_id=agent.id,
            entity_type="sea_booking",
            entity_id=sea_booking.id,
            metadata={
                "batch_id": batch_id,
                "container_id": body.container_id,
                "cbm_amount": body.cbm_amount,
            },
        )

        notify_container_booking_created(db, container, sea_booking, agent)

        db.commit()
        db.refresh(sea_booking)

        return {
            "sea_booking_id": str(sea_booking.id),
            "container_id": str(container.id),
            "cbm_booked": body.cbm_amount,
            "logistics_charge": round(logistics_charge, 2),
            "currency": sea_booking.currency,
            "tracking_number": shipment_order.tracking_number,
            "payment_status": "pending",
            "message": "CBM booked successfully",
            "china_address": copy_ready_address(address),
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error booking CBM: {str(e)}")
        db.rollback()
        raise HTTPException(status_code=500, detail="Failed to book CBM")


@router.get("/batches/{batch_id}/financials")
def get_batch_financials(
    batch_id: str,
    db: Session = Depends(get_db),
    agent: User = Depends(get_sourcing_agent),
):
    """Get financial details for a batch."""
    try:
        batch = _get_my_batch(db, batch_id, agent.id)
        total_cbm_booked = (
            db.query(func.coalesce(func.sum(SourcingOrderItem.total_cbm), 0))
            .join(SourcingOrder, SourcingOrderItem.order_id == SourcingOrder.id)
            .filter(SourcingOrder.batch_id == batch.id)
            .scalar()
        )
        total_product_value = (
            db.query(func.coalesce(func.sum(SourcingOrder.total_product_amount), 0))
            .filter(SourcingOrder.batch_id == batch.id)
            .scalar()
        )
        safe_total_cbm = float(total_cbm_booked or 0)
        safe_product_value = float(total_product_value or 0)
        safe_shipping_fee_per_cbm = (
            float(batch.shipping_fee_per_cbm or 0)
            if batch.shipping_method == "PER_CBM"
            else 0.0
        )
        total_logistics_charge = safe_total_cbm * safe_shipping_fee_per_cbm

        return {
            "total_cbm_booked": safe_total_cbm,
            "total_logistics_charge": round(total_logistics_charge, 2),
            "total_product_value": round(safe_product_value, 2),
            "total_value": round(safe_product_value + total_logistics_charge, 2),
            "currency": batch.currency or "TZS",
            "shipping_method": batch.shipping_method or "PER_CBM",
        }
    except Exception as e:
        logger.error(f"Error getting batch financials for {batch_id}: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")


# ─── PACKING LIST ENDPOINTS ─────────────────────────────────────────────────────


@router.post("/batches/{batch_id}/packing-lists", response_model=PackingListResponse)
def create_packing_list(
    batch_id: str,
    packing_list_data: PackingListCreate,
    db: Session = Depends(get_db),
    agent: User = Depends(get_sourcing_agent),
):
    """Create a new packing list for a batch."""
    try:
        packing_list = PackingListService.create_packing_list(
            db=db,
            batch_id=batch_id,
            agent_id=str(agent.id),
            name=packing_list_data.name,
            description=packing_list_data.description,
        )
        batch = _get_my_batch(db, batch_id, agent.id)
        TrackingService.create_tracking_event(
            db=db,
            entity_type="batch",
            entity_id=str(batch.id),
            event_type="packing_list_created",
            description=f"Packing list submitted: {packing_list.name}",
            triggered_by=str(agent.id),
            extra_data={
                "batch_title": batch.title,
                "packing_list_id": str(packing_list.id),
                "packing_list_name": packing_list.name,
                "logistics_stage": "packed_verified",
            },
        )
        db.commit()
        db.refresh(packing_list)
        return packing_list
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Error creating packing list for batch {batch_id}: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to create packing list")


@router.get(
    "/batches/{batch_id}/packing-lists", response_model=List[PackingListSummaryResponse]
)
def get_batch_packing_lists(
    batch_id: str,
    db: Session = Depends(get_db),
    agent: User = Depends(get_sourcing_agent),
):
    """Get all packing lists for a batch."""
    try:
        # Verify batch belongs to agent
        _get_my_batch(db, batch_id, agent.id)

        packing_lists = PackingListService.get_packing_lists_by_batch(db, batch_id)

        # Add item count to each packing list
        result = []
        for pl in packing_lists:
            result.append(
                {
                    "id": pl.id,
                    "name": pl.name,
                    "batch_id": pl.batch_id,
                    "created_at": pl.created_at,
                    "item_count": len(pl.items),
                    "qr_code_url": pl.qr_code_url,
                }
            )

        return result
    except Exception as e:
        logger.error(f"Error getting packing lists for batch {batch_id}: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to get packing lists")


@router.get("/packing-lists/{packing_list_id}", response_model=PackingListResponse)
def get_packing_list(
    packing_list_id: str,
    db: Session = Depends(get_db),
    agent: User = Depends(get_sourcing_agent),
):
    """Get a specific packing list with all items."""
    try:
        packing_list = PackingListService.get_packing_list_by_id(db, packing_list_id)

        if not packing_list:
            raise HTTPException(status_code=404, detail="Packing list not found")

        # Verify packing list belongs to agent's batch
        _get_my_batch(db, str(packing_list.batch_id), agent.id)

        return _build_packing_list_payload(db, packing_list)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting packing list {packing_list_id}: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to get packing list")


@router.get("/packing-lists/{packing_list_id}/export/pdf")
def export_packing_list_pdf(
    packing_list_id: str,
    db: Session = Depends(get_db),
    agent: User = Depends(get_sourcing_agent),
):
    try:
        packing_list = PackingListService.get_packing_list_by_id(db, packing_list_id)
        if not packing_list:
            raise HTTPException(status_code=404, detail="Packing list not found")
        _get_my_batch(db, str(packing_list.batch_id), agent.id)

        content, filename, media_type = _export_packing_list_document(
            db, packing_list, "pdf"
        )
        return StreamingResponse(
            BytesIO(content),
            media_type=media_type,
            headers={"Content-Disposition": f'attachment; filename="{filename}"'},
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error exporting packing list PDF {packing_list_id}: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to export packing list PDF")


@router.get("/packing-lists/{packing_list_id}/export/excel")
def export_packing_list_excel(
    packing_list_id: str,
    db: Session = Depends(get_db),
    agent: User = Depends(get_sourcing_agent),
):
    try:
        packing_list = PackingListService.get_packing_list_by_id(db, packing_list_id)
        if not packing_list:
            raise HTTPException(status_code=404, detail="Packing list not found")
        _get_my_batch(db, str(packing_list.batch_id), agent.id)

        content, filename, media_type = _export_packing_list_document(
            db, packing_list, "excel"
        )
        return StreamingResponse(
            BytesIO(content),
            media_type=media_type,
            headers={"Content-Disposition": f'attachment; filename="{filename}"'},
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error exporting packing list Excel {packing_list_id}: {str(e)}")
        raise HTTPException(
            status_code=500, detail="Failed to export packing list Excel"
        )


@router.post(
    "/packing-lists/{packing_list_id}/items", response_model=PackingListItemResponse
)
def add_item_to_packing_list(
    packing_list_id: str,
    item_data: PackingListItemCreate,
    db: Session = Depends(get_db),
    agent: User = Depends(get_sourcing_agent),
):
    """Add an item to a packing list."""
    try:
        # Verify packing list belongs to agent
        packing_list = PackingListService.get_packing_list_by_id(db, packing_list_id)
        if not packing_list:
            raise HTTPException(status_code=404, detail="Packing list not found")

        _get_my_batch(db, str(packing_list.batch_id), agent.id)

        item = PackingListService.add_item_to_packing_list(
            db=db, packing_list_id=packing_list_id, item_data=item_data.model_dump()
        )
        return item
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Error adding item to packing list {packing_list_id}: {str(e)}")
        raise HTTPException(
            status_code=500, detail="Failed to add item to packing list"
        )


@router.put("/packing-list-items/{item_id}", response_model=PackingListItemResponse)
def update_packing_list_item(
    item_id: str,
    item_data: PackingListItemUpdate,
    db: Session = Depends(get_db),
    agent: User = Depends(get_sourcing_agent),
):
    """Update a packing list item."""
    try:
        # Get item and verify it belongs to agent's batch
        item = db.query(PackingListItem).filter(PackingListItem.id == item_id).first()
        if not item:
            raise HTTPException(status_code=404, detail="Item not found")

        packing_list = (
            db.query(PackingList).filter(PackingList.id == item.packing_list_id).first()
        )
        if not packing_list:
            raise HTTPException(status_code=404, detail="Packing list not found")

        _get_my_batch(db, str(packing_list.batch_id), agent.id)

        updated_item = PackingListService.update_packing_list_item(
            db=db, item_id=item_id, item_data=item_data.model_dump(exclude_unset=True)
        )
        return updated_item
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Error updating packing list item {item_id}: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to update item")


@router.delete("/packing-lists/{packing_list_id}")
def delete_packing_list(
    packing_list_id: str,
    db: Session = Depends(get_db),
    agent: User = Depends(get_sourcing_agent),
):
    """Delete a packing list."""
    try:
        success = PackingListService.delete_packing_list(
            db=db, packing_list_id=packing_list_id, agent_id=str(agent.id)
        )

        if not success:
            raise HTTPException(
                status_code=404, detail="Packing list not found or access denied"
            )

        return {"message": "Packing list deleted successfully"}
    except Exception as e:
        logger.error(f"Error deleting packing list {packing_list_id}: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to delete packing list")


@router.get("/packing-lists", response_model=List[PackingListSummaryResponse])
def get_agent_packing_lists(
    db: Session = Depends(get_db),
    agent: User = Depends(get_sourcing_agent),
):
    """Get all packing lists created by the agent."""
    try:
        packing_lists = PackingListService.get_agent_packing_lists(db, str(agent.id))

        result = []
        for pl in packing_lists:
            result.append(
                {
                    "id": pl.id,
                    "name": pl.name,
                    "batch_id": pl.batch_id,
                    "created_at": pl.created_at,
                    "item_count": len(pl.items),
                    "qr_code_url": pl.qr_code_url,
                }
            )

        return result
    except Exception as e:
        logger.error(f"Error getting agent packing lists: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to get packing lists")


@router.post("/containers/book-cbm")
def book_cbm_direct(
    body: BookCBMRequest,
    db: Session = Depends(get_db),
    agent: User = Depends(get_sourcing_agent),
):
    """
    Book CBM directly as a sourcing agent without linking to a batch.
    Business rule:
    - If booking WITH a batch, batch must be closed (handled by /batches/{batch_id}/book-cbm).
    - Booking WITHOUT a batch is allowed as direct booking (customer-like flow).
    """
    try:
        container = (
            db.query(Container)
            .filter(
                Container.id == body.container_id,
                Container.status.in_(["open", "nearly_full"]),
            )
            .with_for_update()
            .first()
        )

        if not container:
            raise HTTPException(status_code=404, detail="Container not available")

        current_booked_cbm = (
            db.query(func.coalesce(func.sum(SeaBooking.cbm_booked), 0))
            .filter(SeaBooking.container_id == container.id)
            .scalar()
            or 0
        )
        current_booked_cbm = float(current_booked_cbm)
        current_available_cbm = max(float(container.max_cbm) - current_booked_cbm, 0)

        if current_available_cbm < body.cbm_amount:
            raise HTTPException(
                status_code=400,
                detail=f"Insufficient space. Available: {current_available_cbm:.2f} CBM",
            )

        logistics_charge = float(container.price_per_cbm) * body.cbm_amount
        sea_booking_currency = (container.currency or "TZS").upper()

        sea_booking = SeaBooking(
            container_id=container.id,
            user_id=agent.id,
            source_type="direct",
            source_id=None,
            cbm_booked=body.cbm_amount,
            logistics_charge=logistics_charge,
            currency=sea_booking_currency,
            payment_status="pending",
            goods_status="ready",
        )
        if not container.origin_warehouse or not is_china_warehouse(
            container.origin_warehouse
        ):
            raise HTTPException(
                status_code=409,
                detail="The selected sea service has no ready China forwarding warehouse.",
            )
        address = ensure_customer_china_address(
            db,
            customer=agent,
            warehouse=container.origin_warehouse,
            cargo_mode="sea",
            destination_country=(
                container.destination_warehouse.country
                if container.destination_warehouse
                and container.destination_warehouse.country
                else body.destination_country or "Destination country"
            ),
            destination_city=body.destination_city,
        )
        sea_booking.customer_china_address_id = address.id
        db.add(sea_booking)
        db.flush()

        # Update container fill and status
        container.booked_cbm = current_booked_cbm + body.cbm_amount
        fill_pct = float(container.booked_cbm) / float(container.max_cbm) * 100
        if float(container.booked_cbm) >= float(container.max_cbm):
            container.status = "full"
        elif fill_pct >= 80:
            container.status = "nearly_full"

        shipment_order = ensure_shipment_order_for_sea_booking(db, sea_booking)

        TrackingService.create_tracking_event(
            db=db,
            entity_type="sea_booking",
            entity_id=str(sea_booking.id),
            event_type="sea_booking_created",
            description=f"Direct CBM sea booking created for {body.cbm_amount} CBM",
            triggered_by=str(agent.id),
            extra_data={
                "container_id": str(container.id),
                "cbm_booked": float(sea_booking.cbm_booked),
                "logistics_charge": float(sea_booking.logistics_charge),
                "currency": sea_booking.currency,
                "source_type": "direct",
                "payment_status": sea_booking.payment_status,
            },
        )

        log_action(
            db=db,
            action="cbm_booked_direct",
            user_id=agent.id,
            entity_type="sea_booking",
            entity_id=sea_booking.id,
            metadata={
                "container_id": body.container_id,
                "cbm_amount": body.cbm_amount,
                "source_type": "direct",
            },
        )

        notify_container_booking_created(db, container, sea_booking, agent)

        db.commit()
        db.refresh(sea_booking)

        return {
            "sea_booking_id": str(sea_booking.id),
            "container_id": str(container.id),
            "cbm_booked": body.cbm_amount,
            "logistics_charge": round(logistics_charge, 2),
            "currency": sea_booking.currency,
            "tracking_number": shipment_order.tracking_number,
            "payment_status": "pending",
            "source_type": "direct",
            "message": "CBM booked successfully",
            "china_address": copy_ready_address(address),
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error booking CBM directly: {str(e)}")
        db.rollback()
        raise HTTPException(status_code=500, detail="Failed to book CBM")


@router.get("/goods/categories")
def list_available_goods_categories(
    db: Session = Depends(get_db),
    agent: User = Depends(get_sourcing_agent),
):
    """Compatibility endpoint for the platform-wide goods catalogue."""
    try:
        from app.services.goods_catalog import serialize_goods_catalog

        return serialize_goods_catalog(db)
    except Exception as e:
        logger.error(f"Error listing goods categories: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")


# ─── Financial / Commission ──────────────────────────────


@router.get("/financials")
def get_agent_financials(
    db: Session = Depends(get_db),
    agent: User = Depends(get_sourcing_agent),
):
    """Get comprehensive financial overview for the sourcing agent including batch performance metrics"""
    try:
        from app.models.sourcing import SourcingOrder
        from sqlalchemy import func

        # Get commission settings (for internal reference only)
        commission_setting = (
            db.query(CommissionSettings)
            .order_by(CommissionSettings.effective_from.desc())
            .first()
        )
        commission_rate = (
            float(commission_setting.commission_percentage)
            if commission_setting
            else 1.0
        )

        # Calculate TOTAL BATCH VALUE (sum of all order amounts)
        total_batch_value = (
            db.query(func.sum(SourcingOrder.total_product_amount))
            .filter(SourcingOrder.batch.has(agent_id=agent.id))
            .scalar()
            or 0
        )

        # Count paid orders
        paid_orders = (
            db.query(SourcingOrder)
            .filter(
                SourcingOrder.batch.has(agent_id=agent.id),
                SourcingOrder.payment_status == "paid",
            )
            .count()
        )

        # Count unpaid orders
        unpaid_orders = (
            db.query(SourcingOrder)
            .filter(
                SourcingOrder.batch.has(agent_id=agent.id),
                SourcingOrder.payment_status == "unpaid",
            )
            .count()
        )

        # Count total orders
        total_orders = (
            db.query(SourcingOrder)
            .filter(SourcingOrder.batch.has(agent_id=agent.id))
            .count()
        )
        preferred_currency = (
            db.query(SourcingBatch.currency)
            .filter(SourcingBatch.agent_id == agent.id)
            .order_by(SourcingBatch.created_at.desc())
            .limit(1)
            .scalar()
            or "TZS"
        )

        # Get recent activity (last 10 events)
        recent_activity = []
        notifications = (
            db.query(Notification)
            .filter(
                Notification.user_id == agent.id,
                Notification.type.in_(
                    ["RECEIPT_GENERATED", "PAYMENT_STATUS_UPDATED", "ORDER_COMPLETED"]
                ),
            )
            .order_by(Notification.created_at.desc())
            .limit(10)
            .all()
        )

        for notif in notifications:
            recent_activity.append(
                {
                    "id": str(notif.id),
                    "type": notif.type.lower(),
                    "description": notif.message,
                    "order_id": notif.target_id,
                    "created_at": (
                        notif.created_at.isoformat() if notif.created_at else None
                    ),
                }
            )

        return {
            "stats": {
                "totalBatchValue": float(total_batch_value),
                "totalOrders": total_orders,
                "paidOrders": paid_orders,
                "unpaidOrders": unpaid_orders,
                "commissionRate": commission_rate,  # Internal platform rate, not agent earnings
                "earningsTrend": 0,  # Placeholder for future implementation
            },
            "currency": preferred_currency,
            "recentActivity": recent_activity,
        }
    except Exception as e:
        logger.error(f"Error getting agent financials: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/receipts")
def get_agent_receipts(
    db: Session = Depends(get_db),
    agent: User = Depends(get_sourcing_agent),
):
    """Get all receipts for the sourcing agent's batches (paid orders only)"""
    try:
        # Get receipts for orders with paid status
        paid_orders = (
            db.query(SourcingOrder)
            .options(
                joinedload(SourcingOrder.receipt),
                joinedload(SourcingOrder.batch),
            )
            .filter(
                SourcingOrder.batch.has(agent_id=agent.id),
                SourcingOrder.payment_status == "paid",
            )
            .order_by(SourcingOrder.created_at.desc())
            .all()
        )

        receipt_data = []
        for order in paid_orders:
            receipt_data.append(
                {
                    "id": str(order.id),
                    "receipt_number": (
                        order.receipt.receipt_number
                        if order.receipt
                        else (
                            order.receipt_number
                            or f"RCT-{str(order.id).replace('-', '')[:8].upper()}"
                        )
                    ),
                    "customer_name": (
                        order.customer.name if order.customer else "Guest Customer"
                    ),
                    "total_amount": (
                        float(order.total_product_amount)
                        if order.total_product_amount
                        else 0
                    ),
                    "currency": order.currency or "TZS",
                    "status": "paid",
                    "generated_at": (
                        order.receipt.generated_at.isoformat()
                        if order.receipt and order.receipt.generated_at
                        else (
                            order.created_at.isoformat() if order.created_at else None
                        )
                    ),
                    "pdf_url": order.receipt.pdf_url if order.receipt else None,
                    "batch_title": order.batch.title if order.batch else None,
                    "order_id": str(order.id),
                }
            )

        return {"receipts": receipt_data}
    except Exception as e:
        logger.error(f"Error getting agent receipts: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/invoices")
def get_agent_invoices(
    db: Session = Depends(get_db),
    agent: User = Depends(get_sourcing_agent),
):
    """Get all invoices for the sourcing agent's batches (unpaid orders only)"""
    try:
        # Get invoices for orders with unpaid status
        unpaid_orders = (
            db.query(SourcingOrder)
            .options(joinedload(SourcingOrder.batch))
            .filter(
                SourcingOrder.batch.has(agent_id=agent.id),
                SourcingOrder.payment_status == "unpaid",
            )
            .order_by(SourcingOrder.created_at.desc())
            .all()
        )
        latest_invoice_by_order = _latest_invoice_log_for_orders(
            db, [order.id for order in unpaid_orders]
        )

        invoice_data = []
        for order in unpaid_orders:
            invoice_meta = latest_invoice_by_order.get(str(order.id), {})
            invoice_data.append(
                {
                    "id": str(order.id),
                    "invoice_number": invoice_meta.get("invoice_number")
                    or f"INV-{str(order.id).replace('-', '')[:8].upper()}",
                    "customer_name": (
                        order.customer.name if order.customer else "Guest Customer"
                    ),
                    "total_amount": (
                        float(order.total_product_amount)
                        if order.total_product_amount
                        else 0
                    ),
                    "currency": order.currency or "TZS",
                    "status": "unpaid",
                    "generated_at": (
                        invoice_meta.get("generated_at")
                        or (order.created_at.isoformat() if order.created_at else None)
                    ),
                    "due_date": (
                        invoice_meta.get("due_date")
                        or (
                            (order.created_at + timedelta(days=30)).isoformat()
                            if order.created_at
                            else None
                        )
                    ),
                    "pdf_url": invoice_meta.get("pdf_url"),
                    "excel_url": invoice_meta.get("excel_url"),
                    "document_status": invoice_meta.get("status", "draft"),
                    "order_reference": build_display_reference(
                        "sourcing_order", order.id, order.created_at
                    ),
                    "batch_title": order.batch.title if order.batch else None,
                    "order_id": str(order.id),
                }
            )

        return {"invoices": invoice_data}
    except Exception as e:
        logger.error(f"Error getting agent invoices: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/documents/open")
def open_agent_document(
    url: str = Query(..., min_length=10),
    _: User = Depends(get_sourcing_agent),
):
    filename = os.path.basename(urlparse(url).path or "") or "document.pdf"
    return stream_safe_document(url, filename)


@router.post("/orders/{order_id}/generate-receipt")
def generate_receipt_for_order(
    order_id: str,
    format: str = Query("both", pattern="^(excel|pdf|both)$"),
    db: Session = Depends(get_db),
    agent: User = Depends(get_sourcing_agent),
):
    """Generate receipt document(s) for a paid order in Excel/PDF."""
    try:
        # Verify the order belongs to this agent's batch
        order = (
            db.query(SourcingOrder)
            .filter(
                SourcingOrder.id == order_id, SourcingOrder.batch.has(agent_id=agent.id)
            )
            .first()
        )

        if not order:
            raise HTTPException(
                status_code=404, detail="Order not found or access denied"
            )

        if order.payment_status != "paid":
            raise HTTPException(
                status_code=400, detail="Receipt can only be generated for paid orders"
            )

        receipt = _get_or_create_order_receipt(db, order, issued_by=agent.id)
        db.commit()
        db.refresh(order)
        db.refresh(receipt)

        generated_at = datetime.utcnow().isoformat()
        receipt_data = {
            "id": str(order.id),
            "receipt_id": str(receipt.id),
            "receipt_number": receipt.receipt_number,
            "receipt_token": receipt.receipt_token,
            "order_id": str(order.id),
            "customer_name": (
                order.customer.name
                if order.customer
                else (order.guest.name if order.guest else "Guest Customer")
            ),
            "total_amount": (
                float(order.total_product_amount) if order.total_product_amount else 0.0
            ),
            "currency": order.currency or "TZS",
            "status": "paid",
            "generated_at": generated_at,
            "items": [],
        }

        # Add order items to receipt
        for item in order.items:
            product_name = item.product.name if item.product else "Unknown Product"
            receipt_data["items"].append(
                {
                    "description": product_name,
                    "quantity": item.quantity,
                    "unit_price": float(item.unit_price),
                    "total_price": float(item.total_price),
                    "currency": item.currency or "TZS",
                }
            )

        metadata = {
            "issuer": sourcing_agent_document_branding(db, agent),
            "document_number": receipt_data["receipt_number"],
            "order_id": receipt_data["order_id"],
            "customer_name": receipt_data["customer_name"],
            "currency": receipt_data["currency"],
            "status": receipt_data["status"],
            "generated_at": generated_at,
        }
        items = receipt_data["items"]

        excel_url = None
        pdf_url = None

        if format in ["excel", "both"]:
            excel_bytes = DocumentGenerationService.generate_financial_document_excel(
                "Invoice", metadata, items
            )
            excel_url = DocumentGenerationService.upload_document_to_cloudinary(
                excel_bytes, "invoice_excel", str(order.id), "xlsx"
            )

        if format in ["pdf", "both"]:
            pdf_bytes = DocumentGenerationService.generate_financial_document_pdf(
                "Invoice", metadata, items
            )
            pdf_url = DocumentGenerationService.upload_document_to_cloudinary(
                pdf_bytes, "invoice_pdf", str(order.id), "pdf"
            )

        if (format in ["excel", "both"] and not excel_url) or (
            format in ["pdf", "both"] and not pdf_url
        ):
            raise HTTPException(
                status_code=500,
                detail="Invoice document generated but failed to upload",
            )

        if format in ["excel", "both"]:
            excel_bytes = DocumentGenerationService.generate_financial_document_excel(
                "Receipt", metadata, items
            )
            excel_url = DocumentGenerationService.upload_document_to_cloudinary(
                excel_bytes, "receipt_excel", str(order.id), "xlsx"
            )

        if format in ["pdf", "both"]:
            pdf_bytes = DocumentGenerationService.generate_financial_document_pdf(
                "Receipt", metadata, items
            )
            pdf_url = DocumentGenerationService.upload_document_to_cloudinary(
                pdf_bytes, "receipt_pdf", str(order.id), "pdf"
            )

        if (format in ["excel", "both"] and not excel_url) or (
            format in ["pdf", "both"] and not pdf_url
        ):
            raise HTTPException(
                status_code=500,
                detail="Receipt document generated but failed to upload",
            )

        if pdf_url:
            receipt.pdf_url = pdf_url
        receipt.status = "issued"
        receipt.issued_by = agent.id

        receipt.voided_at = None
        receipt.voided_by = None
        db.commit()
        db.refresh(receipt)

        return {
            "receipt": receipt_data,
            "documents": {
                "requested_format": format,
                "excel_url": excel_url,
                "pdf_url": pdf_url,
            },
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error generating receipt for order {order_id}: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to generate receipt")


@router.post("/orders/{order_id}/generate-invoice")
def generate_invoice_for_order(
    order_id: str,
    format: str = Query("both", pattern="^(excel|pdf|both)$"),
    db: Session = Depends(get_db),
    agent: User = Depends(get_sourcing_agent),
):
    """Generate invoice document(s) for an unpaid order in Excel/PDF."""
    try:
        # Verify the order belongs to this agent's batch
        order = (
            db.query(SourcingOrder)
            .filter(
                SourcingOrder.id == order_id, SourcingOrder.batch.has(agent_id=agent.id)
            )
            .first()
        )

        if not order:
            raise HTTPException(
                status_code=404, detail="Order not found or access denied"
            )

        if order.payment_status != "unpaid":
            raise HTTPException(
                status_code=400,
                detail="Invoice can only be generated for unpaid orders",
            )

        generated_at = datetime.utcnow().isoformat()
        latest_invoice_meta = _latest_invoice_log_for_orders(db, [order.id]).get(
            str(order.id), {}
        )
        invoice_number = (
            latest_invoice_meta.get("invoice_number") or generate_invoice_number()
        )
        invoice_data = {
            "id": str(order.id),
            "invoice_number": invoice_number,
            "order_id": str(order.id),
            "customer_name": (
                order.customer.name
                if order.customer
                else (order.guest.name if order.guest else "Guest Customer")
            ),
            "total_amount": (
                float(order.total_product_amount) if order.total_product_amount else 0.0
            ),
            "currency": order.currency or "TZS",
            "status": "unpaid",
            "generated_at": generated_at,
            "due_date": (datetime.utcnow() + timedelta(days=30)).isoformat(),
            "items": [],
        }

        # Add order items to invoice
        for item in order.items:
            product_name = item.product.name if item.product else "Unknown Product"
            invoice_data["items"].append(
                {
                    "description": product_name,
                    "quantity": item.quantity,
                    "unit_price": float(item.unit_price),
                    "total_price": float(item.total_price),
                    "currency": item.currency or "TZS",
                }
            )

        metadata = {
            "issuer": sourcing_agent_document_branding(db, agent),
            "document_number": invoice_data["invoice_number"],
            "order_id": invoice_data["order_id"],
            "customer_name": invoice_data["customer_name"],
            "currency": invoice_data["currency"],
            "status": invoice_data["status"],
            "generated_at": generated_at,
        }
        items = invoice_data["items"]

        excel_url = None
        pdf_url = None

        if format in ["excel", "both"]:
            excel_bytes = DocumentGenerationService.generate_financial_document_excel(
                "Invoice", metadata, items
            )
            excel_url = DocumentGenerationService.upload_document_to_cloudinary(
                excel_bytes, "invoices/excel", str(order.id), "xlsx"
            )

        if format in ["pdf", "both"]:
            pdf_bytes = DocumentGenerationService.generate_financial_document_pdf(
                "Invoice", metadata, items
            )
            pdf_url = DocumentGenerationService.upload_document_to_cloudinary(
                pdf_bytes, "invoices/pdf", str(order.id), "pdf"
            )

        if (format in ["excel", "both"] and not excel_url) or (
            format in ["pdf", "both"] and not pdf_url
        ):
            raise HTTPException(
                status_code=500,
                detail="Invoice document generated but failed to upload",
            )

        log_action(
            db=db,
            action="ORDER_INVOICE_GENERATED",
            user_id=agent.id,
            entity_type="sourcing_order",
            entity_id=order.id,
            metadata={
                "invoice_number": invoice_number,
                "generated_at": generated_at,
                "due_date": invoice_data["due_date"],
                "currency": invoice_data["currency"],
                "status": "draft",
                "excel_url": excel_url,
                "pdf_url": pdf_url,
            },
        )
        db.commit()

        return {
            "invoice": invoice_data,
            "documents": {
                "requested_format": format,
                "excel_url": excel_url,
                "pdf_url": pdf_url,
            },
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error generating invoice for order {order_id}: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to generate invoice")


@router.get("/batches/{batch_id}/financials")
def batch_financials(
    batch_id: str,
    db: Session = Depends(get_db),
    agent: User = Depends(get_sourcing_agent),
):
    """Get detailed financial information for a batch"""
    try:
        batch = _get_my_batch(db, batch_id, agent.id)

        commission_setting = (
            db.query(CommissionSettings)
            .order_by(CommissionSettings.effective_from.desc())
            .first()
        )
        commission_rate = (
            float(commission_setting.commission_percentage)
            if commission_setting
            else settings.DEFAULT_COMMISSION_PERCENTAGE
        )

        total_revenue = (
            db.query(func.sum(SourcingOrder.total_product_amount))
            .filter(SourcingOrder.batch_id == batch.id)
            .scalar()
            or 0
        )

        # Platform commission (internal only)
        commission = float(total_revenue) * (commission_rate / 100)

        orders = (
            db.query(SourcingOrder)
            .options(joinedload(SourcingOrder.receipt))
            .filter(SourcingOrder.batch_id == batch.id)
            .all()
        )
        latest_invoice_by_order = _latest_invoice_log_for_orders(
            db, [order.id for order in orders]
        )

        # Calculate by PAYMENT status (not commission status)
        paid_orders_count = len([o for o in orders if o.payment_status == "paid"])
        unpaid_orders_count = len([o for o in orders if o.payment_status == "unpaid"])

        paid_orders_value = sum(
            o.total_product_amount for o in orders if o.payment_status == "paid"
        )
        unpaid_orders_value = sum(
            o.total_product_amount for o in orders if o.payment_status == "unpaid"
        )

        return {
            "batch_id": batch_id,
            "batch_title": batch.title,
            "total_orders": len(orders),
            "paid_orders": paid_orders_count,
            "unpaid_orders": unpaid_orders_count,
            "total_product_revenue": round(float(total_revenue), 2),
            "paid_orders_value": round(float(paid_orders_value), 2),
            "unpaid_orders_value": round(float(unpaid_orders_value), 2),
            "commission_rate": commission_rate,
            "commission_amount": round(commission, 2),
            "currency": batch.currency or "TZS",
            "orders": [
                {
                    "id": str(order.id),
                    "order_reference": build_display_reference(
                        "sourcing_order", order.id, order.created_at
                    ),
                    "customer_name": (
                        order.customer.name if order.customer else "Guest Customer"
                    ),
                    "total_amount": (
                        float(order.total_product_amount)
                        if order.total_product_amount
                        else 0
                    ),
                    "payment_status": order.payment_status,
                    "created_at": (
                        order.created_at.isoformat() if order.created_at else None
                    ),
                    "receipt_number": order.receipt_number,
                    "receipt_pdf_url": (
                        order.receipt.pdf_url if order.receipt else None
                    ),
                    "invoice_number": latest_invoice_by_order.get(
                        str(order.id), {}
                    ).get("invoice_number"),
                    "invoice_pdf_url": latest_invoice_by_order.get(
                        str(order.id), {}
                    ).get("pdf_url"),
                }
                for order in orders
            ],
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting batch financials for {batch_id}: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")


# ─── Batch Status Management ─────────────────────────────


@router.post("/batches/{batch_id}/open")
def open_batch(
    batch_id: str,
    db: Session = Depends(get_db),
    agent: User = Depends(get_sourcing_agent),
):
    """Open a draft batch for orders, or reopen a closed batch."""
    try:
        batch = _get_my_batch(db, batch_id, agent.id)

        if batch.status not in {"draft", "closed"}:
            raise HTTPException(
                status_code=400,
                detail="Batch must be draft or closed to open",
            )

        product_count = (
            db.query(func.count(SourcingProduct.id))
            .filter(
                SourcingProduct.batch_id == batch.id,
                SourcingProduct.status.in_(["draft", "published"]),
            )
            .scalar()
            or 0
        )
        if product_count == 0:
            raise HTTPException(
                status_code=400,
                detail="Cannot open an empty batch. Add at least one product first.",
            )

        was_closed = batch.status == "closed"
        batch.status = "open"

        TrackingService.create_tracking_event(
            db=db,
            entity_type="batch",
            entity_id=str(batch.id),
            event_type="batch_reopened" if was_closed else "batch_opened",
            description=(
                "Batch reopened for orders" if was_closed else "Batch opened for orders"
            ),
            triggered_by=str(agent.id),
            extra_data={"status": "open"},
        )

        log_action(
            db=db,
            action="batch_reopened" if was_closed else "batch_opened",
            user_id=agent.id,
            entity_type="batch",
            entity_id=batch.id,
        )

        db.commit()
        return {
            "message": (
                "Batch reopened for orders" if was_closed else "Batch opened for orders"
            ),
            "status": "open",
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error opening batch: {str(e)}")
        db.rollback()
        raise HTTPException(status_code=500, detail="Failed to open batch")


@router.post("/batches/{batch_id}/close")
def close_batch(
    batch_id: str,
    db: Session = Depends(get_db),
    agent: User = Depends(get_sourcing_agent),
):
    """Close batch - locks new orders so agent can proceed to book CBM."""
    try:
        batch = _get_my_batch(db, batch_id, agent.id)

        if batch.status != "open":
            raise HTTPException(status_code=400, detail="Batch must be open to close")

        batch.status = "closed"

        TrackingService.create_tracking_event(
            db=db,
            entity_type="batch",
            entity_id=str(batch.id),
            event_type="batch_closed",
            description="Batch closed for new orders",
            triggered_by=str(agent.id),
            extra_data={"status": "closed"},
        )

        log_action(
            db=db,
            action="batch_closed",
            user_id=agent.id,
            entity_type="batch",
            entity_id=batch.id,
        )

        db.commit()
        return {
            "message": "Batch closed. Proceed to book CBM in a container.",
            "status": "closed",
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error closing batch: {str(e)}")
        db.rollback()
        raise HTTPException(status_code=500, detail="Failed to close batch")


# ─── Express Air Cargo (Sourcing Agent) ─────────────────


class AgentExpressAirCargoBookingResponse(BaseModel):
    booking_id: str
    service_name: str
    route: str
    status: str
    weight_kg: float
    shipment_date: datetime
    cargo_type: str
    cargo_description: Optional[str]
    item_photos: List[str]
    created_at: datetime
    shipping_mark_code: Optional[str] = None


class AgentShippingLabelUpdateRequest(BaseModel):
    destination_region: Optional[str] = None
    carton_count: Optional[int] = None
    packing_list_summary: Optional[str] = None


@router.get("/express-air-cargo/options")
def agent_express_air_cargo_options(
    cargo_admin_id: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    agent: User = Depends(get_sourcing_agent),
):
    """List active Air Cargo Goods Types with the same live rates customers see."""
    cargo_types = (
        db.query(GoodsType)
        .filter(GoodsType.is_active.is_(True))
        .order_by(GoodsType.name.asc())
        .all()
    )
    active_rates = (
        db.query(AirCargoRate)
        .options(joinedload(AirCargoRate.goods_type))
        .filter(
            AirCargoRate.is_active.is_(True),
            *(
                [AirCargoRate.cargo_admin_id == cargo_admin_id]
                if cargo_admin_id
                else []
            ),
        )
        .order_by(AirCargoRate.shipping_method, AirCargoRate.price)
        .all()
    )
    rates_by_goods_type = {}
    for rate in active_rates:
        rates_by_goods_type.setdefault(str(rate.goods_type_id), []).append(
            serialize_rate(rate)
        )
    unique_routes = sorted({rate.route for rate in active_rates if rate.route})
    return {
        "service_name": "China → Africa Air Cargo",
        "route": unique_routes[0] if len(unique_routes) == 1 else "China → Africa",
        "delivery_window": "Varies by selected service",
        "allowed_weight_unit": "KG",
        "cargo_types": [
            {
                "id": str(gt.id),
                "name": gt.name,
                "is_hazardous": gt.is_hazardous,
                "requires_special_handling": gt.requires_special_handling,
                "shipping_policy": get_air_cargo_goods_policy(gt.name),
                "rates": rates_by_goods_type.get(str(gt.id), []),
            }
            for gt in cargo_types
        ],
    }


@router.post("/express-air-cargo/upload-photo")
async def agent_upload_express_air_cargo_photo(
    file: UploadFile = File(...),
    agent: User = Depends(get_sourcing_agent),
):
    """Upload an item image for an express air cargo booking."""
    allowed_types = set(settings.ALLOWED_IMAGE_TYPES) | {"image/gif"}
    if file.content_type not in allowed_types:
        raise HTTPException(
            status_code=400,
            detail="Invalid file type. Only JPEG, PNG, GIF, and WebP images are allowed.",
        )

    content = await file.read()
    if len(content) > settings.MAX_IMAGE_SIZE_MB * 1024 * 1024:
        raise HTTPException(
            status_code=400,
            detail=f"File too large. Maximum file size is {settings.MAX_IMAGE_SIZE_MB}MB.",
        )

    _, file_extension = validated_image_format(
        content, file.content_type, allow_gif=True
    )
    with tempfile.NamedTemporaryFile(delete=False, suffix=f".{file_extension}") as tmp:
        tmp.write(content)
        tmp_path = tmp.name

    try:
        result = upload_to_cloudinary(tmp_path, str(agent.id), "express_air_cargo")
        return {
            "success": True,
            "image_url": result["secure_url"],
            "public_id": result["public_id"],
        }
    finally:
        os.unlink(tmp_path)


@router.post("/express-air-cargo/book")
def agent_create_express_air_booking(
    cargo_type_id: str = Form(...),
    weight_kg: float = Form(...),
    shipment_date: datetime = Form(...),
    cargo_description: Optional[str] = Form(None),
    destination_region: str = Form(...),
    destination_country: str = Form("Tanzania"),
    carton_count: int = Form(1),
    item_photos: Optional[str] = Form("[]"),
    air_cargo_rate_id: Optional[str] = Form(None),
    quantity: float = Form(1),
    certification_acknowledged: bool = Form(False),
    customer_china_address_id: Optional[str] = Form(None),
    cargo_admin_id: Optional[str] = Form(None),
    warehouse_id: Optional[str] = Form(None),
    db: Session = Depends(get_db),
    agent: User = Depends(get_sourcing_agent),
):
    """Sourcing agent books an operator-owned China-to-Africa air service."""
    if weight_kg <= 0:
        raise HTTPException(status_code=400, detail="Weight must be greater than 0 KG")

    # Normalize timezone
    if shipment_date.tzinfo is not None:
        shipment_date = shipment_date.astimezone(timezone.utc).replace(tzinfo=None)

    if shipment_date < datetime.utcnow() + timedelta(hours=6):
        raise HTTPException(
            status_code=400, detail="Shipment date must be at least 6 hours from now"
        )

    if not destination_region.strip():
        raise HTTPException(status_code=400, detail="Destination region is required")
    if not destination_country.strip():
        raise HTTPException(status_code=400, detail="Destination country is required")

    if carton_count <= 0:
        raise HTTPException(status_code=400, detail="Carton count must be at least 1")
    if quantity <= 0:
        raise HTTPException(
            status_code=400, detail="Quantity must be greater than zero"
        )

    cargo_type = (
        db.query(GoodsType)
        .filter(
            GoodsType.id == cargo_type_id,
            GoodsType.is_active.is_(True),
        )
        .first()
    )
    if not cargo_type:
        raise HTTPException(status_code=400, detail="Invalid cargo type selected")
    goods_policy = get_air_cargo_goods_policy(cargo_type.name)
    if goods_policy["requires_certification"] and not certification_acknowledged:
        raise HTTPException(
            status_code=422,
            detail=(
                "Import certification acknowledgement is required for this Goods Type. "
                "Food, medicines, cosmetics, fruits, perfumes, and supplements cannot "
                "use 1–3 day Express until the required permit has been obtained."
            ),
        )

    selected_rate = None
    quoted_total = None
    if air_cargo_rate_id:
        selected_rate = get_matching_rate(
            db,
            rate_id=air_cargo_rate_id,
            goods_type_id=str(cargo_type.id),
            weight_kg=weight_kg,
            cargo_admin_id=cargo_admin_id,
        )
        quoted_total = calculate_rate_total(
            selected_rate, weight_kg=weight_kg, quantity=quantity
        )

    try:
        photos = json.loads(item_photos or "[]")
        if not isinstance(photos, list):
            raise ValueError
    except Exception:
        raise HTTPException(
            status_code=400, detail="item_photos must be a JSON array of URLs"
        )

    booking = ExpressAirCargoBooking(
        customer_id=agent.id,  # agent is stored as the booking owner
        cargo_type_id=cargo_type.id,
        cargo_description=cargo_description,
        weight_kg=round(weight_kg, 2),
        air_cargo_rate_id=selected_rate.id if selected_rate else None,
        pricing_type=selected_rate.pricing_type if selected_rate else None,
        rate_amount=selected_rate.price if selected_rate else None,
        rate_currency=selected_rate.currency if selected_rate else None,
        quantity=round(quantity, 2) if selected_rate else None,
        quoted_total=quoted_total,
        route_label=selected_rate.route if selected_rate else DEFAULT_AIR_CARGO_ROUTE,
        service_label=(
            f"{selected_rate.shipping_method} — {selected_rate.transit_time}"
            if selected_rate
            else "Quotation required"
        ),
        shipment_date=shipment_date,
        photo_urls=json.dumps(photos),
        status="pending",
    )
    customer_address, forwarding_warehouse = prepare_user_air_china_address(
        db,
        user=agent,
        destination_country=destination_country.strip(),
        destination_city=destination_region.strip(),
        preferred_address_id=customer_china_address_id,
        cargo_admin_id=cargo_admin_id,
        warehouse_id=warehouse_id,
    )
    booking.cargo_admin_id = forwarding_warehouse.admin_id
    booking.warehouse_id = forwarding_warehouse.id
    booking.customer_china_address_id = customer_address.id
    db.add(booking)
    db.flush()
    ensure_shipment_order_for_air_booking(
        db, booking, destination_region=destination_region
    )

    create_shipping_mark(
        db,
        booking_id=booking.id,
        cargo_type="AIR",
        customer_name=agent.name,
        customer_phone=agent.phone_number,
        destination_region=destination_region,
        packing_list_summary=cargo_description,
        carton_count=carton_count,
        air_booking_id=booking.id,
    )

    db.commit()
    db.refresh(booking)

    # Create tracking event for the new booking
    TrackingService.create_tracking_event(
        db=db,
        entity_type="booking",
        entity_id=str(booking.id),
        event_type="booking_created",
        description=f"Express air cargo booking created by sourcing agent for {weight_kg}kg shipment",
        triggered_by=str(agent.id),
        extra_data={
            "cargo_type": (
                cargo_type.name if hasattr(cargo_type, "name") else str(cargo_type.id)
            ),
            "weight_kg": float(booking.weight_kg),
            "destination_region": destination_region,
            "carton_count": carton_count,
            "status": booking.status,
            "quoted_total": float(quoted_total) if quoted_total is not None else None,
            "quotation_required": selected_rate is None,
        },
    )

    log_action(
        db=db,
        action="AGENT_EXPRESS_AIR_BOOKING_CREATED",
        user_id=agent.id,
        entity_type="express_air_booking",
        entity_id=booking.id,
        metadata={
            "cargo_type_id": str(cargo_type.id),
            "weight_kg": float(booking.weight_kg),
            "destination_region": destination_region,
            "carton_count": carton_count,
            "air_cargo_rate_id": str(selected_rate.id) if selected_rate else None,
            "quoted_total": float(quoted_total) if quoted_total is not None else None,
        },
    )
    db.commit()
    db.refresh(booking)

    return _agent_express_booking_detail(booking)


@router.get("/express-air-cargo/bookings")
def agent_list_express_air_bookings(
    db: Session = Depends(get_db),
    agent: User = Depends(get_sourcing_agent),
):
    """List agent's own express air cargo bookings."""
    bookings = (
        db.query(ExpressAirCargoBooking)
        .options(
            joinedload(ExpressAirCargoBooking.cargo_type),
            joinedload(ExpressAirCargoBooking.shipping_mark),
        )
        .filter(ExpressAirCargoBooking.customer_id == agent.id)
        .order_by(ExpressAirCargoBooking.created_at.desc())
        .all()
    )
    return [_agent_express_booking_detail(b) for b in bookings]


@router.get("/express-air-cargo/{booking_id}/shipping-label")
def agent_get_express_air_cargo_label(
    booking_id: str,
    db: Session = Depends(get_db),
    agent: User = Depends(get_sourcing_agent),
):
    """Get printable shipping label for an agent's express air cargo booking."""
    booking = (
        db.query(ExpressAirCargoBooking)
        .options(
            joinedload(ExpressAirCargoBooking.cargo_type),
            joinedload(ExpressAirCargoBooking.shipping_mark),
        )
        .filter(
            ExpressAirCargoBooking.id == booking_id,
            ExpressAirCargoBooking.customer_id == agent.id,
        )
        .first()
    )
    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found")

    mark = booking.shipping_mark
    if not mark:
        mark = create_shipping_mark(
            db,
            booking_id=booking.id,
            cargo_type="AIR",
            customer_name=agent.name,
            customer_phone=agent.phone_number,
            destination_region="Unknown",
            packing_list_summary=booking.cargo_description,
            carton_count=1,
            air_booking_id=booking.id,
        )
        db.commit()
        db.refresh(booking)

    company = operator_document_branding(db, booking.cargo_admin_id)
    label = build_printable_label(mark, company["name"])
    photos = []
    if booking.photo_urls:
        try:
            photos = json.loads(booking.photo_urls)
            if not isinstance(photos, list):
                photos = []
        except Exception:
            photos = []

    # Get cargo admin warehouse information if available (air cargo specific)
    warehouse_info = None
    if booking.cargo_admin_id:
        from app.models.container import Warehouse

        # Get the air cargo warehouse for the cargo admin (prefer air or both type)
        warehouse = (
            db.query(Warehouse)
            .filter(
                Warehouse.admin_id == booking.cargo_admin_id,
                Warehouse.warehouse_type.in_(["air", "both"]),
            )
            .order_by(Warehouse.created_at)
            .first()
        )

        if warehouse:
            warehouse_info = {
                "name": warehouse.name,
                "address": warehouse.address or warehouse.location,
                "city": warehouse.city,
                "state": warehouse.state,
                "country": warehouse.country,
                "postal_code": warehouse.postal_code,
                "contact_name": warehouse.contact_name_1,
                "contact_phone": warehouse.contact_phone_1,
                "full_address": f"{warehouse.address or warehouse.location}, {warehouse.city or ''}, {warehouse.state or ''}, {warehouse.country or ''}".strip(
                    ", "
                ),
                "warehouse_type": warehouse.warehouse_type,
            }

    return {
        "company": company,
        "booking": {
            "booking_id": str(booking.id),
            "tracking_number": booking.tracking_number,
            "status": booking.status,
            "shipment_date": booking.shipment_date,
            "weight_kg": float(booking.weight_kg),
            "route_label": booking.route_label,
            "service_label": booking.service_label,
            "cargo_type": {
                "id": str(booking.cargo_type_id),
                "name": booking.cargo_type.name if booking.cargo_type else None,
            },
        },
        "agent": {
            "name": agent.name,
            "phone_number": agent.phone_number,
        },
        "label": label,
        "item_photos": photos,
        "warehouse": warehouse_info,
    }


@router.patch("/express-air-cargo/{booking_id}/shipping-label")
def agent_update_express_air_cargo_label(
    booking_id: str,
    body: AgentShippingLabelUpdateRequest,
    db: Session = Depends(get_db),
    agent: User = Depends(get_sourcing_agent),
):
    """Update shipping label fields for an agent's express air cargo booking."""
    booking = (
        db.query(ExpressAirCargoBooking)
        .options(joinedload(ExpressAirCargoBooking.shipping_mark))
        .filter(
            ExpressAirCargoBooking.id == booking_id,
            ExpressAirCargoBooking.customer_id == agent.id,
        )
        .first()
    )
    if not booking or not booking.shipping_mark:
        raise HTTPException(status_code=404, detail="Shipping label not found")

    mark = booking.shipping_mark

    if body.destination_region is not None:
        dest = body.destination_region.strip()
        if not dest:
            raise HTTPException(
                status_code=400, detail="Destination region is required"
            )
        mark.destination_region = dest
        mark.shipping_mark_code = generate_shipping_mark_code(
            "AIR", dest, str(mark.booking_id)
        )

    if body.carton_count is not None:
        if body.carton_count < 1 or body.carton_count > 999:
            raise HTTPException(
                status_code=400, detail="Carton count must be between 1 and 999"
            )
        mark.carton_count = body.carton_count

    if body.packing_list_summary is not None:
        mark.packing_list_summary = body.packing_list_summary.strip() or None

    db.commit()
    db.refresh(mark)

    return {"message": "Shipping label updated", "label": build_printable_label(mark)}


def _agent_express_booking_detail(booking: ExpressAirCargoBooking) -> dict:
    photos = []
    if booking.photo_urls:
        try:
            photos = json.loads(booking.photo_urls)
        except Exception:
            photos = []

    shipping_mark = None
    if booking.shipping_mark:
        shipping_mark = booking.shipping_mark.shipping_mark_code

    return {
        "booking_id": str(booking.id),
        "service_name": booking.service_label,
        "route": booking.route_label,
        "status": booking.status,
        "weight_kg": float(booking.weight_kg),
        "shipment_date": booking.shipment_date,
        "cargo_type": booking.cargo_type.name if booking.cargo_type else "Unknown",
        "cargo_description": booking.cargo_description,
        "item_photos": photos,
        "created_at": booking.created_at,
        "shipping_mark_code": shipping_mark,
        "pricing": (
            {
                "rate_id": str(booking.air_cargo_rate_id),
                "pricing_type": booking.pricing_type,
                "rate": float(booking.rate_amount),
                "currency": booking.rate_currency,
                "quantity": float(booking.quantity or 1),
                "quoted_total": float(booking.quoted_total),
            }
            if booking.quoted_total is not None
            else None
        ),
        "quotation_required": booking.air_cargo_rate_id is None,
        "china_address": (
            copy_ready_address(booking.customer_china_address)
            if booking.customer_china_address
            else None
        ),
    }


# ─── Health Check ────────────────────────────────────────


@router.get("/health")
def health_check():
    """Health check endpoint for the sourcing agent API"""
    return {
        "status": "healthy",
        "service": "sourcing_agent",
        "timestamp": datetime.utcnow().isoformat(),
        "features": {
            "instagram_import": settings.ENABLE_INSTAGRAM_IMPORT,
            "direct_upload": settings.ENABLE_DIRECT_UPLOAD,
            "cloudinary_configured": all(
                [
                    settings.CLOUDINARY_CLOUD_NAME,
                    settings.CLOUDINARY_API_KEY,
                    settings.CLOUDINARY_API_SECRET,
                ]
            ),
        },
    }


# ─── Notifications ─────────────────────────────────────


@router.get("/notifications")
def get_agent_notifications(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_sourcing_agent),
):
    """Get all notifications for the sourcing agent user."""
    notifications = (
        db.query(Notification)
        .filter(Notification.user_id == current_user.id)
        .order_by(Notification.created_at.desc())
        .limit(50)
        .all()
    )

    unread_count = (
        db.query(Notification)
        .filter(
            Notification.user_id == current_user.id, Notification.is_read.is_(False)
        )
        .count()
    )

    return {
        "notifications": [
            {
                "id": str(n.id),
                "type": n.type,
                "message": n.message,
                "is_read": n.is_read,
                "target_type": n.target_type,
                "target_id": str(n.target_id) if n.target_id else None,
                "created_at": n.created_at.isoformat(),
            }
            for n in notifications
        ],
        "unread_count": unread_count,
    }


# ─── Helpers ─────────────────────────────────────────────


def _get_my_batch(db: Session, batch_id: str, agent_id) -> SourcingBatch:
    """Get batch and verify ownership"""
    batch = (
        db.query(SourcingBatch)
        .filter(
            SourcingBatch.id == batch_id,
            SourcingBatch.agent_id == agent_id,
        )
        .first()
    )

    if not batch:
        raise HTTPException(
            status_code=404,
            detail="Batch not found or you don't have permission to access it",
        )
    return batch


def _get_manageable_batch(
    db: Session, batch_id: str, current_user: User
) -> SourcingBatch:
    """Return a batch its creator or a super admin may manage."""
    batch = db.query(SourcingBatch).filter(SourcingBatch.id == batch_id).first()
    if not batch or (
        current_user.role != "super_admin" and batch.agent_id != current_user.id
    ):
        raise HTTPException(
            status_code=404,
            detail="Batch not found or you don't have permission to manage it",
        )
    return batch


def _batch_summary(b: SourcingBatch) -> dict:
    """Generate batch summary"""
    goods_types = []
    seen_goods_type_ids = set()
    for product in b.products:
        goods_type = product.goods_type
        if not goods_type or goods_type.id in seen_goods_type_ids:
            continue
        seen_goods_type_ids.add(goods_type.id)
        goods_types.append(
            {
                "id": str(goods_type.id),
                "name": goods_type.name,
                "is_hazardous": goods_type.is_hazardous,
            }
        )
    return {
        "id": str(b.id),
        "title": b.title,
        "description": b.description,
        "currency": b.currency or "TZS",
        "shipping_fee_per_cbm": float(b.shipping_fee_per_cbm or 0),
        "shipping_method": b.shipping_method or "PER_CBM",
        "status": b.status,
        "created_at": b.created_at.isoformat() if b.created_at else None,
        "goods_types": goods_types,
        "total_products": len(b.products),
        "total_orders": len(b.orders),
    }


# ─── Order Management ────────────────────────────────────


@router.get("/orders/{order_id}")
def get_agent_order_detail(
    order_id: str,
    db: Session = Depends(get_db),
    agent: User = Depends(get_sourcing_agent),
):
    """Get detailed sourcing order info for an agent-owned batch order."""
    order = (
        db.query(SourcingOrder)
        .options(
            joinedload(SourcingOrder.batch),
            joinedload(SourcingOrder.customer),
            joinedload(SourcingOrder.guest),
            joinedload(SourcingOrder.items).joinedload(SourcingOrderItem.product),
            joinedload(SourcingOrder.receipt),
        )
        .filter(
            SourcingOrder.id == order_id,
            SourcingOrder.batch.has(agent_id=agent.id),
        )
        .first()
    )
    if not order:
        raise HTTPException(status_code=404, detail="Order not found or access denied")

    invoice_meta = _latest_invoice_log_for_orders(db, [order.id]).get(str(order.id), {})

    return {
        "id": str(order.id),
        "order_reference": build_display_reference(
            "sourcing_order", order.id, order.created_at
        ),
        "batch_id": str(order.batch_id),
        "batch_title": order.batch.title if order.batch else None,
        "customer_name": _resolve_order_customer_name(order),
        "customer_phone": (
            order.customer.phone_number
            if order.customer and order.customer.phone_number
            else (order.guest.phone_number if order.guest else None)
        ),
        "submitted_by": order.submitted_by,
        "payment_status": order.payment_status,
        "delivery_status": order.delivery_status,
        "total_product_amount": float(order.total_product_amount or 0),
        "currency": order.currency or (order.batch.currency if order.batch else "TZS"),
        "created_at": order.created_at.isoformat() if order.created_at else None,
        "receipt": (
            {
                "id": str(order.receipt.id),
                "receipt_number": order.receipt.receipt_number,
                "receipt_token": order.receipt.receipt_token,
                "pdf_url": order.receipt.pdf_url,
                "status": order.receipt.status,
                "generated_at": (
                    order.receipt.generated_at.isoformat()
                    if order.receipt.generated_at
                    else None
                ),
            }
            if order.receipt
            else None
        ),
        "invoice": (
            {
                "invoice_number": invoice_meta.get("invoice_number"),
                "pdf_url": invoice_meta.get("pdf_url"),
                "excel_url": invoice_meta.get("excel_url"),
                "generated_at": invoice_meta.get("generated_at"),
                "due_date": invoice_meta.get("due_date"),
                "status": invoice_meta.get("status", "draft"),
            }
            if invoice_meta
            else None
        ),
        "items": [
            {
                "id": str(item.id),
                "product_id": str(item.product_id),
                "product_name": (
                    item.product.name
                    if item.product and item.product.name
                    else "Unknown Product"
                ),
                "quantity": int(item.quantity or 0),
                "unit_price": float(item.unit_price or 0),
                "total_price": float(item.total_price or 0),
                "total_cbm": float(item.total_cbm or 0),
                "currency": item.currency or order.currency or "TZS",
            }
            for item in order.items
        ],
    }


@router.put("/batches/{batch_id}/orders/{order_id}")
def update_order_status(
    batch_id: str,
    order_id: str,
    body: dict,
    db: Session = Depends(get_db),
    agent: User = Depends(get_sourcing_agent),
):
    """Update order status and notify customer."""
    try:
        from app.services.realtime_notifications import create_notification

        # Verify batch ownership
        batch = _get_my_batch(db, batch_id, agent.id)

        # Get the order
        order = (
            db.query(SourcingOrder)
            .filter(SourcingOrder.id == order_id, SourcingOrder.batch_id == batch.id)
            .first()
        )

        if not order:
            raise HTTPException(status_code=404, detail="Order not found")

        # Validate and update delivery status
        if "delivery_status" in body:
            valid_statuses = [
                "not_arrived",
                "arrived",
                "in_transit",
                "delivered",
                "cancelled",
            ]
            if body["delivery_status"] not in valid_statuses:
                raise HTTPException(
                    status_code=400,
                    detail=f"Invalid delivery status. Must be one of: {', '.join(valid_statuses)}",
                )
            order.delivery_status = body["delivery_status"]

        # Handle goods collection
        if "collected_at" in body:
            if body["collected_at"]:
                from datetime import datetime

                order.collected_at = datetime.fromisoformat(body["collected_at"])
                # Auto-update commission status when goods are collected
                order.commission_status = "earned"
            else:
                order.collected_at = None
                order.commission_status = "pending"

        # Update commission status (if explicitly provided)
        if "commission_status" in body:
            if body["commission_status"] in ["pending", "earned"]:
                order.commission_status = body["commission_status"]
            else:
                raise HTTPException(
                    status_code=400,
                    detail="Commission status must be 'pending' or 'earned'",
                )

        db.commit()
        db.refresh(order)

        # Send notification to customer
        customer_user_id = None
        if order.customer_id:
            customer_user_id = order.customer_id
        elif order.guest_id:
            # For guest orders, we might not have a user ID to notify
            pass

        if customer_user_id:
            notification_data = {
                "user_id": customer_user_id,
                "notification_type": "ORDER_STATUS_UPDATED",
                "message": f"Your order #{str(order.id)[:8]} status has been updated to '{order.delivery_status}'",
                "target_type": "sourcing_order",
                "target_id": order.id,
            }
            create_notification(db, **notification_data)
            db.commit()

        return {
            "id": str(order.id),
            "delivery_status": order.delivery_status,
            "commission_status": order.commission_status,
            "collected_at": (
                order.collected_at.isoformat() if order.collected_at else None
            ),
            "message": "Order updated successfully",
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating order: {str(e)}")
        db.rollback()
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/orders/{order_id}/update-payment-status")
def update_order_payment_status(
    order_id: str,
    payment_status: str = Query(..., pattern="^(unpaid|paid)$"),
    db: Session = Depends(get_db),
    agent: User = Depends(get_sourcing_agent),
):
    """Update payment status of an order (unpaid or paid)"""
    try:
        # Verify the order belongs to this agent's batch
        order = (
            db.query(SourcingOrder)
            .filter(
                SourcingOrder.id == order_id, SourcingOrder.batch.has(agent_id=agent.id)
            )
            .first()
        )

        if not order:
            raise HTTPException(
                status_code=404, detail="Order not found or access denied"
            )

        if order.payment_status == payment_status:
            return {
                "message": "Payment status unchanged",
                "order_id": str(order.id),
                "payment_status": order.payment_status,
            }

        # Update payment status
        old_status = order.payment_status
        order.payment_status = payment_status
        db.commit()
        db.refresh(order)

        # Log the action
        log_action(
            db=db,
            action="PAYMENT_STATUS_UPDATED",
            user_id=agent.id,
            entity_type="sourcing_order",
            entity_id=order.id,
            metadata={
                "old_status": old_status,
                "new_status": payment_status,
                "order_total": (
                    float(order.total_product_amount)
                    if order.total_product_amount
                    else 0
                ),
            },
        )

        # If marking as paid, ensure persistent receipt identity exists
        if payment_status == "paid":
            _get_or_create_order_receipt(db, order, issued_by=agent.id)
            db.commit()
            db.refresh(order)

        return {
            "message": "Payment status updated successfully",
            "order_id": str(order.id),
            "payment_status": order.payment_status,
            "receipt_number": order.receipt_number,
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating payment status for order {order_id}: {str(e)}")
        db.rollback()
        raise HTTPException(status_code=500, detail="Failed to update payment status")


@router.post("/orders/{order_id}/share-invoice")
def share_invoice_with_customer(
    order_id: str,
    db: Session = Depends(get_db),
    agent: User = Depends(get_sourcing_agent),
):
    """Share invoice with customer via platform notification"""
    try:
        # Verify the order belongs to this agent's batch
        order = (
            db.query(SourcingOrder)
            .filter(
                SourcingOrder.id == order_id, SourcingOrder.batch.has(agent_id=agent.id)
            )
            .first()
        )

        if not order:
            raise HTTPException(
                status_code=404, detail="Order not found or access denied"
            )

        if not order.customer_id:
            raise HTTPException(
                status_code=400, detail="Cannot share invoice with guest customer"
            )

        if order.payment_status != "unpaid":
            raise HTTPException(
                status_code=400,
                detail="Can only share invoice for unpaid orders",
            )

        latest_invoice_meta = _latest_invoice_log_for_orders(db, [order.id]).get(
            str(order.id), {}
        )
        invoice_number = latest_invoice_meta.get("invoice_number")
        if not invoice_number:
            raise HTTPException(
                status_code=400,
                detail="Generate invoice first before sharing with customer",
            )

        # Create notification for customer
        notification_message = (
            f"New invoice {invoice_number} has been generated for your order. "
            "Please check your financial dashboard to view and pay."
        )

        new_notification = Notification(
            user_id=order.customer_id,
            type="invoice_shared",
            message=notification_message,
            priority="info",
            target_type="sourcing_order",
            target_id=order.id,
        )

        db.add(new_notification)
        db.commit()

        return {
            "success": True,
            "message": "Invoice shared successfully with customer",
            "customer_id": str(order.customer_id),
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error sharing invoice for order {order_id}: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to share invoice")


# Mount public registration + super-admin registration management routes
# under the same sourcing_agent domain entrypoint.
