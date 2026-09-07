"""
Models: Payment, CommissionSettings, Receipt, ReceiptScan, Notification, AuditLog
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
    Integer,
    Numeric,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import relationship


class Payment(Base):
    """
    Payment for sea booking logistics charge.
    Due after container arrival. Goods cannot be collected without confirmed payment.
    """

    __tablename__ = "payments"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    sea_booking_id = Column(
        UUID(as_uuid=True), ForeignKey("sea_bookings.id"), nullable=False
    )
    amount = Column(Numeric(20, 2), nullable=False)
    # Financial snapshot copied from the sea_booking at payment creation.
    currency = Column(String(3), nullable=True)
    method = Column(String(50), nullable=True)  # mobile_money | bank_transfer | card
    transaction_reference = Column(String(150), nullable=True)
    status = Column(String(20), nullable=False, default="pending")
    paid_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        CheckConstraint(
            "status IN ('pending','confirmed','failed')", name="chk_payment_status"
        ),
        CheckConstraint(
            "currency IS NULL OR currency IN ('TZS', 'RMB', 'USD')",
            name="chk_payment_currency",
        ),
    )

    sea_booking = relationship("SeaBooking", back_populates="payments")


class CommissionSettings(Base):
    """Platform-wide commission rate, set by Super Admin only. Default 1%."""

    __tablename__ = "commission_settings"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    commission_percentage = Column(Numeric(5, 2), default=1.00, nullable=False)
    effective_from = Column(DateTime, default=datetime.utcnow)


class Receipt(Base):
    """Generated automatically on collection confirmation. Contains QR token."""

    __tablename__ = "receipts"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    order_id = Column(
        UUID(as_uuid=True), ForeignKey("sourcing_orders.id"), nullable=True
    )
    sea_booking_id = Column(
        UUID(as_uuid=True), ForeignKey("sea_bookings.id"), nullable=True
    )
    receipt_number = Column(String(50), unique=True, nullable=False)
    receipt_token = Column(String(120), unique=True, nullable=False)
    amount = Column(Numeric(20, 2), nullable=True)
    # A receipt must never be reinterpreted using a container's later currency.
    currency = Column(String(3), nullable=True)
    pdf_url = Column(Text, nullable=True)
    status = Column(String(20), nullable=False, default="issued")
    issued_by = Column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    voided_at = Column(DateTime, nullable=True)
    voided_by = Column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    notes = Column(Text, nullable=True)
    generated_at = Column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        CheckConstraint("status IN ('issued','voided')", name="chk_receipt_status"),
        CheckConstraint(
            "currency IS NULL OR currency IN ('TZS', 'RMB', 'USD')",
            name="chk_receipt_currency",
        ),
    )

    order = relationship("SourcingOrder", back_populates="receipt")
    scans = relationship(
        "ReceiptScan", back_populates="receipt", cascade="all, delete-orphan"
    )


class SeaBookingInvoice(Base):
    """Persistent invoice lifecycle for sea bookings."""

    __tablename__ = "sea_booking_invoices"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    sea_booking_id = Column(
        UUID(as_uuid=True),
        ForeignKey("sea_bookings.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    container_id = Column(
        UUID(as_uuid=True),
        ForeignKey("containers.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    customer_id = Column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    created_by = Column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    invoice_number = Column(String(60), unique=True, nullable=False, index=True)
    amount = Column(Numeric(20, 2), nullable=False)
    currency = Column(String(3), nullable=False, default="TZS")
    status = Column(String(20), nullable=False, default="draft", index=True)
    notes = Column(Text, nullable=True)
    sent_at = Column(DateTime, nullable=True)
    paid_at = Column(DateTime, nullable=True)
    cancelled_at = Column(DateTime, nullable=True)
    excel_url = Column(Text, nullable=True)
    pdf_url = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    updated_at = Column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False,
    )

    __table_args__ = (
        CheckConstraint(
            "status IN ('draft','sent','paid','cancelled')",
            name="chk_sea_booking_invoice_status",
        ),
        CheckConstraint(
            "currency IN ('TZS', 'RMB', 'USD')",
            name="chk_sea_booking_invoice_currency",
        ),
    )


class SeaBookingPackingList(Base):
    """Cargo-admin packing workflow for a sea booking."""

    __tablename__ = "sea_booking_packing_lists"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    sea_booking_id = Column(
        UUID(as_uuid=True),
        ForeignKey("sea_bookings.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    container_id = Column(
        UUID(as_uuid=True),
        ForeignKey("containers.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    customer_id = Column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    created_by = Column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    status = Column(String(20), nullable=False, default="draft", index=True)
    shipment_stage = Column(
        String(40), nullable=False, default="booking_received", index=True
    )
    notes = Column(Text, nullable=True)
    total_cartons = Column(Integer, nullable=False, default=0)
    total_cbm = Column(Numeric(12, 3), nullable=False, default=0)
    total_weight_kg = Column(Numeric(12, 3), nullable=False, default=0)
    received_cbm = Column(Numeric(12, 3), nullable=False, default=0)
    loaded_cbm = Column(Numeric(12, 3), nullable=False, default=0)
    confirmed_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    updated_at = Column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False,
    )

    __table_args__ = (
        CheckConstraint(
            "status IN ('draft','in_progress','finalized')",
            name="chk_sea_booking_packing_list_status",
        ),
    )

    sea_booking = relationship(
        "SeaBooking",
        foreign_keys=[sea_booking_id],
    )
    container = relationship(
        "Container",
        foreign_keys=[container_id],
    )
    customer = relationship(
        "User",
        foreign_keys=[customer_id],
    )
    created_by_user = relationship(
        "User",
        foreign_keys=[created_by],
    )
    items = relationship(
        "SeaBookingPackingListItem",
        back_populates="packing_list",
        cascade="all, delete-orphan",
    )


class SeaBookingPackingListItem(Base):
    """Item-level progress inside cargo-admin sea booking packing list."""

    __tablename__ = "sea_booking_packing_list_items"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    packing_list_id = Column(
        UUID(as_uuid=True),
        ForeignKey("sea_booking_packing_lists.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    sea_booking_goods_id = Column(
        UUID(as_uuid=True),
        ForeignKey("sea_booking_goods.id", ondelete="SET NULL"),
        nullable=True,
    )
    item_name = Column(String(200), nullable=False)
    supplier_details = Column(String(255), nullable=True)
    cartons = Column(Integer, nullable=False, default=0)
    cbm = Column(Numeric(12, 3), nullable=False, default=0)
    weight_kg = Column(Numeric(12, 3), nullable=False, default=0)
    status = Column(String(20), nullable=False, default="pending", index=True)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    updated_at = Column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False,
    )

    __table_args__ = (
        CheckConstraint(
            (
                "status IN "
                "('pending','received','inspected','packed','loaded','completed')"
            ),
            name="chk_sea_booking_packing_item_status",
        ),
        CheckConstraint("cartons >= 0", name="chk_sea_booking_packing_item_cartons"),
        CheckConstraint("cbm >= 0", name="chk_sea_booking_packing_item_cbm"),
        CheckConstraint("weight_kg >= 0", name="chk_sea_booking_packing_item_weight"),
    )

    packing_list = relationship(
        "SeaBookingPackingList",
        back_populates="items",
    )
    sea_booking_goods = relationship(
        "SeaBookingGoods",
        foreign_keys=[sea_booking_goods_id],
    )


class ContainerConsolidatedPackingList(Base):
    """Persisted PDF generated for a complete cargo container."""

    __tablename__ = "container_consolidated_packing_lists"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    container_id = Column(
        UUID(as_uuid=True),
        ForeignKey("containers.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    # Container references are derived from UUIDs today. Store the displayed
    # reference at generation time so the document history remains meaningful.
    container_reference = Column(String(80), nullable=False)
    generated_by = Column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    document_url = Column(Text, nullable=False)
    status = Column(String(20), nullable=False, default="generated", index=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    updated_at = Column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False,
    )

    __table_args__ = (
        CheckConstraint(
            "status IN ('generated','superseded')",
            name="chk_container_consolidated_packing_list_status",
        ),
    )

    container = relationship("Container", foreign_keys=[container_id])
    generated_by_user = relationship("User", foreign_keys=[generated_by])


class ReceiptScan(Base):
    """Audit trail for every QR scan of a receipt."""

    __tablename__ = "receipt_scans"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    receipt_id = Column(UUID(as_uuid=True), ForeignKey("receipts.id"), nullable=False)
    scanned_at = Column(DateTime, default=datetime.utcnow)
    ip_address = Column(String(100), nullable=True)

    receipt = relationship("Receipt", back_populates="scans")


class Notification(Base):
    __tablename__ = "notifications"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    type = Column(String(50), nullable=True)
    message = Column(Text, nullable=False)
    is_read = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="notifications")

    # NEW: Add priority column to Notification model if not already present
    priority = Column(
        String(20), default="info", nullable=True
    )  # info, warning, critical
    target_type = Column(String(30), nullable=True, index=True)
    target_id = Column(UUID(as_uuid=True), nullable=True, index=True)


class AuditLog(Base):
    """
    Immutable audit trail.
    Required for: hold actions, collection confirmations, admin overrides, role changes.
    """

    __tablename__ = "audit_logs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    action = Column(String(150), nullable=False)
    entity_type = Column(String(50), nullable=True)
    entity_id = Column(UUID(as_uuid=True), nullable=True)
    extra_data = Column(JSONB, nullable=True)
    reason = Column(Text, nullable=True)  # required for admin overrides
    created_at = Column(DateTime, default=datetime.utcnow, index=True)

    user = relationship("User", back_populates="audit_logs")
