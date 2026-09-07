"""Cargo-admin owned customer CRM and customs packing-list records.

These records intentionally complement, rather than replace, ``User``. A
``User`` is an authentication account; a logistics customer can be a company
with many contacts and may not have a Sahajomy login at all.
"""

import uuid
from datetime import datetime

from app.database import Base
from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Column,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import relationship, validates


class CargoCustomer(Base):
    __tablename__ = "cargo_customers"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    cargo_admin_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    linked_user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    customer_reference = Column(String(30), nullable=False, unique=True, index=True)
    customer_type = Column(String(20), nullable=False, default="individual")
    name = Column(String(200), nullable=False, index=True)
    primary_contact_name = Column(String(160), nullable=True)
    phone = Column(String(80), nullable=True, index=True)
    whatsapp = Column(String(80), nullable=True, index=True)
    email = Column(String(255), nullable=True, index=True)
    country = Column(String(120), nullable=True, index=True)
    city = Column(String(120), nullable=True, index=True)
    region = Column(String(120), nullable=True)
    full_address = Column(Text, nullable=True)
    tax_id = Column(String(120), nullable=True, index=True)
    company_registration_number = Column(String(120), nullable=True, index=True)
    preferred_cargo_type = Column(String(10), nullable=True)
    preferred_destination_port = Column(String(160), nullable=True)
    preferred_destination_airport = Column(String(160), nullable=True)
    notes = Column(Text, nullable=True)
    tags = Column(JSONB, nullable=False, default=list, server_default="[]")
    status = Column(String(20), nullable=False, default="active", index=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow, index=True)
    updated_at = Column(
        DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    __table_args__ = (
        CheckConstraint(
            "customer_type IN ('individual','company')", name="chk_cargo_customer_type"
        ),
        CheckConstraint(
            "status IN ('active','inactive')", name="chk_cargo_customer_status"
        ),
        CheckConstraint(
            "preferred_cargo_type IN ('sea','air','both')",
            name="chk_cargo_customer_preferred_cargo",
        ),
    )

    contacts = relationship(
        "CargoCustomerContact", back_populates="customer", cascade="all, delete-orphan"
    )
    addresses = relationship(
        "CargoCustomerAddress", back_populates="customer", cascade="all, delete-orphan"
    )


class CargoCustomerContact(Base):
    __tablename__ = "cargo_customer_contacts"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    customer_id = Column(
        UUID(as_uuid=True),
        ForeignKey("cargo_customers.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    full_name = Column(String(160), nullable=False)
    role = Column(String(100), nullable=True)
    phone = Column(String(80), nullable=True)
    whatsapp = Column(String(80), nullable=True)
    email = Column(String(255), nullable=True)
    notes = Column(Text, nullable=True)
    is_primary = Column(Boolean, nullable=False, default=False)
    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(
        DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    customer = relationship("CargoCustomer", back_populates="contacts")


class CargoCustomerAddress(Base):
    __tablename__ = "cargo_customer_addresses"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    customer_id = Column(
        UUID(as_uuid=True),
        ForeignKey("cargo_customers.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    label = Column(String(100), nullable=False, default="Address")
    contact_person = Column(String(160), nullable=True)
    phone = Column(String(80), nullable=True)
    country = Column(String(120), nullable=True)
    city = Column(String(120), nullable=True)
    region = Column(String(120), nullable=True)
    full_address = Column(Text, nullable=True)
    postal_code = Column(String(40), nullable=True)
    notes = Column(Text, nullable=True)
    is_default_shipping = Column(Boolean, nullable=False, default=False)
    is_default_billing = Column(Boolean, nullable=False, default=False)
    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(
        DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    customer = relationship("CargoCustomer", back_populates="addresses")


class ManualCargoIntake(Base):
    """Warehouse-received goods that did not originate from a customer booking."""

    __tablename__ = "manual_cargo_intakes"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    cargo_admin_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    intake_number = Column(String(40), nullable=False, unique=True, index=True)
    tracking_number = Column(String(100), nullable=False, unique=True, index=True)
    external_tracking_number = Column(String(100), nullable=True, index=True)
    customer_id = Column(
        UUID(as_uuid=True),
        ForeignKey("cargo_customers.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    warehouse_id = Column(
        UUID(as_uuid=True),
        ForeignKey("warehouses.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    container_id = Column(
        UUID(as_uuid=True),
        ForeignKey("containers.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    sea_booking_id = Column(
        UUID(as_uuid=True),
        ForeignKey("sea_bookings.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    air_booking_id = Column(
        UUID(as_uuid=True),
        ForeignKey("express_air_cargo_bookings.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    cargo_type = Column(String(10), nullable=False)
    destination_country = Column(String(120), nullable=True)
    destination_city = Column(String(120), nullable=True)
    consignee_address = Column(Text, nullable=True)
    supplier_name = Column(String(200), nullable=True)
    supplier_contact = Column(String(160), nullable=True)
    received_at = Column(DateTime, nullable=False, default=datetime.utcnow, index=True)
    received_by = Column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    charge_basis = Column(String(20), nullable=False)
    rate_amount = Column(Numeric(20, 4), nullable=False, default=0)
    rate_currency = Column(String(3), nullable=False, default="USD")
    calculated_billable_quantity = Column(Numeric(16, 6), nullable=False, default=0)
    calculated_shipping_charge = Column(Numeric(20, 4), nullable=False, default=0)
    total_cartons = Column(Integer, nullable=False, default=0)
    total_quantity = Column(Numeric(16, 3), nullable=False, default=0)
    total_cbm = Column(Numeric(16, 6), nullable=False, default=0)
    total_gross_weight_kg = Column(Numeric(16, 3), nullable=False, default=0)
    total_volumetric_weight_kg = Column(Numeric(16, 3), nullable=True)
    chargeable_weight_kg = Column(Numeric(16, 3), nullable=True)
    status = Column(String(30), nullable=False, default="draft", index=True)
    # Automation augments the same receipt record; it does not create a second
    # cargo/parcel system. These fields are deliberately independent of the
    # existing document lifecycle in ``status``.
    intake_method = Column(
        String(24), nullable=False, default="manual", server_default="manual"
    )
    carrier = Column(String(120), nullable=True)
    shipping_mark = Column(String(100), nullable=True, index=True)
    payment_status = Column(
        String(16),
        nullable=False,
        default="unpaid",
        server_default="unpaid",
        index=True,
    )
    collection_status = Column(
        String(24),
        nullable=False,
        default="not_ready",
        server_default="not_ready",
        index=True,
    )
    intake_confirmed_by = Column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    collected_by = Column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    collected_at = Column(DateTime, nullable=True)
    extraction_metadata = Column(
        JSONB, nullable=False, default=dict, server_default="{}"
    )
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow, index=True)
    updated_at = Column(
        DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    __table_args__ = (
        CheckConstraint(
            "cargo_type IN ('sea','air')", name="chk_manual_intake_cargo_type"
        ),
        CheckConstraint(
            "charge_basis IN ('cbm','metric_ton','flat','custom','kg')",
            name="chk_manual_intake_charge_basis",
        ),
        CheckConstraint(
            "rate_currency IN ('TZS','RMB','USD')", name="chk_manual_intake_currency"
        ),
        CheckConstraint(
            "status IN ('draft','received','ready_for_packing_list','finalized','cancelled')",
            name="chk_manual_intake_status",
        ),
        CheckConstraint(
            "intake_method IN ('manual','scan','barcode','assisted_scan')",
            name="chk_manual_intake_method",
        ),
        CheckConstraint(
            "payment_status IN ('unpaid','paid')",
            name="chk_manual_intake_payment_status",
        ),
        CheckConstraint(
            "collection_status IN ('not_ready','ready','collected')",
            name="chk_manual_intake_collection_status",
        ),
    )

    customer = relationship("CargoCustomer", foreign_keys=[customer_id])
    warehouse = relationship("Warehouse", foreign_keys=[warehouse_id])
    container = relationship("Container", foreign_keys=[container_id])
    sea_booking = relationship("SeaBooking", foreign_keys=[sea_booking_id])
    air_booking = relationship("ExpressAirCargoBooking", foreign_keys=[air_booking_id])
    items = relationship(
        "ManualCargoIntakeItem",
        back_populates="intake",
        cascade="all, delete-orphan",
        order_by="ManualCargoIntakeItem.sort_order",
    )
    customs_packing_lists = relationship(
        "CustomsPackingList",
        back_populates="manual_intake",
        foreign_keys="CustomsPackingList.manual_intake_id",
    )

    @validates("tracking_number")
    def keep_platform_tracking_number_immutable(self, key, value):
        current = self.__dict__.get(key)
        if current and value != current:
            raise ValueError("A Sahajomy tracking number cannot be changed")
        return value


class ManualCargoIntakeItem(Base):
    __tablename__ = "manual_cargo_intake_items"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    intake_id = Column(
        UUID(as_uuid=True),
        ForeignKey("manual_cargo_intakes.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    sort_order = Column(Integer, nullable=False, default=0)
    item_name = Column(String(200), nullable=False)
    item_description = Column(String(500), nullable=False)
    item_photo_url = Column(Text, nullable=True)
    carton_count = Column(Integer, nullable=False, default=1)
    qty_per_carton = Column(Numeric(16, 3), nullable=False, default=0)
    total_quantity = Column(Numeric(16, 3), nullable=False, default=0)
    length_cm = Column(Numeric(16, 3), nullable=False, default=0)
    width_cm = Column(Numeric(16, 3), nullable=False, default=0)
    height_cm = Column(Numeric(16, 3), nullable=False, default=0)
    cbm_source = Column(
        String(20), nullable=False, default="dimensions", server_default="dimensions"
    )
    cbm_per_carton = Column(Numeric(16, 9), nullable=False, default=0)
    total_cbm = Column(Numeric(16, 6), nullable=False, default=0)
    gross_weight_per_carton_kg = Column(Numeric(16, 3), nullable=True)
    total_gross_weight_kg = Column(Numeric(16, 3), nullable=False, default=0)
    volumetric_weight_per_carton_kg = Column(Numeric(16, 3), nullable=True)
    total_volumetric_weight_kg = Column(Numeric(16, 3), nullable=True)
    charge_basis = Column(
        String(20), nullable=False, default="cbm", server_default="cbm"
    )
    rate_amount = Column(Numeric(20, 4), nullable=False, default=0, server_default="0")
    rate_currency = Column(
        String(3), nullable=False, default="USD", server_default="USD"
    )
    calculated_billable_quantity = Column(
        Numeric(16, 6), nullable=False, default=0, server_default="0"
    )
    calculated_shipping_charge = Column(
        Numeric(20, 4), nullable=False, default=0, server_default="0"
    )
    hs_code = Column(String(80), nullable=True)
    brand = Column(String(120), nullable=True)
    model = Column(String(120), nullable=True)
    country_of_origin = Column(String(120), nullable=True)
    sku = Column(String(120), nullable=True)
    remarks = Column(Text, nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(
        DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    __table_args__ = (
        CheckConstraint("carton_count > 0", name="chk_manual_intake_item_cartons"),
        CheckConstraint("qty_per_carton >= 0", name="chk_manual_intake_item_qty"),
        CheckConstraint(
            "charge_basis IN ('cbm','metric_ton','flat','custom','kg')",
            name="chk_manual_intake_item_charge_basis",
        ),
        CheckConstraint(
            "rate_currency IN ('TZS','RMB','USD')",
            name="chk_manual_intake_item_currency",
        ),
    )

    intake = relationship("ManualCargoIntake", back_populates="items")


class CustomsPackingList(Base):
    __tablename__ = "customs_packing_lists"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    cargo_admin_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    packing_list_number = Column(String(40), nullable=False, unique=True, index=True)
    customer_id = Column(
        UUID(as_uuid=True),
        ForeignKey("cargo_customers.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    consignee_customer_id = Column(
        UUID(as_uuid=True),
        ForeignKey("cargo_customers.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    warehouse_id = Column(
        UUID(as_uuid=True),
        ForeignKey("warehouses.id", ondelete="SET NULL"),
        nullable=True,
    )
    container_id = Column(
        UUID(as_uuid=True),
        ForeignKey("containers.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    sea_booking_id = Column(
        UUID(as_uuid=True),
        ForeignKey("sea_bookings.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    air_booking_id = Column(
        UUID(as_uuid=True),
        ForeignKey("express_air_cargo_bookings.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    manual_intake_id = Column(
        UUID(as_uuid=True),
        ForeignKey("manual_cargo_intakes.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    source_type = Column(String(30), nullable=False, default="manual", index=True)
    cargo_type = Column(String(10), nullable=False)
    status = Column(String(20), nullable=False, default="draft", index=True)
    issue_date = Column(Date, nullable=False, default=datetime.utcnow)
    origin_address = Column(JSONB, nullable=False, default=dict, server_default="{}")
    shipper_snapshot = Column(JSONB, nullable=False, default=dict, server_default="{}")
    consignee_snapshot = Column(
        JSONB, nullable=False, default=dict, server_default="{}"
    )
    notify_party = Column(JSONB, nullable=False, default=dict, server_default="{}")
    shipment_references = Column(
        JSONB, nullable=False, default=dict, server_default="{}"
    )
    optional_columns = Column(JSONB, nullable=False, default=list, server_default="[]")
    custom_columns = Column(JSONB, nullable=False, default=list, server_default="[]")
    notes = Column(Text, nullable=True)
    total_cartons = Column(Integer, nullable=False, default=0)
    total_quantity = Column(Numeric(16, 3), nullable=False, default=0)
    total_cbm = Column(Numeric(16, 6), nullable=False, default=0)
    total_gross_weight_kg = Column(Numeric(16, 3), nullable=False, default=0)
    total_net_weight_kg = Column(Numeric(16, 3), nullable=True)
    total_volumetric_weight_kg = Column(Numeric(16, 3), nullable=True)
    chargeable_weight_kg = Column(Numeric(16, 3), nullable=True)
    snapshot = Column(JSONB, nullable=True)
    finalized_at = Column(DateTime, nullable=True)
    cancelled_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow, index=True)
    updated_at = Column(
        DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    __table_args__ = (
        CheckConstraint(
            "cargo_type IN ('sea','air')", name="chk_customs_packing_cargo_type"
        ),
        CheckConstraint(
            "status IN ('draft','finalized','cancelled')",
            name="chk_customs_packing_status",
        ),
    )

    customer = relationship("CargoCustomer", foreign_keys=[customer_id])
    consignee_customer = relationship(
        "CargoCustomer", foreign_keys=[consignee_customer_id]
    )
    warehouse = relationship("Warehouse", foreign_keys=[warehouse_id])
    container = relationship("Container", foreign_keys=[container_id])
    sea_booking = relationship("SeaBooking", foreign_keys=[sea_booking_id])
    air_booking = relationship("ExpressAirCargoBooking", foreign_keys=[air_booking_id])
    manual_intake = relationship(
        "ManualCargoIntake",
        back_populates="customs_packing_lists",
        foreign_keys=[manual_intake_id],
    )
    items = relationship(
        "CustomsPackingListItem",
        back_populates="packing_list",
        cascade="all, delete-orphan",
        order_by="CustomsPackingListItem.sort_order",
    )


class CustomsPackingListItem(Base):
    __tablename__ = "customs_packing_list_items"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    packing_list_id = Column(
        UUID(as_uuid=True),
        ForeignKey("customs_packing_lists.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    sort_order = Column(Integer, nullable=False, default=0)
    item_name = Column(String(200), nullable=False)
    item_description = Column(String(500), nullable=False)
    # Every printable customs row has a photo value. The API substitutes the
    # documented fallback thumbnail whenever its source did not provide one.
    item_photo_url = Column(
        Text,
        nullable=False,
        default="fallback://packing-item-photo",
        server_default="fallback://packing-item-photo",
    )
    carton_count = Column(Integer, nullable=False, default=0)
    qty_per_carton = Column(Numeric(16, 3), nullable=False, default=0)
    total_quantity = Column(Numeric(16, 3), nullable=False, default=0)
    length_cm = Column(Numeric(16, 3), nullable=False, default=0)
    width_cm = Column(Numeric(16, 3), nullable=False, default=0)
    height_cm = Column(Numeric(16, 3), nullable=False, default=0)
    cbm_source = Column(
        String(20), nullable=False, default="dimensions", server_default="dimensions"
    )
    cbm_per_carton = Column(Numeric(16, 9), nullable=False, default=0)
    total_cbm = Column(Numeric(16, 6), nullable=False, default=0)
    gross_weight_per_carton_kg = Column(Numeric(16, 3), nullable=False, default=0)
    total_gross_weight_kg = Column(Numeric(16, 3), nullable=False, default=0)
    net_weight_per_carton_kg = Column(Numeric(16, 3), nullable=True)
    total_net_weight_kg = Column(Numeric(16, 3), nullable=True)
    volumetric_weight_per_carton_kg = Column(Numeric(16, 3), nullable=True)
    total_volumetric_weight_kg = Column(Numeric(16, 3), nullable=True)
    remarks = Column(Text, nullable=True)
    optional_values = Column(JSONB, nullable=False, default=dict, server_default="{}")
    custom_values = Column(JSONB, nullable=False, default=dict, server_default="{}")
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(
        DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    __table_args__ = (
        CheckConstraint("carton_count > 0", name="chk_customs_packing_item_cartons"),
        CheckConstraint("qty_per_carton >= 0", name="chk_customs_packing_item_qty"),
        CheckConstraint(
            "length_cm >= 0 AND width_cm >= 0 AND height_cm >= 0",
            name="chk_customs_packing_item_dimensions",
        ),
        CheckConstraint(
            "gross_weight_per_carton_kg >= 0",
            name="chk_customs_packing_item_gross_weight",
        ),
    )

    packing_list = relationship("CustomsPackingList", back_populates="items")
