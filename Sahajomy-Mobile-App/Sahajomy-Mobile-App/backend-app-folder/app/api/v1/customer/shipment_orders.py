import json
import os
import tempfile
from typing import List, Optional
from uuid import UUID

from app.core.cloudinary import upload_to_cloudinary
from app.core.config import settings
from app.core.dependencies import get_customer  # Correct import for customer auth
from app.core.upload_validation import validated_image_format
from app.database import get_db
from app.models.shipment_orders import ShipmentOrder, ShipmentOrderStatus
from app.models.user import User
from app.schemas.shipment_orders import (
    ShipmentOrderCreate,
    ShipmentOrderResponse,
    ShipmentOrderUpdate,
)
from app.services.shipment_orders_service import (
    create_shipment_order,
    delete_shipment_order,
    get_shipment_order,
    get_shipment_orders_by_air_booking,
    get_shipment_orders_by_sea_booking,
    get_shipment_orders_by_user,
    update_shipment_order,
)
from app.services.tracking import TrackingService
from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from sqlalchemy.orm import Session

# Rename the dependency to match what's used in the file
get_current_customer_user = get_customer

router = APIRouter()


@router.post("/", response_model=ShipmentOrderResponse)
def create_new_shipment_order(
    shipment_order: ShipmentOrderCreate,
    current_user: User = Depends(get_current_customer_user),
    db: Session = Depends(get_db),
):
    # Ensure the shipment order is created by the current user
    shipment_order.created_by_user_id = current_user.id
    created_order = create_shipment_order(db, shipment_order)

    # Create tracking event for shipment order creation
    TrackingService.create_tracking_event(
        db=db,
        entity_type="shipment_order",
        entity_id=str(created_order.id),
        event_type="shipment_order_created",
        description=f"Shipment order created for {created_order.order_description or 'order'}",
        triggered_by=str(current_user.id),
        extra_data={
            "status": created_order.status,
            "supplier_name": created_order.supplier_name,
            "order_value": (
                str(created_order.order_value) if created_order.order_value else None
            ),
            "currency": created_order.currency,
            "has_container": bool(created_order.sea_booking_id),
            "has_air_booking": bool(created_order.air_booking_id),
        },
    )
    db.commit()
    db.refresh(created_order)

    return created_order


@router.post("/with-photos", response_model=ShipmentOrderResponse)
async def create_shipment_order_with_photos(
    supplier_name: Optional[str] = Form(None),
    supplier_email: Optional[str] = Form(None),
    supplier_phone: Optional[str] = Form(None),
    order_description: Optional[str] = Form(None),
    order_value: Optional[str] = Form(None),
    tracking_number: Optional[str] = Form(None),
    notes: Optional[str] = Form(None),
    order_status: Optional[str] = Form("pending", alias="status"),
    sea_booking_id: Optional[str] = Form(None),
    air_booking_id: Optional[str] = Form(None),
    item_photos: Optional[str] = Form("[]"),
    photos: List[UploadFile] = File([]),
    current_user: User = Depends(get_current_customer_user),
    db: Session = Depends(get_db),
):
    """Create a new shipment order with photo uploads"""
    # Handle photo uploads
    photo_urls = []

    # Add existing photo URLs from form
    try:
        existing_photos = json.loads(item_photos or "[]")
        if isinstance(existing_photos, list):
            photo_urls.extend(existing_photos)
    except (json.JSONDecodeError, TypeError):
        pass

    # Upload new photos to the existing Cloudinary-backed media store.
    for photo in photos:
        if photo and photo.filename:
            if photo.content_type not in set(settings.ALLOWED_IMAGE_TYPES) | {
                "image/gif"
            }:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Invalid file type. Only JPEG, PNG, GIF, and WebP images are allowed.",
                )

            content = await photo.read()
            if len(content) > settings.MAX_IMAGE_SIZE_MB * 1024 * 1024:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"File too large. Maximum file size is {settings.MAX_IMAGE_SIZE_MB}MB.",
                )

            _, file_extension = validated_image_format(
                content, photo.content_type, allow_gif=True
            )
            with tempfile.NamedTemporaryFile(
                delete=False, suffix=f".{file_extension}"
            ) as tmp:
                tmp.write(content)
                tmp_path = tmp.name

            try:
                uploaded_url = upload_to_cloudinary(
                    file=tmp_path,
                    folder=f"shipment_orders/{current_user.id}",
                    resource_type="image",
                    tags=["shipment_order_attachment"],
                    context={"uploaded_by": str(current_user.id)},
                )
                photo_urls.append(uploaded_url)
            except Exception as e:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Failed to upload photo: {str(e)}",
                )
            finally:
                if os.path.exists(tmp_path):
                    os.unlink(tmp_path)

    # Parse UUIDs
    container_uuid = UUID(sea_booking_id) if sea_booking_id else None
    air_booking_uuid = UUID(air_booking_id) if air_booking_id else None

    # If an auto-created shipment order already exists for this booking/sea_booking,
    # enrich it instead of creating a duplicate.
    existing_order = None
    if container_uuid:
        existing_order = (
            db.query(ShipmentOrder)
            .filter(
                ShipmentOrder.created_by_user_id == current_user.id,
                ShipmentOrder.sea_booking_id == container_uuid,
            )
            .order_by(ShipmentOrder.created_at.desc())
            .first()
        )
    elif air_booking_uuid:
        existing_order = (
            db.query(ShipmentOrder)
            .filter(
                ShipmentOrder.created_by_user_id == current_user.id,
                ShipmentOrder.air_booking_id == air_booking_uuid,
            )
            .order_by(ShipmentOrder.created_at.desc())
            .first()
        )

    if existing_order:
        previous_status = existing_order.status
        had_details = any(
            [
                existing_order.supplier_name,
                existing_order.order_description,
                existing_order.order_value,
                existing_order.tracking_number,
                existing_order.notes,
                existing_order.has_attachments,
            ]
        )
        if order_status:
            try:
                order_status = ShipmentOrderStatus(order_status).value
            except ValueError:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Invalid status. Valid statuses are: {[s.value for s in ShipmentOrderStatus]}",
                )

        if supplier_name is not None:
            existing_order.supplier_name = supplier_name
        if order_description is not None:
            existing_order.order_description = order_description
        if order_value not in (None, ""):
            try:
                existing_order.order_value = float(order_value)
            except ValueError:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="order_value must be a valid number",
                )
        if tracking_number is not None:
            existing_order.tracking_number = tracking_number
        if notes is not None:
            existing_order.notes = notes
        if order_status:
            existing_order.status = order_status
        if photo_urls:
            existing_order.has_attachments = True

        event_type = (
            "shipment_information_updated"
            if had_details
            else "shipment_details_uploaded"
        )
        TrackingService.create_tracking_event(
            db=db,
            entity_type="shipment_order",
            entity_id=str(existing_order.id),
            event_type=event_type,
            description=f"Shipment details updated for {existing_order.order_description or 'order'}",
            triggered_by=str(current_user.id),
            extra_data={
                "old_status": str(previous_status),
                "new_status": str(existing_order.status),
                "order_description": existing_order.order_description or "order",
                "photo_count": len(photo_urls),
                "has_container": bool(existing_order.sea_booking_id),
                "has_air_booking": bool(existing_order.air_booking_id),
            },
        )
        db.commit()
        db.refresh(existing_order)
        return existing_order

    # Create shipment order
    shipment_order_data = {
        "supplier_name": supplier_name,
        "supplier_email": supplier_email,
        "supplier_phone": supplier_phone,
        "order_description": order_description,
        "order_value": order_value,
        "tracking_number": tracking_number,
        "notes": notes,
        "status": order_status,
        "sea_booking_id": container_uuid,
        "air_booking_id": air_booking_uuid,
        "created_by_user_id": current_user.id,
        "photo_urls": json.dumps(photo_urls) if photo_urls else None,
    }

    shipment_order = ShipmentOrderCreate(**shipment_order_data)
    created_order = create_shipment_order(db, shipment_order)

    # Create tracking event for shipment order creation
    TrackingService.create_tracking_event(
        db=db,
        entity_type="shipment_order",
        entity_id=str(created_order.id),
        event_type="shipment_order_created",
        description=f"Shipment order created with {len(photo_urls)} photos for {created_order.order_description or 'order'}",
        triggered_by=str(current_user.id),
        extra_data={
            "status": created_order.status,
            "supplier_name": created_order.supplier_name,
            "order_value": (
                str(created_order.order_value) if created_order.order_value else None
            ),
            "currency": created_order.currency,
            "photo_count": len(photo_urls),
            "has_container": bool(created_order.sea_booking_id),
            "has_air_booking": bool(created_order.air_booking_id),
        },
    )
    db.commit()
    db.refresh(created_order)

    return created_order


@router.get("/{shipment_order_id}", response_model=ShipmentOrderResponse)
def get_single_shipment_order(
    shipment_order_id: UUID,
    current_user: User = Depends(get_current_customer_user),
    db: Session = Depends(get_db),
):
    shipment_order = get_shipment_order(db, shipment_order_id, current_user.id)
    if not shipment_order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Shipment order not found"
        )
    return shipment_order


@router.get("/", response_model=List[ShipmentOrderResponse])
def get_my_shipment_orders(
    skip: int = 0,
    limit: int = 100,
    current_user: User = Depends(get_current_customer_user),
    db: Session = Depends(get_db),
):
    return get_shipment_orders_by_user(db, current_user.id, skip=skip, limit=limit)


@router.get("/by-container/{sea_booking_id}")
def get_shipment_orders_for_sea_booking(
    sea_booking_id: UUID,
    current_user: User = Depends(get_current_customer_user),
    db: Session = Depends(get_db),
):
    """Get all shipment orders for a specific sea booking"""
    orders = get_shipment_orders_by_sea_booking(db, sea_booking_id, current_user.id)
    return orders


@router.get("/by-air-booking/{air_booking_id}")
def get_shipment_orders_for_air_booking(
    air_booking_id: UUID,
    current_user: User = Depends(get_current_customer_user),
    db: Session = Depends(get_db),
):
    """Get all shipment orders for a specific air cargo booking"""
    orders = get_shipment_orders_by_air_booking(db, air_booking_id, current_user.id)
    return orders


@router.put("/{shipment_order_id}", response_model=ShipmentOrderResponse)
def update_my_shipment_order(
    shipment_order_id: UUID,
    shipment_order_update: ShipmentOrderUpdate,
    current_user: User = Depends(get_current_customer_user),
    db: Session = Depends(get_db),
):
    # Get the current order to compare status changes
    current_order = get_shipment_order(db, shipment_order_id, current_user.id)
    if not current_order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Shipment order not found"
        )

    previous_status = current_order.status
    updated_order = update_shipment_order(
        db, shipment_order_id, shipment_order_update, current_user.id
    )
    if not updated_order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Shipment order not found"
        )

    # Create tracking event if status changed
    if shipment_order_update.status and str(shipment_order_update.status) != str(
        previous_status
    ):
        TrackingService.create_tracking_event(
            db=db,
            entity_type="shipment_order",
            entity_id=str(updated_order.id),
            event_type="shipment_order_status_updated",
            description=f"Shipment order status updated from {previous_status} to {updated_order.status}",
            triggered_by=str(current_user.id),
            extra_data={
                "old_status": str(previous_status),
                "new_status": updated_order.status,
                "order_description": updated_order.order_description,
            },
        )
        db.commit()
        db.refresh(updated_order)

    return updated_order


@router.delete("/{shipment_order_id}")
def delete_my_shipment_order(
    shipment_order_id: UUID,
    current_user: User = Depends(get_current_customer_user),
    db: Session = Depends(get_db),
):
    deleted = delete_shipment_order(db, shipment_order_id, current_user.id)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Shipment order not found"
        )
    return {"message": "Shipment order deleted successfully"}
