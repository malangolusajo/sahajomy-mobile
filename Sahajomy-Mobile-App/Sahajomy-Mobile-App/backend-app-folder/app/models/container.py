"""
Models: Route, Warehouse, GoodsCategory, GoodsType, Container, SeaBooking, SeaBookingGoods
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
    UniqueConstraint,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import relationship


class Route(Base):
    __tablename__ = "routes"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    origin = Column(String(150), nullable=False)
    destination = Column(String(150), nullable=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    containers = relationship("Container", back_populates="route")


class Warehouse(Base):
    __tablename__ = "warehouses"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    admin_id = Column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    name = Column(String(150), nullable=False)
    location = Column(Text, nullable=False)
    country = Column(String(100), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    # NEW FIELDS - Add these
    country_code = Column(String(2), nullable=True)
    state = Column(String(100), nullable=True)
    state_code = Column(String(20), nullable=True)
    city = Column(String(100), nullable=True)
    address = Column(Text, nullable=True)
    postal_code = Column(String(20), nullable=True)

    # China marketplace delivery configuration. ``address`` remains the
    # canonical legacy display value; these fields only supplement it.
    name_zh = Column(String(150), nullable=True)
    china_receiver_name = Column(String(100), nullable=True)
    china_mobile = Column(String(50), nullable=True)
    china_province = Column(String(100), nullable=True)
    china_city = Column(String(100), nullable=True)
    china_district = Column(String(100), nullable=True)
    china_street = Column(String(150), nullable=True)
    china_detailed_address = Column(Text, nullable=True)
    china_original_address = Column(Text, nullable=True)
    china_address_status = Column(String(24), nullable=True)
    china_address_source = Column(String(24), nullable=True)

    # NEW - Contact information
    contact_name_1 = Column(String(100), nullable=True)
    contact_phone_1 = Column(String(50), nullable=True)
    contact_name_2 = Column(String(100), nullable=True)
    contact_phone_2 = Column(String(50), nullable=True)

    # NEW - Operating hours
    operating_hours = Column(String(200), nullable=True)
    weekend_hours = Column(String(200), nullable=True)

    # NEW - Coordinates
    latitude = Column(Numeric(10, 8), nullable=True)
    longitude = Column(Numeric(11, 8), nullable=True)

    # NEW - Warehouse type to distinguish between sea cargo, air cargo, or both
    warehouse_type = Column(String(20), nullable=False, default="both")

    # Opaque customer-access token hash. Raw tokens are returned only when a
    # Cargo Admin generates or rotates one and are never persisted.
    automation_access_token_hash = Column(
        String(64), nullable=True, unique=True, index=True
    )
    automation_token_created_at = Column(DateTime, nullable=True)
    automation_token_revoked_at = Column(DateTime, nullable=True)

    admin = relationship("User", back_populates="warehouses")
    containers_origin = relationship(
        "Container",
        foreign_keys="Container.warehouse_origin_id",
        back_populates="origin_warehouse",
    )
    containers_destination = relationship(
        "Container",
        foreign_keys="Container.warehouse_destination_id",
        back_populates="destination_warehouse",
    )


class GoodsCategory(Base):
    """Master goods categories controlled by Super Admin."""

    __tablename__ = "goods_categories"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(150), nullable=False)
    description = Column(Text, nullable=True)
    canonical_key = Column(String(80), nullable=True, unique=True, index=True)
    standard_version = Column(String(20), nullable=True)
    is_standard = Column(Boolean, nullable=False, default=False, server_default="false")
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    goods_types = relationship("GoodsType", back_populates="category")

    __table_args__ = (
        Index(
            "uq_goods_categories_normalized_name",
            text("lower(trim(both from name))"),
            unique=True,
        ),
    )


class GoodsType(Base):
    """
    Specific goods types under a category.
    is_hazardous & requires_special_handling trigger warnings.
    """

    __tablename__ = "goods_types"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    category_id = Column(
        UUID(as_uuid=True), ForeignKey("goods_categories.id"), nullable=True
    )
    name = Column(String(150), nullable=False)
    description = Column(Text, nullable=True)
    canonical_key = Column(String(100), nullable=True, unique=True, index=True)
    hs_reference = Column(String(40), nullable=True, index=True)
    hs_level = Column(String(20), nullable=True)
    hs_version = Column(String(20), nullable=True)
    customs_description = Column(Text, nullable=True)
    is_customs_standard = Column(
        Boolean, nullable=False, default=False, server_default="false", index=True
    )
    is_hazardous = Column(Boolean, default=False)
    requires_special_handling = Column(Boolean, default=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    category = relationship("GoodsCategory", back_populates="goods_types")
    sea_booking_goods = relationship(
        "SeaBookingGoods", back_populates="goods_type"
    )
    batch_goods_types = relationship("BatchGoodsType", back_populates="goods_type")
    express_air_bookings = relationship(
        "ExpressAirCargoBooking", back_populates="cargo_type"
    )
    air_cargo_rates = relationship("AirCargoRate", back_populates="goods_type")
    attribute_templates = relationship(
        "GoodsTypeAttributeTemplate",
        back_populates="goods_type",
        cascade="all, delete-orphan",
        order_by="GoodsTypeAttributeTemplate.sort_order",
    )
    aliases = relationship(
        "GoodsTypeAlias",
        back_populates="goods_type",
        cascade="all, delete-orphan",
        order_by="GoodsTypeAlias.alias",
    )

    __table_args__ = (
        Index(
            "uq_goods_types_normalized_name",
            text("lower(trim(both from name))"),
            unique=True,
        ),
        CheckConstraint(
            "hs_level IS NULL OR hs_level IN ('chapter','heading','subheading','multiple')",
            name="chk_goods_type_hs_level",
        ),
        CheckConstraint(
            "NOT is_customs_standard OR "
            "(canonical_key IS NOT NULL AND hs_reference IS NOT NULL "
            "AND hs_level IS NOT NULL AND hs_version = 'HS 2022')",
            name="chk_goods_type_standard_metadata",
        ),
    )


class GoodsTypeAlias(Base):
    """Hidden synonym mapped to one canonical customs-aligned Goods Type."""

    __tablename__ = "goods_type_aliases"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    goods_type_id = Column(
        UUID(as_uuid=True),
        ForeignKey("goods_types.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    alias = Column(String(150), nullable=False)
    normalized_alias = Column(String(150), nullable=False, unique=True, index=True)
    language = Column(String(8), nullable=False, default="en", server_default="en")
    is_legacy = Column(Boolean, nullable=False, default=False, server_default="false")
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    goods_type = relationship("GoodsType", back_populates="aliases")


class GoodsTypeAttributeTemplate(Base):
    """Admin-managed dynamic product fields for one Goods Type."""

    __tablename__ = "goods_type_attribute_templates"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    goods_type_id = Column(
        UUID(as_uuid=True),
        ForeignKey("goods_types.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    key = Column(String(60), nullable=False)
    label = Column(String(100), nullable=False)
    field_type = Column(String(20), nullable=False, default="text")
    allowed_values = Column(JSONB, nullable=False, default=list, server_default="[]")
    is_required = Column(Boolean, nullable=False, default=False)
    customer_visible = Column(Boolean, nullable=False, default=True)
    is_variant_option = Column(Boolean, nullable=False, default=False)
    sort_order = Column(Integer, nullable=False, default=0)
    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    __table_args__ = (
        CheckConstraint(
            "field_type IN ('text','number','select','multiselect','boolean')",
            name="chk_goods_type_attribute_template_field_type",
        ),
        UniqueConstraint(
            "goods_type_id", "key", name="uq_goods_type_attribute_template_key"
        ),
    )

    goods_type = relationship("GoodsType", back_populates="attribute_templates")


class Container(Base):
    """
    Lifecycle: draft → open → nearly_full → full → in_transit → arrived → completed
    Auto-locks when booked_cbm reaches max_cbm.
    """

    __tablename__ = "containers"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    admin_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    route_id = Column(UUID(as_uuid=True), ForeignKey("routes.id"), nullable=True)
    warehouse_origin_id = Column(
        UUID(as_uuid=True), ForeignKey("warehouses.id"), nullable=True
    )
    warehouse_destination_id = Column(
        UUID(as_uuid=True), ForeignKey("warehouses.id"), nullable=True
    )
    container_size = Column(String(20), nullable=True)  # 20ft | 40ft
    max_cbm = Column(Numeric(10, 2), nullable=False)
    booked_cbm = Column(Numeric(10, 2), default=0)
    price_per_cbm = Column(Numeric(16, 2), nullable=False)
    currency = Column(
        String(3), nullable=True, default="TZS"
    )  # Currency code: TZS, RMB, or USD
    status = Column(String(20), nullable=False, default="draft", index=True)
    departure_date = Column(DateTime, nullable=True)
    estimated_arrival_date = Column(DateTime, nullable=True)
    arrival_date = Column(DateTime, nullable=True)
    is_archived = Column(Boolean, nullable=False, default=False, index=True)
    archived_at = Column(DateTime, nullable=True)
    archived_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        CheckConstraint(
            "status IN ('draft','open','nearly_full','full','in_transit','arrived','completed')",
            name="chk_container_status",
        ),
        CheckConstraint("booked_cbm <= max_cbm", name="chk_cbm_limit"),
        CheckConstraint(
            "currency IN ('TZS', 'RMB', 'USD')", name="chk_container_currency"
        ),
    )

    admin = relationship("User", back_populates="containers", foreign_keys=[admin_id])
    route = relationship("Route", back_populates="containers")
    origin_warehouse = relationship(
        "Warehouse",
        foreign_keys=[warehouse_origin_id],
        back_populates="containers_origin",
    )
    destination_warehouse = relationship(
        "Warehouse",
        foreign_keys=[warehouse_destination_id],
        back_populates="containers_destination",
    )
    sea_bookings = relationship(
        "SeaBooking", back_populates="container", cascade="all, delete-orphan"
    )

    @property
    def fill_percentage(self):
        if self.max_cbm and float(self.max_cbm) > 0:
            return round(float(self.booked_cbm) / float(self.max_cbm) * 100, 2)
        return 0.0

    @property
    def available_cbm(self):
        return float(self.max_cbm) - float(self.booked_cbm)


class SeaBooking(Base):
    """
    A customer or sourcing agent's sea_booking of CBM space in a container.
    Payment is due after arrival. Goods cannot be collected without confirmed payment.
    """

    __tablename__ = "sea_bookings"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    container_id = Column(
        UUID(as_uuid=True),
        ForeignKey("containers.id", ondelete="CASCADE"),
        nullable=False,
    )
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    # Optional for historical sea_bookings. New China-forwarding bookings retain
    # the exact reusable forwarding address selected for the booking.
    customer_china_address_id = Column(
        UUID(as_uuid=True),
        ForeignKey("customer_china_addresses.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    source_type = Column(String(20), nullable=True)  # direct | batch
    source_id = Column(
        UUID(as_uuid=True), nullable=True
    )  # batch_id if source_type=batch
    cbm_booked = Column(Numeric(10, 2), nullable=False)
    logistics_charge = Column(Numeric(18, 2), nullable=False)
    # Immutable commercial currency captured from the container when booked.
    # Nullable only for sea bookings created before this snapshot was introduced.
    currency = Column(String(3), nullable=True)
    payment_status = Column(String(20), default="pending", index=True)
    payment_due_date = Column(DateTime, nullable=True)
    goods_status = Column(String(20), default="ready", index=True)
    hold_reason = Column(Text, nullable=True)
    hold_marked_at = Column(DateTime, nullable=True)
    hold_marked_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    collected_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        CheckConstraint(
            "source_type IN ('direct','batch')", name="chk_sea_booking_source_type"
        ),
        CheckConstraint(
            "payment_status IN ('pending','due','confirmed','overdue')",
            name="chk_payment_status",
        ),
        CheckConstraint(
            "goods_status IN ('ready','held','released','collected')",
            name="chk_goods_status",
        ),
        CheckConstraint(
            "currency IS NULL OR currency IN ('TZS', 'RMB', 'USD')",
            name="chk_sea_booking_currency",
        ),
    )

    container = relationship("Container", back_populates="sea_bookings")
    user = relationship(
        "User", foreign_keys=[user_id], back_populates="sea_bookings"
    )
    hold_by = relationship(
        "User", foreign_keys=[hold_marked_by], overlaps="holds_marked"
    )
    goods_types = relationship(
        "SeaBookingGoods",
        back_populates="sea_booking",
        cascade="all, delete-orphan",
    )
    payments = relationship(
        "Payment", back_populates="sea_booking", cascade="all, delete-orphan"
    )
    shipping_mark = relationship(
        "ShippingMark", back_populates="sea_booking", uselist=False
    )
    customer_china_address = relationship("CustomerChinaAddress")


class SeaBookingGoods(Base):
    """Multi-select goods types for a sea_booking."""

    __tablename__ = "sea_booking_goods"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    sea_booking_id = Column(
        UUID(as_uuid=True),
        ForeignKey("sea_bookings.id", ondelete="CASCADE"),
        nullable=False,
    )
    goods_type_id = Column(
        UUID(as_uuid=True), ForeignKey("goods_types.id"), nullable=False
    )

    sea_booking = relationship("SeaBooking", back_populates="goods_types")
    goods_type = relationship("GoodsType", back_populates="sea_booking_goods")
