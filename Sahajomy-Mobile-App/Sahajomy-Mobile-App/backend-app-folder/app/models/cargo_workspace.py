"""Cargo company workspaces, staff memberships, branches, roles, and permissions."""

import uuid
from datetime import datetime, timedelta

from app.database import Base
from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    String,
    Table,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

role_permissions = Table(
    "cargo_role_permissions",
    Base.metadata,
    Column(
        "role_id",
        UUID(as_uuid=True),
        ForeignKey("cargo_roles.id", ondelete="CASCADE"),
        primary_key=True,
    ),
    Column(
        "permission_id",
        UUID(as_uuid=True),
        ForeignKey("cargo_permissions.id", ondelete="CASCADE"),
        primary_key=True,
    ),
)


class CargoCompany(Base):
    __tablename__ = "cargo_companies"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(180), nullable=False, index=True)
    status = Column(String(20), nullable=False, default="active", index=True)
    base_currency = Column(
        String(3), nullable=False, default="USD", server_default="USD"
    )
    logo_url = Column(String(500), nullable=True)
    created_by_user_id = Column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL")
    )
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    branches = relationship(
        "CargoBranch", back_populates="company", cascade="all, delete-orphan"
    )
    memberships = relationship(
        "CargoCompanyMembership", back_populates="company", cascade="all, delete-orphan"
    )
    roles = relationship(
        "CargoRole", back_populates="company", cascade="all, delete-orphan"
    )


class CargoBranch(Base):
    __tablename__ = "cargo_branches"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    company_id = Column(
        UUID(as_uuid=True),
        ForeignKey("cargo_companies.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    name = Column(String(150), nullable=False)
    country = Column(String(100), nullable=False)
    city = Column(String(120), nullable=False)
    warehouse_id = Column(
        UUID(as_uuid=True), ForeignKey("warehouses.id", ondelete="SET NULL")
    )
    status = Column(String(20), nullable=False, default="active", index=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    company = relationship("CargoCompany", back_populates="branches")
    __table_args__ = (
        UniqueConstraint("company_id", "name", name="uq_cargo_branch_company_name"),
    )


class CargoPermission(Base):
    __tablename__ = "cargo_permissions"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    key = Column(String(100), nullable=False, unique=True, index=True)
    description = Column(Text)


class CargoRole(Base):
    __tablename__ = "cargo_roles"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    company_id = Column(
        UUID(as_uuid=True),
        ForeignKey("cargo_companies.id", ondelete="CASCADE"),
        index=True,
    )
    name = Column(String(100), nullable=False)
    scope = Column(String(20), nullable=False, default="branch")
    is_system = Column(Boolean, nullable=False, default=False)
    company = relationship("CargoCompany", back_populates="roles")
    permissions = relationship(
        "CargoPermission", secondary=role_permissions, lazy="selectin"
    )
    __table_args__ = (
        UniqueConstraint("company_id", "name", name="uq_cargo_role_company_name"),
    )


class CargoCompanyMembership(Base):
    __tablename__ = "cargo_company_memberships"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    company_id = Column(
        UUID(as_uuid=True),
        ForeignKey("cargo_companies.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    role_id = Column(
        UUID(as_uuid=True),
        ForeignKey("cargo_roles.id", ondelete="RESTRICT"),
        nullable=False,
    )
    default_branch_id = Column(
        UUID(as_uuid=True), ForeignKey("cargo_branches.id", ondelete="SET NULL")
    )
    status = Column(String(20), nullable=False, default="pending", index=True)
    created_by_user_id = Column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL")
    )
    invited_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    joined_at = Column(DateTime)
    disabled_at = Column(DateTime)
    company = relationship("CargoCompany", back_populates="memberships")
    user = relationship("User", foreign_keys=[user_id])
    role = relationship("CargoRole", lazy="joined")
    default_branch = relationship("CargoBranch")
    __table_args__ = (
        UniqueConstraint(
            "user_id", "company_id", name="uq_cargo_membership_user_company"
        ),
    )


class CargoStaffInvitation(Base):
    __tablename__ = "cargo_staff_invitations"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    company_id = Column(
        UUID(as_uuid=True),
        ForeignKey("cargo_companies.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    branch_id = Column(
        UUID(as_uuid=True), ForeignKey("cargo_branches.id", ondelete="SET NULL")
    )
    role_id = Column(
        UUID(as_uuid=True),
        ForeignKey("cargo_roles.id", ondelete="RESTRICT"),
        nullable=False,
    )
    invited_email_hash = Column(String(64), index=True)
    invited_phone_hash = Column(String(64), index=True)
    token_hash = Column(String(64), nullable=False, unique=True, index=True)
    status = Column(String(20), nullable=False, default="pending")
    invited_by_user_id = Column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL")
    )
    expires_at = Column(
        DateTime, nullable=False, default=lambda: datetime.utcnow() + timedelta(days=7)
    )
    accepted_at = Column(DateTime)
