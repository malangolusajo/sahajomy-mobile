from datetime import datetime

from app.database import get_db
from app.models.container import Container
from app.models.finance import CommissionSettings, Receipt, ReceiptScan
from app.models.sourcing import (
    BatchShareToken,
    SourcingBatch,
    SourcingOrder,
    SourcingOrderItem,
    SourcingProduct,
)
from app.models.user import Guest, User
from app.services.goods_catalog import serialize_goods_catalog
from app.services.company_service_governance import company_service_is_bookable
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy import func
from sqlalchemy.orm import Session

router = APIRouter(prefix="/public", tags=["Public"])


# ====== SHARED BATCH ENDPOINT ======
@router.get("/batch/{token}")
def view_shared_batch(token: str, db: Session = Depends(get_db)):
    if not (20 <= len(token) <= 200):
        raise HTTPException(status_code=404, detail="Batch not found or link invalid")
    share_token = (
        db.query(BatchShareToken).filter(BatchShareToken.token == token).first()
    )
    if not share_token:
        raise HTTPException(status_code=404, detail="Batch not found or link invalid")
    if share_token.expires_at and share_token.expires_at < datetime.utcnow():
        raise HTTPException(status_code=410, detail="Share link expired")
    if share_token.max_views and share_token.current_views >= share_token.max_views:
        raise HTTPException(status_code=410, detail="Share link view limit reached")

    share_token.current_views += 1
    db.commit()

    batch = (
        db.query(SourcingBatch)
        .filter(
            SourcingBatch.id == share_token.batch_id, SourcingBatch.status == "open"
        )
        .first()
    )
    if not batch:
        raise HTTPException(status_code=404, detail="Batch not available")

    products = (
        db.query(SourcingProduct).filter(SourcingProduct.batch_id == batch.id).all()
    )
    return {
        "batch_id": str(batch.id),
        "title": batch.title,
        "description": batch.description,
        "products": [
            {
                "id": str(p.id),
                "name": p.name,
                "description": p.description,
                "cbm_per_unit": float(p.cbm_per_unit),
                "price_per_unit": float(p.price_per_unit),
                "image_url": p.image_url,
            }
            for p in products
        ],
    }


# ====== RECEIPT VERIFICATION ======
@router.get("/receipt/verify/{token}")
def verify_receipt(token: str, request: Request, db: Session = Depends(get_db)):
    if not (20 <= len(token) <= 200):
        raise HTTPException(status_code=404, detail="Receipt not found")
    receipt = db.query(Receipt).filter(Receipt.receipt_token == token).first()
    if not receipt:
        raise HTTPException(status_code=404, detail="Receipt not found")

    scan = ReceiptScan(
        receipt_id=receipt.id,
        ip_address=request.client.host if request.client else None,
    )
    db.add(scan)
    db.commit()

    order = receipt.order
    return {
        "valid": True,
        "receipt_number": receipt.receipt_number,
        "generated_at": receipt.generated_at.isoformat(),
        "order_id": str(order.id) if order else None,
        "total_amount": float(order.total_product_amount or 0) if order else None,
    }


# ====== GOODS CATEGORIES ======
@router.get("/goods/categories")
def list_goods_categories(db: Session = Depends(get_db)):
    return serialize_goods_catalog(db)


# ====== PLATFORM STATS (FOR LANDING PAGE) ======
@router.get("/platform-stats")
def get_platform_stats(db: Session = Depends(get_db)):
    """Get live platform statistics for landing page"""

    live_containers = (
        db.query(Container)
        .filter(Container.status.in_(["open", "nearly_full"]))
        .count()
    )

    active_operators = (
        db.query(User)
        .filter(
            User.role == "admin",
            User.containers.any(Container.status.in_(["open", "nearly_full"])),
        )
        .count()
    )

    available_cbm = (
        db.query(func.sum(Container.max_cbm - Container.booked_cbm))
        .filter(Container.status.in_(["open", "nearly_full"]))
        .scalar()
        or 0
    )

    return {
        "containers": live_containers,
        "operators": active_operators,
        "cbm": float(available_cbm),
    }


# ====== FEATURED CONTAINERS (FOR LANDING PAGE) ======
@router.get("/featured-containers")
def get_featured_containers(db: Session = Depends(get_db)):
    """Get 3 featured containers for landing page preview"""

    containers = (
        db.query(Container)
        .filter(Container.status.in_(["open", "nearly_full"]))
        .order_by(Container.created_at.desc())
        .limit(3)
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

    return [
        {
            "id": str(c.id),
            "operator": c.admin.name if c.admin else "Cargo Company",
            "route": f"{c.origin_warehouse.city if c.origin_warehouse else 'China'} → {c.destination_warehouse.city if c.destination_warehouse else 'East Africa'}",
            "available_cbm": float(c.max_cbm - c.booked_cbm),
            "fill_percentage": round(
                (c.booked_cbm / c.max_cbm * 100) if c.max_cbm > 0 else 0, 0
            ),
            "price_per_cbm": float(c.price_per_cbm),
            "container_size": c.container_size,
            "status": c.status,
        }
        for c in containers
    ]


# ====== NEW: PUBLIC CONTAINERS LISTING ======
@router.get("/containers")
def list_public_containers(limit: int = 10, db: Session = Depends(get_db)):
    """Public endpoint to browse available containers (no login required)"""
    containers = (
        db.query(Container)
        .filter(Container.status.in_(["open", "nearly_full"]))
        .order_by(Container.created_at.desc())
        .limit(limit)
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

    return [
        {
            "id": str(c.id),
            "operator": c.admin.name if c.admin else "Cargo Company",
            "route": f"{c.origin_warehouse.city if c.origin_warehouse else 'China'} → {c.destination_warehouse.city if c.destination_warehouse else 'East Africa'}",
            "available_cbm": float(c.max_cbm - c.booked_cbm),
            "fill_percentage": round(
                (c.booked_cbm / c.max_cbm * 100) if c.max_cbm > 0 else 0, 0
            ),
            "price_per_cbm": float(c.price_per_cbm),
            "container_size": c.container_size,
            "status": c.status,
            "departure_date": (
                c.departure_date.isoformat() if c.departure_date else None
            ),
            "estimated_arrival": (
                c.estimated_arrival_date.isoformat()
                if c.estimated_arrival_date
                else None
            ),
        }
        for c in containers
    ]
