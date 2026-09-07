"""
Pydantic schemas for packing list API.
"""

from datetime import datetime
from typing import Dict, List, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class PackingListItemBase(BaseModel):
    """Base schema for packing list items."""

    item_name: str = Field(..., min_length=1, max_length=200)
    item_picture: Optional[str] = None
    price_per_piece: float = Field(..., gt=0)
    item_code: Optional[str] = Field(None, max_length=100)
    cartons: Optional[int] = Field(None, ge=0)
    items_per_carton: Optional[int] = Field(None, ge=1)
    cbm_per_carton: Optional[float] = Field(None, ge=0)
    kilogram_per_carton: Optional[float] = Field(None, ge=0)


class PackingListItemCreate(PackingListItemBase):
    """Schema for creating packing list items."""

    pass


class PackingListItemUpdate(BaseModel):
    """Schema for updating packing list items (all fields optional)."""

    item_name: Optional[str] = Field(None, min_length=1, max_length=200)
    item_picture: Optional[str] = None
    price_per_piece: Optional[float] = Field(None, gt=0)
    item_code: Optional[str] = Field(None, max_length=100)
    cartons: Optional[int] = Field(None, ge=0)
    items_per_carton: Optional[int] = Field(None, ge=1)
    cbm_per_carton: Optional[float] = Field(None, ge=0)
    kilogram_per_carton: Optional[float] = Field(None, ge=0)


class PackingListItemResponse(PackingListItemBase):
    """Response schema for packing list items with calculated fields."""

    id: UUID
    total_quantity: Optional[int] = None
    total_amount: Optional[float] = None
    total_cbm: Optional[float] = None
    total_kilogram: Optional[float] = None
    ordered_by: Optional[str] = None
    order_references: List[str] = []
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class PackingListBase(BaseModel):
    """Base schema for packing lists."""

    name: str = Field(..., min_length=1, max_length=200)
    description: Optional[str] = None


class PackingListCreate(PackingListBase):
    """Schema for creating packing lists."""

    pass


class PackingListResponse(PackingListBase):
    """Response schema for packing lists."""

    id: UUID
    batch_id: UUID
    created_by: UUID
    qr_code_url: Optional[str] = None
    reference: Optional[str] = None
    batch_title: Optional[str] = None
    batch_status: Optional[str] = None
    currency: Optional[str] = None
    agent_details: Optional[Dict[str, Optional[str]]] = None
    created_at: datetime
    updated_at: datetime
    items: List[PackingListItemResponse] = []

    model_config = ConfigDict(from_attributes=True)


class PackingListSummaryResponse(BaseModel):
    """Summary response for packing lists (without items)."""

    id: UUID
    name: str
    batch_id: UUID
    created_at: datetime
    item_count: int
    qr_code_url: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class GeneratePackingListResponse(BaseModel):
    """Response schema for generating packing list from closed batch."""

    success: bool
    packing_list_id: str
    packing_list_name: str
    excel_url: Optional[str] = None
    pdf_url: Optional[str] = None
    items_count: int
    orders_count: int

    model_config = ConfigDict(from_attributes=True)
