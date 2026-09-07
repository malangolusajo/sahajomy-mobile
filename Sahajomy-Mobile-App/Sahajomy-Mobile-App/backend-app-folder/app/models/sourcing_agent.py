"""Sourcing agent registration profile model."""

import uuid
from datetime import datetime
from typing import Optional

from app.core.encryption import data_encryption
from app.database import Base
from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Column,
    DateTime,
    ForeignKey,
    LargeBinary,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.orm import relationship


class SourcingAgent(Base):
    __tablename__ = "sourcing_agents"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        unique=True,
        index=True,
    )
    full_name = Column(String(150), nullable=False, index=True)
    phone_encrypted = Column(LargeBinary, nullable=True)
    phone_hash = Column(String(64), nullable=True, unique=True, index=True)
    email_encrypted = Column(LargeBinary, nullable=True)
    email_hash = Column(String(64), nullable=True, unique=True, index=True)
    # Deprecated plain fields kept for backward compatibility.
    phone = Column(String(30), nullable=True, unique=True, index=True)
    email = Column(String(255), nullable=True, unique=True, index=True)
    whatsapp = Column(String(30), nullable=True)
    instagram = Column(String(255), nullable=True, index=True)
    tiktok = Column(String(255), nullable=True, index=True)
    niche = Column(String(100), nullable=False, index=True)
    location = Column(String(120), nullable=False, index=True)
    bio = Column(Text, nullable=True)
    years_experience = Column(String(30), nullable=True)
    profile_photo = Column(Text, nullable=True)
    # Public storefronts are deliberately opt-in.  Contact details and social
    # handles above remain registration/admin data and are never included in
    # the Agizisha public serializers.
    public_handle = Column(String(80), nullable=True, unique=True, index=True)
    is_public = Column(Boolean, nullable=False, default=False, server_default="false")
    status = Column(String(20), nullable=False, default="pending", index=True)
    is_verified = Column(Boolean, nullable=False, default=False, index=True)
    verified_at = Column(DateTime, nullable=True)
    verified_by = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )

    __table_args__ = (
        CheckConstraint(
            "status IN ('pending','verified','rejected','inactive')",
            name="chk_sourcing_agent_status",
        ),
    )

    user = relationship("User", foreign_keys=[user_id])
    verifier = relationship("User", foreign_keys=[verified_by])

    @hybrid_property
    def secure_phone(self) -> Optional[str]:
        if self.phone_encrypted:
            return data_encryption.decrypt_phone(self.phone_encrypted)
        elif self.phone:
            if not self.phone_hash:
                self.phone_encrypted = data_encryption.encrypt_phone(self.phone)
                self.phone_hash = data_encryption.hash_phone(self.phone)
            return self.phone
        return self.phone

    @hybrid_property
    def secure_email(self) -> Optional[str]:
        if self.email_encrypted:
            return data_encryption.decrypt_email(self.email_encrypted)
        elif self.email:
            if not self.email_hash:
                self.email_encrypted = data_encryption.encrypt_email(self.email)
                self.email_hash = data_encryption.hash_email(self.email)
            return self.email
        return self.email
