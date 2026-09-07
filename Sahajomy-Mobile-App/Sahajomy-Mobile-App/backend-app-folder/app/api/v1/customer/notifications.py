"""
Customer Notification API endpoints
Handles fetching notifications for customers
"""

from typing import List

from app.core.dependencies import get_customer
from app.database import get_db
from app.models.finance import Notification
from app.models.user import User
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

router = APIRouter(prefix="/customer", tags=["Notifications"])


@router.get("/notifications")
def get_notifications(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_customer),
) -> List[dict]:
    """
    Get all notifications for the current user
    """
    notifications = (
        db.query(Notification)
        .filter(Notification.user_id == current_user.id)
        .order_by(Notification.created_at.desc())
        .limit(50)  # Limit to last 50 notifications
        .all()
    )

    return [
        {
            "id": str(notification.id),
            "type": notification.type,
            "message": notification.message,
            "is_read": notification.is_read,
            "priority": notification.priority or "info",
            "target_type": notification.target_type,
            "target_id": (
                str(notification.target_id) if notification.target_id else None
            ),
            "created_at": (
                notification.created_at.isoformat() if notification.created_at else None
            ),
        }
        for notification in notifications
    ]


@router.put("/notifications/{notification_id}/mark-read")
def mark_notification_as_read(
    notification_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_customer),
):
    """
    Mark a specific notification as read
    """
    notification = (
        db.query(Notification)
        .filter(
            Notification.id == notification_id, Notification.user_id == current_user.id
        )
        .first()
    )

    if not notification:
        from fastapi import HTTPException

        raise HTTPException(status_code=404, detail="Notification not found")

    notification.is_read = True
    db.commit()

    return {"success": True, "message": "Notification marked as read"}


@router.put("/notifications/mark-all-read")
def mark_all_notifications_as_read(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_customer),
):
    """
    Mark all notifications for the current user as read
    """
    db.query(Notification).filter(
        Notification.user_id == current_user.id, Notification.is_read.is_(False)
    ).update({"is_read": True})

    db.commit()

    return {"success": True, "message": "All notifications marked as read"}
