"""
Models: SourcingBatch, BatchGoodsType, BatchShareToken, SourcingProduct, SourcingOrder, SourcingOrderItem
Aligned with Sahajomy Platform v3.0 spec.
"""

import uuid
from datetime import datetime

from app.database import Base
from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Column,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import relationship


class SourcingBatch(Base):
    """
    Created by Sourcing Agents. Aggregates customer demand.
    Goods types are derived from its products. Earns 1% commission after collection.
    """

    __tablename__ = "sourcing_batches"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    agent_id = Column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    title = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)
    currency = Column(
        String(3), nullable=False, default="TZS", server_default="TZS"
    )  # Default currency for prices shown in this batch
    shipping_fee_per_cbm = Column(
        Numeric(18, 2), nullable=False, default=0, server_default="0"
    )
    shipping_method = Column(
        String(20), nullable=False, default="PER_CBM", server_default="PER_CBM"
    )
    status = Column(String(20), nullable=False, default="draft", index=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        CheckConstraint(
            "status IN ('draft','open','closed','completed')", name="chk_batch_status"
        ),
        CheckConstraint(
            "currency IN ('TZS', 'RMB', 'USD')", name="chk_sourcing_batch_currency"
        ),
        CheckConstraint(
            "shipping_method IN ('PER_CBM', 'FREE_SHIPPING')",
            name="chk_sourcing_batch_shipping_method",
        ),
    )

    agent = relationship("User", back_populates="sourcing_batches")
    goods_types = relationship(
        "BatchGoodsType", back_populates="batch", cascade="all, delete-orphan"
    )  # Legacy preselected types, retained for historical records only.
    share_tokens = relationship(
        "BatchShareToken", back_populates="batch", cascade="all, delete-orphan"
    )
    products = relationship(
        "SourcingProduct", back_populates="batch", cascade="all, delete-orphan"
    )
    orders = relationship("SourcingOrder", back_populates="batch")
    packing_lists = relationship(
        "PackingList", back_populates="batch", cascade="all, delete-orphan"
    )

    # ================= AIR CARGO BOOKINGS =================
    # Relationship to express air cargo bookings
    # Allows sourcing agents to book air cargo for their batches
    air_bookings = relationship(
        "ExpressAirCargoBooking", back_populates="batch", cascade="all, delete-orphan"
    )


class BatchGoodsType(Base):
    """Legacy batch-level type selection retained for historical records."""

    __tablename__ = "batch_goods_types"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    batch_id = Column(
        UUID(as_uuid=True),
        ForeignKey("sourcing_batches.id", ondelete="CASCADE"),
        nullable=False,
    )
    goods_type_id = Column(
        UUID(as_uuid=True), ForeignKey("goods_types.id"), nullable=False
    )

    batch = relationship("SourcingBatch", back_populates="goods_types")
    goods_type = relationship("GoodsType", back_populates="batch_goods_types")


class BatchShareToken(Base):
    """Secure link for guests to access a specific batch."""

    __tablename__ = "batch_share_tokens"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    batch_id = Column(
        UUID(as_uuid=True),
        ForeignKey("sourcing_batches.id", ondelete="CASCADE"),
        nullable=False,
    )
    token = Column(String(120), unique=True, nullable=False)
    expires_at = Column(DateTime, nullable=True)
    max_views = Column(Integer, nullable=True)
    current_views = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)

    batch = relationship("SourcingBatch", back_populates="share_tokens")


class SourcingProduct(Base):
    __tablename__ = "sourcing_products"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    batch_id = Column(
        UUID(as_uuid=True),
        ForeignKey("sourcing_batches.id", ondelete="CASCADE"),
        nullable=False,
    )
    goods_type_id = Column(
        UUID(as_uuid=True),
        ForeignKey("goods_types.id", ondelete="SET NULL"),
        nullable=True,
    )
    name = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)
    cbm_per_unit = Column(Numeric(10, 4), nullable=False)
    price_per_unit = Column(Numeric(18, 2), nullable=False)
    minimum_order_quantity = Column(Integer, nullable=False, default=1)
    image_url = Column(Text, nullable=True)
    # Customer-facing merchandising data.  These remain on the canonical
    # sourcing product rather than introducing a parallel public catalogue.
    additional_image_urls = Column(
        JSONB, nullable=False, default=list, server_default="[]"
    )
    public_attributes = Column(JSONB, nullable=False, default=dict, server_default="{}")
    attribute_image_map = Column(
        JSONB, nullable=False, default=dict, server_default="{}"
    )
    status = Column(String(20), nullable=False, default="draft", server_default="draft")
    published_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    batch = relationship("SourcingBatch", back_populates="products")
    goods_type = relationship("GoodsType")
    variants = relationship(
        "SourcingProductVariant", back_populates="product", cascade="all, delete-orphan"
    )
    order_items = relationship("SourcingOrderItem", back_populates="product")
    agizisha_orders = relationship("AgizishaOrder", back_populates="product")

    __table_args__ = (
        CheckConstraint(
            "status IN ('draft','published','archived')",
            name="chk_sourcing_product_status",
        ),
        Index("ix_sourcing_products_public_visibility", "status", "goods_type_id"),
    )


class SourcingProductVariant(Base):
    """A customer-selectable price and availability combination for a product."""

    __tablename__ = "sourcing_product_variants"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    product_id = Column(
        UUID(as_uuid=True),
        ForeignKey("sourcing_products.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    option_values = Column(JSONB, nullable=False, default=dict, server_default="{}")
    price_per_unit = Column(Numeric(18, 2), nullable=False)
    stock_quantity = Column(Integer, nullable=False, default=0, server_default="0")
    is_active = Column(Boolean, nullable=False, default=True, server_default="true")
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )

    __table_args__ = (
        CheckConstraint(
            "stock_quantity >= 0", name="chk_sourcing_product_variant_stock"
        ),
    )

    product = relationship("SourcingProduct", back_populates="variants")
    agizisha_orders = relationship("AgizishaOrder", back_populates="product_variant")


class AgizishaOrder(Base):
    """Public product request assigned to the sourcing agent who owns its batch.

    This is intentionally separate from ``SourcingOrder``. A SourcingOrder is a
    priced, fulfilment-oriented batch order; an AgizishaOrder is an early-stage
    public enquiry that must not expose internal shipping or sourcing values.
    """

    __tablename__ = "agizisha_orders"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    product_id = Column(
        UUID(as_uuid=True),
        ForeignKey("sourcing_products.id"),
        nullable=False,
        index=True,
    )
    product_variant_id = Column(
        UUID(as_uuid=True),
        ForeignKey("sourcing_product_variants.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    sourcing_agent_id = Column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=True, index=True
    )
    customer_name = Column(String(150), nullable=False)
    whatsapp_number = Column(String(20), nullable=False, index=True)
    quantity = Column(Integer, nullable=True)
    quoted_unit_price = Column(Numeric(18, 2), nullable=True)
    selected_options = Column(JSONB, nullable=False, default=dict, server_default="{}")
    status = Column(String(30), nullable=False, default="NEW", index=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    updated_at = Column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )

    __table_args__ = (
        CheckConstraint(
            "status IN ('NEW','CONTACTED','QUOTATION_SENT','CONFIRMED','COMPLETED','CANCELLED')",
            name="chk_agizisha_order_status",
        ),
        CheckConstraint(
            "quantity IS NULL OR quantity >= 1", name="chk_agizisha_order_quantity"
        ),
    )

    product = relationship("SourcingProduct", back_populates="agizisha_orders")
    product_variant = relationship(
        "SourcingProductVariant", back_populates="agizisha_orders"
    )
    sourcing_agent = relationship(
        "User", back_populates="agizisha_orders", foreign_keys=[sourcing_agent_id]
    )


class SourcingOrder(Base):
    """
    Placed by customers or guests.
    Commission = 1% of total_product_amount.
    Commission becomes 'earned' only when batch closed AND goods collected.
    """

    __tablename__ = "sourcing_orders"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    batch_id = Column(
        UUID(as_uuid=True), ForeignKey("sourcing_batches.id"), nullable=False
    )
    customer_id = Column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=True
    )  # null if guest
    guest_id = Column(
        UUID(as_uuid=True), ForeignKey("guests.id"), nullable=True
    )  # null if user
    submitted_by = Column(String(20), nullable=False)  # user | guest
    total_product_amount = Column(Numeric(20, 2), nullable=True)
    commission_amount = Column(Numeric(20, 2), nullable=True)
    currency = Column(
        String(3), nullable=True, default="TZS"
    )  # Currency code: TZS, RMB, or USD
    commission_status = Column(String(20), default="pending")  # pending | earned
    delivery_status = Column(String(20), default="not_arrived")
    payment_status = Column(String(20), default="unpaid")  # unpaid | paid
    is_urgent = Column(Boolean, nullable=False, default=False)
    receipt_number = Column(String(50), unique=True, nullable=True)
    receipt_token = Column(String(120), unique=True, nullable=True)
    collected_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        CheckConstraint("submitted_by IN ('user','guest')", name="chk_submitted_by"),
        CheckConstraint(
            "commission_status IN ('pending','earned')", name="chk_commission_status"
        ),
        CheckConstraint(
            "payment_status IN ('unpaid','paid')", name="chk_payment_status"
        ),
        CheckConstraint(
            "currency IN ('TZS', 'RMB', 'USD')", name="chk_sourcing_order_currency"
        ),
    )

    batch = relationship("SourcingBatch", back_populates="orders")
    customer = relationship("User", back_populates="sourcing_orders")
    guest = relationship("Guest", back_populates="sourcing_orders")
    items = relationship(
        "SourcingOrderItem", back_populates="order", cascade="all, delete-orphan"
    )
    receipt = relationship("Receipt", back_populates="order", uselist=False)


class SourcingOrderItem(Base):
    __tablename__ = "sourcing_order_items"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    order_id = Column(
        UUID(as_uuid=True),
        ForeignKey("sourcing_orders.id", ondelete="CASCADE"),
        nullable=False,
    )
    product_id = Column(
        UUID(as_uuid=True), ForeignKey("sourcing_products.id"), nullable=False
    )
    quantity = Column(Integer, nullable=False)
    unit_price = Column(Numeric(18, 2), nullable=False)
    total_price = Column(Numeric(20, 2), nullable=False)
    currency = Column(
        String(3), nullable=True, default="TZS"
    )  # Currency code: TZS, RMB, or USD
    total_cbm = Column(Numeric(10, 4), nullable=False)

    order = relationship("SourcingOrder", back_populates="items")
    product = relationship("SourcingProduct", back_populates="order_items")

    __table_args__ = (
        CheckConstraint(
            "currency IN ('TZS', 'RMB', 'USD')", name="chk_sourcing_order_item_currency"
        ),
    )
