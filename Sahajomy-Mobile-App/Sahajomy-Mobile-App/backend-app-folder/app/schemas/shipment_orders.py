from datetime import datetime
from enum import Enum
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator


class ShipmentOrderStatus(str, Enum):
    pending = "pending"
    supplier_contacted = "supplier_contacted"
    confirmed = "confirmed"
    shipped = "shipped"
    received_at_warehouse = "received_at_warehouse"


class ShipmentOrderBase(BaseModel):
    supplier_name: Optional[str] = Field(None, description="Name of the supplier")
    supplier_contact: Optional[str] = Field(
        None, description="Contact information of the supplier"
    )
    supplier_reference: Optional[str] = Field(
        None, description="Reference number from supplier"
    )
    order_description: Optional[str] = Field(
        None, description="Description of the order"
    )
    order_value: Optional[float] = Field(
        None, description="Value of the order in specified currency", ge=0
    )
    currency: Optional[str] = Field(
        "TZS", description="Currency code: TZS, RMB, or USD"
    )
    tracking_number: Optional[str] = Field(
        None, description="Tracking number for the shipment"
    )
    notes: Optional[str] = Field(None, description="Additional notes")
    has_attachments: Optional[bool] = Field(
        False, description="Whether the order has attachments"
    )

    @field_validator("currency")
    @classmethod
    def validate_currency(cls, v):
        if v is not None:
            supported_currencies = {"TZS", "RMB", "USD"}
            if v.upper() not in supported_currencies:
                raise ValueError(f"Currency must be one of {supported_currencies}")
            return v.upper()
        return v


class ShipmentOrderCreate(ShipmentOrderBase):
    status: Optional[ShipmentOrderStatus] = "pending"
    sea_booking_id: Optional[UUID] = None
    air_booking_id: Optional[UUID] = None
    created_by_user_id: Optional[UUID] = Field(
        None, description="ID of the user creating this order"
    )


class ShipmentOrderUpdate(BaseModel):
    supplier_name: Optional[str] = None
    supplier_contact: Optional[str] = None
    supplier_reference: Optional[str] = None
    order_description: Optional[str] = None
    order_value: Optional[float] = None
    currency: Optional[str] = None
    status: Optional[ShipmentOrderStatus] = None
    tracking_number: Optional[str] = None
    notes: Optional[str] = None
    has_attachments: Optional[bool] = None


class ShipmentOrderResponse(ShipmentOrderBase):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    status: ShipmentOrderStatus
    created_by_user_id: UUID
    sea_booking_id: Optional[UUID] = None
    air_booking_id: Optional[UUID] = None
    created_at: datetime
    updated_at: datetime
    display_reference: Optional[str] = None
    reference_id: Optional[str] = None
    customer_display_name: Optional[str] = None
    customer_phone: Optional[str] = None
    cargo_mode: Optional[str] = None
    cargo_type_name: Optional[str] = None
    origin_region: Optional[str] = None
    destination_region: Optional[str] = None
    service_reference: Optional[str] = None
    service_label: Optional[str] = None
    payment_status: Optional[str] = None
    carton_count: Optional[int] = None
    cbm_booked: Optional[float] = None
    shipping_mark_code: Optional[str] = None
    shipping_label_available: Optional[bool] = None
    shipping_label_path: Optional[str] = None
    latest_update: Optional[str] = None
    latest_update_at: Optional[datetime] = None
