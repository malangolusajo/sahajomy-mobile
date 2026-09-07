"""
WhatsApp chat state tracking for users
"""

import uuid
from datetime import datetime

from app.database import Base
from sqlalchemy import JSON, Boolean, Column, DateTime, ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship


class WhatsAppState(Base):
    __tablename__ = "whatsapp_states"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # Link to user (optional - could be before user is created)
    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )

    # Phone identifier (for users not yet registered)
    phone_hash = Column(String(64), nullable=False, index=True, unique=True)

    # Current chat state (NEW, MENU, ASK_NAME, etc.)
    current_state = Column(String(50), nullable=False, default="new")

    # Context data (JSON)
    context = Column(JSON, nullable=True, default={})

    # Timestamps
    last_interaction = Column(DateTime, default=datetime.utcnow)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    user = relationship("User", back_populates="whatsapp_state")
