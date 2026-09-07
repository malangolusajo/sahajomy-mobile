"""Tracking models for logistics platform."""

import uuid
from datetime import datetime

from app.database import Base
from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import relationship


class TrackingEvent(Base):
    """
    Centralized tracking event system for all logistics entities.
    Captures status changes, milestones, and significant events across the platform.
    """

    __tablename__ = "tracking_events"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    entity_type = Column(
        String(50), nullable=False, index=True
    )  # container, sea_booking, order, booking, manual_cargo_intake
    entity_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    event_type = Column(
        String(100), nullable=False, index=True
    )  # departed, arrived, payment_confirmed, etc
    description = Column(Text, nullable=True)
    timestamp = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    triggered_by = Column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=True
    )
    extra_data = Column(JSONB, nullable=True)  # Additional event-specific data

    # Relationship to user who triggered the event
    user = relationship("User", back_populates="tracking_events")


class NotificationTemplate(Base):
    """
    Template system for notifications to ensure consistency and localization.
    """

    __tablename__ = "notification_templates"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(
        String(100), unique=True, nullable=False
    )  # e.g., "container_departed", "payment_due"
    subject = Column(String(200), nullable=True)  # Subject for email/push notifications
    message_template = Column(Text, nullable=False)  # Message with placeholders
    channel_preferences = Column(
        JSONB, nullable=True
    )  # Which channels to use by default
    enabled = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


# Add relationship to User model
# We'll need to update the User model separately to include this relationship
