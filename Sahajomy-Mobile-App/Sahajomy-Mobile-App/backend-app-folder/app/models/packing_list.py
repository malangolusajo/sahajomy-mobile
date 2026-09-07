"""
Packing List Models for Sourcing Batches.
Each packing list belongs to a sourcing batch and contains multiple items.
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
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship


class PackingList(Base):
    """
    Represents a packing list for a sourcing batch.
    Created by sourcing agents to organize and track items in a batch.
    """

    __tablename__ = "packing_lists"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    batch_id = Column(
        UUID(as_uuid=True),
        ForeignKey("sourcing_batches.id", ondelete="CASCADE"),
        nullable=False,
    )
    created_by = Column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    name = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)
    qr_code_url = Column(String(500), nullable=True)  # URL to QR code image
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    batch = relationship("SourcingBatch", back_populates="packing_lists")
    created_by_user = relationship("User", foreign_keys=[created_by])
    items = relationship(
        "PackingListItem", back_populates="packing_list", cascade="all, delete-orphan"
    )


class PackingListItem(Base):
    """
    Individual item in a packing list with automatic calculations.
    Contains required and optional fields as specified in requirements.
    """

    __tablename__ = "packing_list_items"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    packing_list_id = Column(
        UUID(as_uuid=True),
        ForeignKey("packing_lists.id", ondelete="CASCADE"),
        nullable=False,
    )

    # Required fields (must always exist)
    item_name = Column(String(200), nullable=False)
    item_picture = Column(String(500), nullable=True)  # URL to image
    price_per_piece = Column(Numeric(20, 2), nullable=False)

    # Optional fields (can be filled by sourcing agent)
    item_code = Column(String(100), nullable=True)
    cartons = Column(Integer, nullable=True)
    items_per_carton = Column(Integer, nullable=True)
    cbm_per_carton = Column(Numeric(10, 4), nullable=True)
    kilogram_per_carton = Column(Numeric(10, 2), nullable=True)

    # Auto-calculated fields (will be computed by service layer)
    total_quantity = Column(Integer, nullable=True)
    total_amount = Column(Numeric(20, 2), nullable=True)
    total_cbm = Column(Numeric(10, 4), nullable=True)
    total_kilogram = Column(Numeric(10, 2), nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    packing_list = relationship("PackingList", back_populates="items")

    def calculate_totals(self):
        """Calculate auto-generated fields based on available data."""
        # total_quantity = cartons × items_per_carton
        if self.cartons is not None and self.items_per_carton is not None:
            self.total_quantity = self.cartons * self.items_per_carton
        else:
            self.total_quantity = None

        # total_amount = total_quantity × price_per_piece
        if self.total_quantity is not None and self.price_per_piece is not None:
            self.total_amount = float(self.total_quantity) * float(self.price_per_piece)
        else:
            self.total_amount = None

        # total_cbm = cartons × cbm_per_carton
        if self.cartons is not None and self.cbm_per_carton is not None:
            self.total_cbm = float(self.cartons) * float(self.cbm_per_carton)
        else:
            self.total_cbm = None

        # total_kilogram = cartons × kilogram_per_carton
        if self.cartons is not None and self.kilogram_per_carton is not None:
            self.total_kilogram = float(self.cartons) * float(self.kilogram_per_carton)
        else:
            self.total_kilogram = None
