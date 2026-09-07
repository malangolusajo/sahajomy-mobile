# backend/app/api/v1/websocket/containers.py
import logging
from typing import Dict, Set

from app.database import SessionLocal
from app.models.container import Container, SeaBooking
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from sqlalchemy import func

logger = logging.getLogger(__name__)
router = APIRouter()


class ConnectionManager:
    def __init__(self):
        # room_id -> Set[WebSocket]
        self.active_connections: Dict[str, Set[WebSocket]] = {}
        # user_id -> room_id
        self.user_rooms: Dict[str, str] = {}

    async def connect(
        self, websocket: WebSocket, user_id: str, lat: float, lon: float, radius: float
    ):
        await websocket.accept()

        # Create room based on approximate location (geohash precision 4 = ~20km)
        import geohash2

        room_id = geohash2.encode(lat, lon, precision=4)

        if room_id not in self.active_connections:
            self.active_connections[room_id] = set()

        self.active_connections[room_id].add(websocket)
        self.user_rooms[user_id] = room_id

        # Send initial container data
        await self.send_initial_containers(websocket, lat, lon, radius)

        return room_id

    def disconnect(self, websocket: WebSocket, user_id: str):
        if user_id in self.user_rooms:
            room_id = self.user_rooms[user_id]
            if room_id in self.active_connections:
                self.active_connections[room_id].discard(websocket)
                if not self.active_connections[room_id]:
                    del self.active_connections[room_id]
            del self.user_rooms[user_id]

    async def send_initial_containers(
        self, websocket: WebSocket, lat: float, lon: float, radius: float
    ):
        """Send initial container list"""
        db = SessionLocal()
        try:
            # Get containers from database
            containers = (
                db.query(Container)
                .filter(Container.status.in_(["open", "nearly_full"]))
                .limit(50)
                .all()
            )
            booked_cbm_rows = (
                db.query(
                    SeaBooking.container_id,
                    func.coalesce(func.sum(SeaBooking.cbm_booked), 0).label(
                        "booked_cbm"
                    ),
                )
                .group_by(SeaBooking.container_id)
                .all()
            )
            booked_cbm_map = {
                str(container_id): float(booked_cbm or 0)
                for container_id, booked_cbm in booked_cbm_rows
            }

            # Format response
            container_list = []
            for c in containers:
                # Calculate distance (simplified)
                distance = (
                    self.calculate_distance(
                        lat,
                        lon,
                        (
                            float(c.warehouse_origin.latitude)
                            if c.warehouse_origin
                            else lat
                        ),
                        (
                            float(c.warehouse_origin.longitude)
                            if c.warehouse_origin
                            else lon
                        ),
                    )
                    if c.warehouse_origin
                    else 0
                )

                if distance <= radius:
                    booked_cbm = booked_cbm_map.get(
                        str(c.id), float(c.booked_cbm or 0)
                    )
                    max_cbm = float(c.max_cbm or 0)
                    container_list.append(
                        {
                            "id": str(c.id),
                            "operator": c.admin.name if c.admin else "Cargo Company",
                            "origin": (
                                c.warehouse_origin.city
                                if c.warehouse_origin
                                else "China"
                            ),
                            "destination": (
                                c.destination_warehouse.city
                                if c.destination_warehouse
                                else "Africa"
                            ),
                            "container_size": c.container_size,
                            "max_cbm": float(c.max_cbm),
                            "available_cbm": max(max_cbm - booked_cbm, 0),
                            "fill_percentage": (
                                round((booked_cbm / max_cbm) * 100, 2)
                                if max_cbm > 0
                                else 0.0
                            ),
                            "price_per_cbm": float(c.price_per_cbm),
                            "status": c.status,
                            "distance": round(distance, 2),
                            "latitude": (
                                float(c.warehouse_origin.latitude)
                                if c.warehouse_origin
                                else None
                            ),
                            "longitude": (
                                float(c.warehouse_origin.longitude)
                                if c.warehouse_origin
                                else None
                            ),
                        }
                    )

            await websocket.send_json({"type": "initial", "containers": container_list})

        finally:
            db.close()

    async def broadcast_container_update(self, container_id: str, update_data: dict):
        """Broadcast container update to all relevant rooms"""
        # Get container location to determine rooms
        db = SessionLocal()
        try:
            container = db.query(Container).filter(Container.id == container_id).first()
            if not container or not container.warehouse_origin:
                return

            lat = float(container.warehouse_origin.latitude)
            lon = float(container.warehouse_origin.longitude)

            if lat and lon:
                import geohash2

                room_id = geohash2.encode(lat, lon, precision=4)

                if room_id in self.active_connections:
                    message = {"type": "update", "container": update_data}
                    for connection in self.active_connections[room_id]:
                        try:
                            await connection.send_json(message)
                        except Exception:
                            pass
        finally:
            db.close()

    def calculate_distance(self, lat1, lon1, lat2, lon2):
        """Haversine formula to calculate distance between two points"""
        from math import atan2, cos, radians, sin, sqrt

        R = 6371  # Earth's radius in kilometers

        lat1, lon1, lat2, lon2 = map(radians, [lat1, lon1, lat2, lon2])

        dlat = lat2 - lat1
        dlon = lon2 - lon1

        a = sin(dlat / 2) ** 2 + cos(lat1) * cos(lat2) * sin(dlon / 2) ** 2
        c = 2 * atan2(sqrt(a), sqrt(1 - a))

        return R * c


manager = ConnectionManager()


@router.websocket("/ws/containers")
async def websocket_endpoint(
    websocket: WebSocket,
    user_id: str = "anonymous",
    lat: float = -6.8,
    lon: float = 39.2,
    radius: float = 50,
):
    await manager.connect(websocket, user_id, lat, lon, radius)
    try:
        while True:
            # Keep connection alive with ping/pong
            data = await websocket.receive_text()
            if data == "ping":
                await websocket.send_text("pong")
    except WebSocketDisconnect:
        manager.disconnect(websocket, user_id)
