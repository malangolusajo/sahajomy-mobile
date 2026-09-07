"""
General Notification API endpoints
Handles fetching notifications for all user types
"""

import logging
import uuid

import jwt
from app.core.config import settings
from app.core.dependencies import get_current_user
from app.core.encryption import data_encryption
from app.database import SessionLocal, get_db
from app.models.finance import Notification
from app.models.user import User
from app.services.realtime_notifications import (
    notification_realtime_manager,
    serialize_notification,
)
from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    Query,
    WebSocket,
    WebSocketDisconnect,
)
from jwt.exceptions import PyJWTError as JWTError
from sqlalchemy.orm import Session

router = APIRouter(tags=["Notifications"])

logger = logging.getLogger(__name__)


@router.get("/notifications")
async def get_notifications(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    skip: int = 0,
    limit: int = 100,
):
    """
    Get all notifications for the current user
    Available to all authenticated users
    """
    notifications = (
        db.query(Notification)
        .filter(Notification.user_id == current_user.id)
        .order_by(Notification.created_at.desc())
        .limit(50)  # Limit to last 50 notifications
        .all()
    )

    unread_count = (
        db.query(Notification)
        .filter(
            Notification.user_id == current_user.id,
            Notification.is_read.is_(False),
        )
        .count()
    )

    return {
        "notifications": [serialize_notification(n) for n in notifications],
        "unread_count": unread_count,
    }


@router.put("/notifications/{notification_id}/mark-read")
def mark_notification_as_read(
    notification_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Mark a specific notification as read
    Available to all authenticated users
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
    notification_realtime_manager.send_to_user_sync(
        str(current_user.id),
        {
            "event": "notification_read",
            "notification_id": str(notification.id),
        },
    )

    return {"success": True, "message": "Notification marked as read"}


@router.patch("/notifications/{notification_id}/read")
def mark_notification_as_read_patch(
    notification_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return mark_notification_as_read(notification_id, db, current_user)


@router.put("/notifications/mark-all-read")
def mark_all_notifications_as_read(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Mark all notifications for the current user as read
    Available to all authenticated users
    """
    unread = (
        db.query(Notification)
        .filter(
            Notification.user_id == current_user.id,
            Notification.is_read.is_(False),
        )
        .count()
    )

    db.query(Notification).filter(
        Notification.user_id == current_user.id, Notification.is_read.is_(False)
    ).update({"is_read": True})

    db.commit()
    if unread > 0:
        notification_realtime_manager.send_to_user_sync(
            str(current_user.id),
            {"event": "notifications_all_read"},
        )

    return {"success": True, "message": "All notifications marked as read"}


@router.delete("/notifications/{notification_id}")
def delete_notification(
    notification_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Delete one notification owned by the authenticated user."""
    notification = (
        db.query(Notification)
        .filter(
            Notification.id == notification_id,
            Notification.user_id == current_user.id,
        )
        .first()
    )

    if not notification:
        raise HTTPException(status_code=404, detail="Notification not found")

    deleted_id = str(notification.id)
    was_unread = not notification.is_read
    db.delete(notification)
    db.commit()
    notification_realtime_manager.send_to_user_sync(
        str(current_user.id),
        {
            "event": "notification_deleted",
            "notification_id": deleted_id,
            "was_unread": was_unread,
        },
    )

    return {
        "success": True,
        "message": "Notification deleted",
        "was_unread": was_unread,
    }


async def get_websocket_user(
    websocket: WebSocket, token: str = Query(None)
) -> User | None:
    """
    Authenticate user for WebSocket connection using token from query parameter.
    Mimics the logic of get_current_user but adapted for WebSockets.
    """
    token = token or websocket.cookies.get(settings.ACCESS_COOKIE_NAME)
    if not token:
        await websocket.close(code=4401)
        return None

    try:
        payload = jwt.decode(
            token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM]
        )
        if payload.get("type") != "access":
            await websocket.close(code=4401)
            return None

        user_identifier = payload.get("sub")
        if not user_identifier:
            await websocket.close(code=4401)
            return None
    except JWTError:
        await websocket.close(code=4401)
        return None

    db = SessionLocal()
    try:
        # Check if user_identifier is a UUID (for agents/admins) or phone number (for customers)
        try:
            # Try to parse as UUID - if successful, it's an agent/admin
            user_id_uuid = uuid.UUID(user_identifier)
            user = db.query(User).filter(User.id == user_id_uuid).first()
        except ValueError:
            # Not a valid UUID, treat as phone number for customers
            phone_hash = data_encryption.hash_phone(user_identifier)
            user = db.query(User).filter(User.phone_hash == phone_hash).first()

        if not user:
            await websocket.close(code=4401)
            return None

        return user
    finally:
        db.close()


@router.websocket("/ws/notifications")
async def websocket_notifications(websocket: WebSocket, token: str = Query(None)):
    """
    WebSocket endpoint for real-time notifications.
    Browser clients authenticate with the HttpOnly session cookie. The token
    query parameter remains available for non-browser clients.
    """
    user = await get_websocket_user(websocket, token)
    if not user:
        return  # get_websocket_user already closed the connection

    await websocket.accept()

    try:
        # Register this connection with the notification manager
        user_id_str = str(user.id)
        await notification_realtime_manager.connect(user_id_str, websocket)

        # Keep connection alive
        while True:
            # Wait for any message (we don't expect client messages, just keep alive)
            await websocket.receive_text()

    except WebSocketDisconnect:
        # Clean up when client disconnects
        notification_realtime_manager.disconnect(user_id_str, websocket)
    except Exception as e:
        # Handle any other exceptions and clean up
        error_msg = f"WebSocket error for user {user_id_str}: {e}"
        logger.error(error_msg)
        notification_realtime_manager.disconnect(user_id_str, websocket)
        await websocket.close()
