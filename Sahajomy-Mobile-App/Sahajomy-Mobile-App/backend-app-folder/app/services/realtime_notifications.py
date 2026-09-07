"""Utilities for persisted notifications with real-time fanout."""

from __future__ import annotations

import asyncio
import logging
import uuid
from datetime import datetime
from typing import Any, Dict

from app.models.finance import Notification
from fastapi import WebSocket

logger = logging.getLogger(__name__)


class NotificationRealtimeManager:
    """Tracks notification websocket connections by user id."""

    def __init__(self) -> None:
        self.active_connections: dict[str, set[WebSocket]] = {}
        self._loop: asyncio.AbstractEventLoop | None = None

    def set_loop(self, loop: asyncio.AbstractEventLoop) -> None:
        self._loop = loop

    async def connect(self, user_id: str, websocket: WebSocket) -> None:
        self.active_connections.setdefault(user_id, set()).add(websocket)

    def disconnect(self, user_id: str, websocket: WebSocket) -> None:
        sockets = self.active_connections.get(user_id)
        if not sockets:
            return
        sockets.discard(websocket)
        if not sockets:
            self.active_connections.pop(user_id, None)

    async def send_to_user(self, user_id: str, payload: Dict[str, Any]) -> None:
        sockets = list(self.active_connections.get(user_id, set()))
        if not sockets:
            return

        dead: list[WebSocket] = []
        for ws in sockets:
            try:
                await ws.send_json(payload)
            except Exception:
                dead.append(ws)

        if dead:
            current = self.active_connections.get(user_id, set())
            for ws in dead:
                current.discard(ws)
            if not current:
                self.active_connections.pop(user_id, None)

    def send_to_user_sync(self, user_id: str, payload: Dict[str, Any]) -> None:
        """Thread-safe bridge for sync endpoints running in threadpool workers."""
        if not self._loop or self._loop.is_closed():
            return
        try:
            asyncio.run_coroutine_threadsafe(
                self.send_to_user(user_id, payload), self._loop
            )
        except Exception as exc:
            logger.debug("Realtime notification send failed: %s", exc)


notification_realtime_manager = NotificationRealtimeManager()


def serialize_notification(notification: Notification) -> Dict[str, Any]:
    return {
        "id": str(notification.id),
        "type": notification.type,
        "message": notification.message,
        "is_read": bool(notification.is_read),
        "priority": notification.priority or "info",
        "target_type": notification.target_type,
        "target_id": str(notification.target_id) if notification.target_id else None,
        "created_at": (
            notification.created_at.isoformat()
            if notification.created_at
            else datetime.utcnow().isoformat()
        ),
    }


def create_notification(
    db,
    user_id,
    notification_type: str,
    message: str,
    priority: str = "info",
    target_type: str | None = None,
    target_id=None,
) -> Notification:
    """Persist notification and push live event to connected clients."""
    parsed_target_id = None
    if target_id:
        try:
            parsed_target_id = uuid.UUID(str(target_id))
        except (ValueError, TypeError):
            parsed_target_id = None

    notification = Notification(
        user_id=user_id,
        type=notification_type,
        message=message,
        priority=priority or "info",
        target_type=target_type,
        target_id=parsed_target_id,
    )
    db.add(notification)
    db.flush()

    notification_realtime_manager.send_to_user_sync(
        str(user_id),
        {
            "event": "notification_created",
            "notification": serialize_notification(notification),
        },
    )
    return notification
