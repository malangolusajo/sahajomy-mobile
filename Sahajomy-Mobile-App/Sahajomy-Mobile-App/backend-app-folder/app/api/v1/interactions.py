"""Threaded interactions API for orders, shipments, and products."""

from __future__ import annotations

from collections import defaultdict
from typing import Literal, Optional
from uuid import UUID

from app.core.dependencies import get_any_authenticated_user
from app.database import get_db
from app.models.air_cargo import ExpressAirCargoBooking
from app.models.container import SeaBooking
from app.models.interaction import Interaction, InteractionReaction
from app.models.shipment_orders import ShipmentOrder
from app.models.sourcing import SourcingOrder, SourcingProduct
from app.models.user import User
from app.services.realtime_notifications import create_notification
from app.services.shipment_orders_service import cargo_admin_can_access_shipment_order
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session, joinedload

router = APIRouter(tags=["Interactions"])

TargetType = Literal["order", "shipment", "product", "sea_booking", "booking"]
ReactionType = Literal["like", "dislike"]
ADMIN_COMMUNICATION_ROLES = {"cargo_admin", "super_admin"}
USER_COMMUNICATION_ROLES = {"customer", "sourcing_agent"}
TARGET_TYPE_QUERY = Query(...)
TARGET_ID_QUERY = Query(...)
DB_SESSION_DEP = Depends(get_db)
ANY_AUTH_USER_DEP = Depends(get_any_authenticated_user)


class InteractionCreateRequest(BaseModel):
    target_type: TargetType
    target_id: str
    content: str = Field(..., min_length=1, max_length=4000)
    parent_id: Optional[str] = None


class InteractionReactionRequest(BaseModel):
    reaction: Optional[ReactionType] = None


def _parse_uuid(value: str, field_name: str) -> UUID:
    try:
        return UUID(str(value))
    except (ValueError, TypeError):
        raise HTTPException(status_code=400, detail=f"Invalid {field_name}")


def _get_target_entity(db: Session, target_type: str, target_id: UUID):
    if target_type == "order":
        return (
            db.query(SourcingOrder)
            .options(joinedload(SourcingOrder.batch))
            .filter(SourcingOrder.id == target_id)
            .first()
        )
    if target_type == "shipment":
        return db.query(ShipmentOrder).filter(ShipmentOrder.id == target_id).first()
    if target_type == "product":
        return (
            db.query(SourcingProduct)
            .options(joinedload(SourcingProduct.batch))
            .filter(SourcingProduct.id == target_id)
            .first()
        )
    if target_type == "sea_booking":
        return (
            db.query(SeaBooking)
            .options(joinedload(SeaBooking.container))
            .filter(SeaBooking.id == target_id)
            .first()
        )
    if target_type == "booking":
        return (
            db.query(ExpressAirCargoBooking)
            .filter(ExpressAirCargoBooking.id == target_id)
            .first()
        )
    return None


def _get_target_owner_ids(target_type: str, entity) -> set[UUID]:
    owner_ids: set[UUID] = set()
    if not entity:
        return owner_ids

    if target_type == "order":
        if entity.customer_id:
            owner_ids.add(entity.customer_id)
        if entity.batch and entity.batch.agent_id:
            owner_ids.add(entity.batch.agent_id)
    elif target_type == "shipment":
        if entity.created_by_user_id:
            owner_ids.add(entity.created_by_user_id)
    elif target_type == "product":
        if entity.batch and entity.batch.agent_id:
            owner_ids.add(entity.batch.agent_id)
    elif target_type == "sea_booking":
        if entity.user_id:
            owner_ids.add(entity.user_id)
    elif target_type == "booking":
        if entity.customer_id:
            owner_ids.add(entity.customer_id)
        if entity.sourcing_agent_id:
            owner_ids.add(entity.sourcing_agent_id)
    return owner_ids


def _can_access_target(
    db: Session, current_user: User, target_type: TargetType, entity
) -> bool:
    """Authorize interaction access for the current user and target entity."""
    if current_user.role == "super_admin":
        return True

    if target_type == "order":
        if current_user.role in ADMIN_COMMUNICATION_ROLES:
            return True
        if entity.customer_id == current_user.id:
            return True
        if entity.batch and entity.batch.agent_id == current_user.id:
            return True
        return False

    if target_type == "product":
        if current_user.role in ADMIN_COMMUNICATION_ROLES:
            return True
        if entity.batch and entity.batch.agent_id == current_user.id:
            return True
        # Allow customers who have orders in this batch to participate.
        if current_user.role == "customer":
            return (
                db.query(SourcingOrder.id)
                .filter(
                    SourcingOrder.customer_id == current_user.id,
                    SourcingOrder.batch_id == entity.batch_id,
                )
                .first()
                is not None
            )
        return False

    if target_type == "shipment":
        if current_user.role == "super_admin":
            return True
        if entity.created_by_user_id == current_user.id:
            return True
        if current_user.role == "cargo_admin":
            return cargo_admin_can_access_shipment_order(db, entity.id, current_user.id)
        return False

    if target_type == "sea_booking":
        if entity.user_id == current_user.id:
            return True
        if current_user.role == "cargo_admin":
            return bool(
                entity.container
                and entity.container.admin_id
                and entity.container.admin_id == current_user.id
            )
        return False

    if target_type == "booking":
        if entity.customer_id == current_user.id:
            return True
        if entity.sourcing_agent_id == current_user.id:
            return True
        if current_user.role == "cargo_admin":
            return bool(
                entity.cargo_admin_id and entity.cargo_admin_id == current_user.id
            )
        return False

    return False


def _get_admin_recipient_ids(db: Session, target_type: str, entity) -> set[UUID]:
    recipient_ids: set[UUID] = set()
    if target_type == "shipment" and entity:
        if entity.air_booking_id:
            booking = (
                db.query(ExpressAirCargoBooking)
                .filter(ExpressAirCargoBooking.id == entity.air_booking_id)
                .first()
            )
            if booking and booking.cargo_admin_id:
                recipient_ids.add(booking.cargo_admin_id)
        if entity.sea_booking_id:
            sea_booking = (
                db.query(SeaBooking)
                .filter(SeaBooking.id == entity.sea_booking_id)
                .first()
            )
            if sea_booking and sea_booking.container and sea_booking.container.admin_id:
                recipient_ids.add(sea_booking.container.admin_id)
    elif target_type == "sea_booking" and entity:
        if entity.container and entity.container.admin_id:
            recipient_ids.add(entity.container.admin_id)
    elif target_type == "booking" and entity:
        if entity.cargo_admin_id:
            recipient_ids.add(entity.cargo_admin_id)

    if not recipient_ids:
        admins = (
            db.query(User.id)
            .filter(User.role.in_(["cargo_admin", "super_admin"]))
            .all()
        )
        recipient_ids.update(row[0] for row in admins)

    return recipient_ids


def _interaction_message(
    current_user: User, parent: Interaction | None, target_type: str
) -> str:
    actor = current_user.name or "A user"
    labels = {
        "order": "order",
        "shipment": "shipment",
        "product": "product",
        "sea_booking": "sea_booking",
        "booking": "booking",
    }
    target_label = labels.get(target_type, "thread")
    if current_user.role in ADMIN_COMMUNICATION_ROLES:
        return (
            f"{actor} replied to your {target_label} conversation."
            if parent
            else f"{actor} posted an admin update."
        )
    return (
        f"{actor} replied to your {target_label} conversation."
        if parent
        else f"{actor} posted a new {target_label} comment."
    )


def _serialize_interaction(
    node: Interaction, user_map: dict[str, User], reaction_map: dict[str, str]
):
    user = user_map.get(str(node.user_id))
    display_name = user.name if user and user.name else "User"
    return {
        "id": str(node.id),
        "target_type": node.target_type,
        "target_id": str(node.target_id),
        "parent_id": str(node.parent_id) if node.parent_id else None,
        "content": node.content,
        "likes_count": int(node.likes_count or 0),
        "dislikes_count": int(node.dislikes_count or 0),
        "user_reaction": reaction_map.get(str(node.id)),
        "created_at": node.created_at.isoformat() if node.created_at else None,
        "updated_at": node.updated_at.isoformat() if node.updated_at else None,
        "user": {
            "id": str(node.user_id),
            "name": display_name,
            "profile_image_url": user.profile_image_url if user else None,
        },
        "replies": [],
    }


@router.get("/interactions")
def get_interactions(
    target_type: TargetType = TARGET_TYPE_QUERY,
    target_id: str = TARGET_ID_QUERY,
    db: Session = DB_SESSION_DEP,
    current_user: User = ANY_AUTH_USER_DEP,
):
    parsed_target_id = _parse_uuid(target_id, "target_id")

    entity = _get_target_entity(db, target_type, parsed_target_id)
    if not entity:
        raise HTTPException(status_code=404, detail="Target entity not found")
    if not _can_access_target(db, current_user, target_type, entity):
        raise HTTPException(status_code=403, detail="Not authorized to access target")

    rows = (
        db.query(Interaction)
        .filter(
            Interaction.target_type == target_type,
            Interaction.target_id == parsed_target_id,
        )
        .order_by(Interaction.created_at.asc())
        .all()
    )

    if not rows:
        return []

    user_ids = {row.user_id for row in rows}
    users = db.query(User).filter(User.id.in_(user_ids)).all()
    user_map = {str(u.id): u for u in users}

    reactions = (
        db.query(InteractionReaction)
        .filter(
            InteractionReaction.user_id == current_user.id,
            InteractionReaction.interaction_id.in_([row.id for row in rows]),
        )
        .all()
    )
    reaction_map = {str(r.interaction_id): r.reaction_type for r in reactions}

    serialized = {
        str(row.id): _serialize_interaction(row, user_map, reaction_map) for row in rows
    }
    tree_children = defaultdict(list)
    roots = []
    for row in rows:
        row_id = str(row.id)
        if row.parent_id:
            tree_children[str(row.parent_id)].append(row_id)
        else:
            roots.append(row_id)

    for parent_id, child_ids in tree_children.items():
        serialized[parent_id]["replies"] = [serialized[cid] for cid in child_ids]

    return [serialized[root_id] for root_id in roots]


@router.post("/interactions")
def create_interaction(
    body: InteractionCreateRequest,
    db: Session = DB_SESSION_DEP,
    current_user: User = ANY_AUTH_USER_DEP,
):
    parsed_target_id = _parse_uuid(body.target_id, "target_id")
    entity = _get_target_entity(db, body.target_type, parsed_target_id)
    if not entity:
        raise HTTPException(status_code=404, detail="Target entity not found")
    if not _can_access_target(db, current_user, body.target_type, entity):
        raise HTTPException(status_code=403, detail="Not authorized to access target")

    parent = None
    if body.parent_id:
        parent_id = _parse_uuid(body.parent_id, "parent_id")
        parent = db.query(Interaction).filter(Interaction.id == parent_id).first()
        if not parent:
            raise HTTPException(status_code=404, detail="Parent interaction not found")
        if parent.target_type != body.target_type or str(parent.target_id) != str(
            parsed_target_id
        ):
            raise HTTPException(
                status_code=400, detail="Parent interaction target mismatch"
            )

    content = body.content.strip()
    if not content:
        raise HTTPException(status_code=400, detail="Content is required")

    interaction = Interaction(
        user_id=current_user.id,
        target_type=body.target_type,
        target_id=parsed_target_id,
        parent_id=parent.id if parent else None,
        content=content,
    )
    db.add(interaction)
    db.flush()

    recipient_ids = _get_target_owner_ids(body.target_type, entity)
    if current_user.role in USER_COMMUNICATION_ROLES:
        recipient_ids.update(_get_admin_recipient_ids(db, body.target_type, entity))
    elif current_user.role in ADMIN_COMMUNICATION_ROLES and parent:
        recipient_ids.add(parent.user_id)

    if parent:
        recipient_ids.add(parent.user_id)

    recipient_ids.discard(current_user.id)
    for recipient_id in recipient_ids:
        create_notification(
            db=db,
            user_id=recipient_id,
            notification_type="interaction_update",
            message=_interaction_message(current_user, parent, body.target_type),
            priority="info",
            target_type=body.target_type,
            target_id=parsed_target_id,
        )

    db.commit()
    db.refresh(interaction)

    return {
        "id": str(interaction.id),
        "target_type": interaction.target_type,
        "target_id": str(interaction.target_id),
        "parent_id": str(interaction.parent_id) if interaction.parent_id else None,
        "content": interaction.content,
        "likes_count": int(interaction.likes_count or 0),
        "dislikes_count": int(interaction.dislikes_count or 0),
        "user_reaction": None,
        "created_at": (
            interaction.created_at.isoformat() if interaction.created_at else None
        ),
        "updated_at": (
            interaction.updated_at.isoformat() if interaction.updated_at else None
        ),
        "user": {
            "id": str(current_user.id),
            "name": current_user.name or "User",
            "profile_image_url": current_user.profile_image_url,
        },
        "replies": [],
    }


@router.post("/interactions/{interaction_id}/reaction")
def react_to_interaction(
    interaction_id: str,
    body: InteractionReactionRequest,
    db: Session = DB_SESSION_DEP,
    current_user: User = ANY_AUTH_USER_DEP,
):
    parsed_interaction_id = _parse_uuid(interaction_id, "interaction_id")
    interaction = (
        db.query(Interaction).filter(Interaction.id == parsed_interaction_id).first()
    )
    if not interaction:
        raise HTTPException(status_code=404, detail="Interaction not found")
    entity = _get_target_entity(db, interaction.target_type, interaction.target_id)
    if not entity or not _can_access_target(
        db, current_user, interaction.target_type, entity
    ):
        raise HTTPException(status_code=403, detail="Not authorized to access target")

    existing = (
        db.query(InteractionReaction)
        .filter(
            InteractionReaction.interaction_id == interaction.id,
            InteractionReaction.user_id == current_user.id,
        )
        .first()
    )

    desired = body.reaction
    if existing and desired == existing.reaction_type:
        desired = None

    if existing:
        if existing.reaction_type == "like":
            interaction.likes_count = max(0, int(interaction.likes_count or 0) - 1)
        elif existing.reaction_type == "dislike":
            interaction.dislikes_count = max(
                0, int(interaction.dislikes_count or 0) - 1
            )

    if desired is None:
        if existing:
            db.delete(existing)
    elif existing:
        existing.reaction_type = desired
        if desired == "like":
            interaction.likes_count = int(interaction.likes_count or 0) + 1
        else:
            interaction.dislikes_count = int(interaction.dislikes_count or 0) + 1
    else:
        db.add(
            InteractionReaction(
                interaction_id=interaction.id,
                user_id=current_user.id,
                reaction_type=desired,
            )
        )
        if desired == "like":
            interaction.likes_count = int(interaction.likes_count or 0) + 1
        else:
            interaction.dislikes_count = int(interaction.dislikes_count or 0) + 1

    db.commit()
    db.refresh(interaction)

    return {
        "interaction_id": str(interaction.id),
        "likes_count": int(interaction.likes_count or 0),
        "dislikes_count": int(interaction.dislikes_count or 0),
        "user_reaction": desired,
    }
