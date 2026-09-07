"""
Models: User, Guest, OTPVerification, RefreshToken
Aligned with Sahajomy Platform v3.0 spec.
"""

import enum
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
    Enum,
    ForeignKey,
    LargeBinary,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.orm import relationship

# ======================================================
# ENUMS
# ======================================================


class AuthProvider(str, enum.Enum):
    """Authentication provider for user login"""

    OTP = "otp"


# ======================================================
# USER
# ======================================================


class User(Base):
    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    name = Column(String, index=True)  # Changed to match likely database schema

    # 🔒 ENCRYPTED FIELDS - Primary storage for sensitive data
    phone_encrypted = Column(LargeBinary, nullable=True)  # AES encrypted phone
    phone_hash = Column(
        String(64), nullable=True, unique=True, index=True
    )  # Hashed phone for lookups
    email_encrypted = Column(LargeBinary, nullable=True)  # AES encrypted email
    email_hash = Column(
        String(64), nullable=True, unique=True, index=True
    )  # Hashed email for lookups

    # 📞📧 DEPRECATED PLAIN TEXT FIELDS - For backward compatibility only
    # These will be removed in future versions after migration
    email = Column(String, unique=True, index=True, nullable=True)
    phone_number = Column(String, unique=True, index=True, nullable=True)

    auth_provider = Column(Enum(AuthProvider), nullable=False, default=AuthProvider.OTP)
    is_active = Column(Boolean, default=True)
    is_verified = Column(Boolean, default=False)
    is_admin = Column(Boolean, default=False)
    role = Column(
        String, default="customer"
    )  # customer, sourcing_agent, cargo_admin, super_admin
    status = Column(String, default="active")  # active, suspended, etc.
    verification_code = Column(String, nullable=True)
    verification_code_expiry = Column(DateTime, nullable=True)
    profile_image_url = Column(String, nullable=True)
    encrypted_key = Column(LargeBinary, nullable=True)
    mfa_secret_encrypted = Column(LargeBinary, nullable=True)
    mfa_enabled = Column(Boolean, nullable=False, default=False)
    mfa_enrolled_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # ================= SECURE ACCESS PROPERTIES =================

    @hybrid_property
    def secure_phone(self) -> Optional[str]:
        """Get decrypted phone number securely"""
        if self.phone_encrypted:
            return data_encryption.decrypt_phone(self.phone_encrypted)
        elif self.phone_number:
            # Backward compatibility - migrate to encrypted field
            if self.phone_number and not self.phone_hash:
                self.phone_encrypted = data_encryption.encrypt_phone(self.phone_number)
                self.phone_hash = data_encryption.hash_phone(self.phone_number)
                # Note: In practice, you'd need to commit this change
            return self.phone_number
        return None

    @hybrid_property
    def secure_email(self) -> Optional[str]:
        """Get decrypted email securely"""
        if self.email_encrypted:
            return data_encryption.decrypt_email(self.email_encrypted)
        elif self.email:
            # Backward compatibility - migrate to encrypted field
            if self.email and not self.email_hash:
                self.email_encrypted = data_encryption.encrypt_email(self.email)
                self.email_hash = data_encryption.hash_email(self.email)
                # Note: In practice, you'd need to commit this change
            return self.email
        return None

    # ================= AUTH =================

    refresh_tokens = relationship(
        "RefreshToken", back_populates="user", cascade="all, delete-orphan"
    )

    otp_verifications = relationship(
        "OTPVerification", back_populates="user", cascade="all, delete-orphan"
    )

    # ================= RELATIONSHIPS =================

    # Warehouses managed by this user (as cargo admin)
    warehouses = relationship(
        "Warehouse", back_populates="admin", cascade="all, delete-orphan"
    )

    # Containers managed by this user (as cargo admin)
    containers = relationship(
        "Container",
        back_populates="admin",
        foreign_keys="[Container.admin_id]",
    )

    cargo_operator_profile = relationship(
        "CargoOperatorProfile",
        foreign_keys="[CargoOperatorProfile.user_id]",
        back_populates="user",
        uselist=False,
        cascade="all, delete-orphan",
    )

    # ================= SOURCING =================

    # Sourcing batches managed by this user (as sourcing agent)
    sourcing_batches = relationship("SourcingBatch", back_populates="agent")

    # Sourcing orders placed by this user (as customer)
    sourcing_orders = relationship("SourcingOrder", back_populates="customer")

    # Public Agizisha requests assigned to this user (as sourcing agent).
    agizisha_orders = relationship(
        "AgizishaOrder",
        back_populates="sourcing_agent",
        foreign_keys="[AgizishaOrder.sourcing_agent_id]",
    )

    # ================= SEA_BOOKINGS =================

    # SeaBookings OWNED by this user
    sea_bookings = relationship(
        "SeaBooking",
        foreign_keys="[SeaBooking.user_id]",
        back_populates="user",
    )

    # SeaBookings where this user MARKED A HOLD
    holds_marked = relationship(
        "SeaBooking", foreign_keys="[SeaBooking.hold_marked_by]"
    )

    # Shipment orders created by this user (as customer)
    shipment_orders_created = relationship(
        "ShipmentOrder",
        back_populates="created_by_user",
        foreign_keys="[ShipmentOrder.created_by_user_id]",
        cascade="all, delete-orphan",
    )

    # ================= AIR CARGO BOOKINGS =================
    # Bookings where user is the customer
    express_air_bookings_as_customer = relationship(
        "ExpressAirCargoBooking",
        foreign_keys="[ExpressAirCargoBooking.customer_id]",
        back_populates="customer",
        cascade="all, delete-orphan",
    )

    # Bookings where user is the sourcing agent
    express_air_bookings_as_agent = relationship(
        "ExpressAirCargoBooking",
        foreign_keys="[ExpressAirCargoBooking.sourcing_agent_id]",
        back_populates="sourcing_agent",
        cascade="all, delete-orphan",
    )

    # Bookings assigned to this user as cargo admin
    express_air_bookings_as_admin = relationship(
        "ExpressAirCargoBooking",
        foreign_keys="[ExpressAirCargoBooking.cargo_admin_id]",
        back_populates="cargo_admin",
    )

    # Public FCL quote requests may be linked to a customer later and are
    # assigned to a specific cargo admin within the cargo-admin role.
    fcl_quote_requests = relationship(
        "QuoteRequest",
        foreign_keys="[QuoteRequest.customer_id]",
        back_populates="customer",
    )
    fcl_quote_requests_assigned_as_cargo_admin = relationship(
        "QuoteRequest",
        foreign_keys="[QuoteRequest.assigned_cargo_admin_id]",
        back_populates="assigned_cargo_admin",
    )

    # ================= SYSTEM =================
    # Relationship to notifications for the user
    notifications = relationship("Notification", back_populates="user")
    # Relationship to audit logs for the user
    audit_logs = relationship("AuditLog", back_populates="user")
    # Relationship to tracking events triggered by the user
    tracking_events = relationship("TrackingEvent", back_populates="user")
    interactions = relationship(
        "Interaction", back_populates="user", cascade="all, delete-orphan"
    )
    interaction_reactions = relationship(
        "InteractionReaction",
        back_populates="user",
        cascade="all, delete-orphan",
    )

    # ================= END RELATIONSHIPS =================


# Define relationships after class definition to avoid initialization issues

# ======================================================
# GUEST
# ======================================================


class Guest(Base):
    """Temporary buyers via batch share link. No OTP, no JWT, no dashboard."""

    __tablename__ = "guests"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(150), nullable=False)
    phone_number = Column(String(20), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    sourcing_orders = relationship("SourcingOrder", back_populates="guest")


# ======================================================
# OTP VERIFICATION
# ======================================================


class OTPVerification(Base):
    __tablename__ = "otp_verifications"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    # Legacy plaintext fields remain readable only for short-lived records
    # issued before the security migration. New OTPs use the keyed hashes below.
    phone_number = Column(String(20), nullable=True, index=True)
    phone_hash = Column(String(64), nullable=True, index=True)

    user_id = Column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=True
    )

    otp_code = Column(String(10), nullable=True)
    otp_code_hash = Column(String(64), nullable=True, index=True)
    expires_at = Column(DateTime, nullable=False)
    verified = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="otp_verifications")


# ======================================================
# REFRESH TOKEN
# ======================================================


class RefreshToken(Base):
    __tablename__ = "refresh_tokens"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    user_id = Column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )

    token = Column(Text, nullable=False, unique=True)
    expires_at = Column(DateTime, nullable=False)
    revoked = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="refresh_tokens")
