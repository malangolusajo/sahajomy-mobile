import uuid
from datetime import datetime

from app.database import Base
from sqlalchemy import (
    CheckConstraint,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship


class Interaction(Base):
    __tablename__ = "interactions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    target_type = Column(
        String(30), nullable=False, index=True
    )  # order | shipment | product | sea_booking | booking
    target_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    parent_id = Column(
        UUID(as_uuid=True),
        ForeignKey("interactions.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    content = Column(Text, nullable=False)
    likes_count = Column(Integer, nullable=False, default=0)
    dislikes_count = Column(Integer, nullable=False, default=0)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )

    __table_args__ = (
        CheckConstraint(
            "target_type IN ('order','shipment','product','sea_booking','booking')",
            name="chk_interactions_target_type",
        ),
    )

    user = relationship("User", back_populates="interactions")
    parent = relationship("Interaction", remote_side=[id], back_populates="replies")
    replies = relationship(
        "Interaction", back_populates="parent", cascade="all, delete-orphan"
    )
    reactions = relationship(
        "InteractionReaction",
        back_populates="interaction",
        cascade="all, delete-orphan",
    )


class InteractionReaction(Base):
    __tablename__ = "interaction_reactions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    interaction_id = Column(
        UUID(as_uuid=True),
        ForeignKey("interactions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    reaction_type = Column(String(10), nullable=False)  # like | dislike
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )

    __table_args__ = (
        CheckConstraint(
            "reaction_type IN ('like','dislike')",
            name="chk_interaction_reaction_type",
        ),
        UniqueConstraint(
            "interaction_id", "user_id", name="uq_interaction_user_reaction"
        ),
    )

    interaction = relationship("Interaction", back_populates="reactions")
    user = relationship("User", back_populates="interaction_reactions")
