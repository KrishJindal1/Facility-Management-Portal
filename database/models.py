"""
SQLAlchemy ORM models for HomeDesk Facility Management Portal.
Implements the Phase 2 business model:
1. NORMAL USER: Submits requirements, does not see other users' requirements.
2. ORGANIZATION: Registers with ONE service category, sees requirements matching its category.
3. ADMIN: Manages organizations and requirements across all categories.
Requirements belong to a Category and a Normal User (NOT directly to an organization).
"""
from datetime import datetime, timezone
from sqlalchemy import (
    Column,
    Integer,
    String,
    Text,
    Float,
    Date,
    DateTime,
    ForeignKey,
    Index,
)
from sqlalchemy.orm import relationship
from database.connection import Base


def get_utc_now():
    return datetime.now(timezone.utc)


class Category(Base):
    """
    Service Category entity (e.g. COOK, DRIVER, SECURITY_GUARD).
    Organizations register under one category.
    Requirements belong to one category.
    """
    __tablename__ = "categories"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(50), unique=True, nullable=False, index=True)  # e.g. 'COOK', 'DRIVER', 'SECURITY_GUARD'
    display_name = Column(String(100), nullable=True)  # e.g. 'Cook', 'Driver', 'Security Guard'
    created_at = Column(DateTime, default=get_utc_now, nullable=False)

    organizations = relationship("Organization", back_populates="category")
    requirements = relationship("Requirement", back_populates="category")

    def __repr__(self):
        return f"<Category {self.name} (id={self.id})>"


class Organization(Base):
    """
    Service Organization entity.
    Registers with exactly one service category.
    Can only access requirements matching its registered category_id.
    """
    __tablename__ = "organizations"

    id = Column(Integer, primary_key=True, autoincrement=True)
    organization_name = Column(String(100), nullable=False)
    slug = Column(String(100), unique=True, nullable=False, index=True)
    email = Column(String(120), unique=True, nullable=True, index=True)
    phone = Column(String(20), nullable=True)
    password_hash = Column(String(255), nullable=True)
    category_id = Column(
        Integer,
        ForeignKey("categories.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    status = Column(String(30), default="active", nullable=False)  # active, pending, suspended
    created_at = Column(DateTime, default=get_utc_now, nullable=False)

    category = relationship("Category", back_populates="organizations")
    users = relationship("User", back_populates="organization", cascade="all, delete-orphan")

    @property
    def name(self):
        return self.organization_name

    @name.setter
    def name(self, val):
        self.organization_name = val

    @property
    def mobile(self):
        return self.phone

    @mobile.setter
    def mobile(self, val):
        self.phone = val

    def __repr__(self):
        return f"<Organization {self.organization_name} (cat_id={self.category_id})>"


class User(Base):
    """
    User entity representing:
    - Normal user (role='user', organization_id=None): submits requirements
    - Organization member (role='organization', organization_id=org.id)
    - Platform admin (role='admin')
    """
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, autoincrement=True)
    organization_id = Column(
        Integer,
        ForeignKey("organizations.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    name = Column(String(100), nullable=False)
    email = Column(String(120), unique=True, nullable=True, index=True)
    phone = Column(String(20), nullable=False, index=True)
    password_hash = Column(String(255), nullable=True)
    role = Column(String(30), default="user", nullable=False)  # 'user', 'organization', 'admin'
    created_at = Column(DateTime, default=get_utc_now, nullable=False)

    organization = relationship("Organization", back_populates="users")
    requirements = relationship("Requirement", back_populates="user", cascade="all, delete-orphan")

    @property
    def mobile(self):
        return self.phone

    @mobile.setter
    def mobile(self, val):
        self.phone = val

    __table_args__ = (
        Index("idx_users_role", "role"),
        Index("idx_users_phone", "phone"),
    )

    def __repr__(self):
        return f"<User {self.name} ({self.phone}, role={self.role})>"


class Requirement(Base):
    """
    Customer Service Requirement / Lead entity.
    MUST belong to a Category (category_id).
    MUST belong to the Normal User who submitted it (user_id).
    Does NOT belong directly to an organization.
    Organizations see this requirement if organization.category_id == requirement.category_id.
    """
    __tablename__ = "requirements"

    id = Column(Integer, primary_key=True, autoincrement=True)
    lead_id = Column(String(30), unique=True, nullable=False, index=True)  # e.g. Cook-001
    user_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    category_id = Column(
        Integer,
        ForeignKey("categories.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    service_type = Column(String(50), nullable=False, index=True)  # 'Cook', 'Driver', 'Security Guard'

    # Customer snapshot fields (preserves form values)
    name = Column(String(100), nullable=False)
    mobile = Column(String(20), nullable=False, index=True)
    email = Column(String(120), nullable=True)
    address = Column(Text, nullable=True)
    city = Column(String(100), nullable=False)
    state = Column(String(100), nullable=True)
    pincode = Column(String(10), nullable=True)
    start_date = Column(Date, nullable=True)
    preferred_timing = Column(String(50), nullable=True)
    budget = Column(Float, nullable=False, default=0.0)
    additional_notes = Column(Text, nullable=True)
    status = Column(String(30), default="New", nullable=False)  # 'New', 'Claimed', 'Completed'
    created_at = Column(DateTime, default=get_utc_now, nullable=False)
    updated_at = Column(DateTime, default=get_utc_now, onupdate=get_utc_now, nullable=False)

    user = relationship("User", back_populates="requirements")
    category = relationship("Category", back_populates="requirements")

    cook_requirement = relationship(
        "CookRequirement",
        back_populates="requirement",
        uselist=False,
        cascade="all, delete-orphan",
    )
    driver_requirement = relationship(
        "DriverRequirement",
        back_populates="requirement",
        uselist=False,
        cascade="all, delete-orphan",
    )
    security_guard_requirement = relationship(
        "SecurityGuardRequirement",
        back_populates="requirement",
        uselist=False,
        cascade="all, delete-orphan",
    )

    @property
    def location(self):
        parts = [p for p in (self.city, self.state, self.pincode) if p]
        return ", ".join(parts) if parts else (self.city or "")

    @property
    def phone(self):
        return self.mobile

    @phone.setter
    def phone(self, val):
        self.mobile = val

    __table_args__ = (
        Index("idx_requirements_cat_status", "category_id", "status"),
        Index("idx_requirements_user_id", "user_id"),
        Index("idx_requirements_mobile", "mobile"),
    )

    def __repr__(self):
        return f"<Requirement {self.lead_id} ({self.service_type}) - User {self.user_id}>"


# Compatibility alias
Lead = Requirement


class CookRequirement(Base):
    """Service-specific details for Cook requests."""
    __tablename__ = "cook_requirements"

    id = Column(Integer, primary_key=True, autoincrement=True)
    requirement_id = Column(
        Integer,
        ForeignKey("requirements.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
        index=True,
    )
    cuisine_type = Column(String(100), nullable=True)
    meals_per_day = Column(Integer, nullable=True)

    requirement = relationship("Requirement", back_populates="cook_requirement")

    @property
    def lead(self):
        return self.requirement

    @lead.setter
    def lead(self, val):
        self.requirement = val

    def __repr__(self):
        return f"<CookRequirement req_id={self.requirement_id} ({self.cuisine_type})>"


class DriverRequirement(Base):
    """Service-specific details for Driver requests."""
    __tablename__ = "driver_requirements"

    id = Column(Integer, primary_key=True, autoincrement=True)
    requirement_id = Column(
        Integer,
        ForeignKey("requirements.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
        index=True,
    )
    vehicle_type = Column(String(100), nullable=True)
    license_required = Column(String(20), nullable=True)

    requirement = relationship("Requirement", back_populates="driver_requirement")

    @property
    def lead(self):
        return self.requirement

    @lead.setter
    def lead(self, val):
        self.requirement = val

    def __repr__(self):
        return f"<DriverRequirement req_id={self.requirement_id} ({self.vehicle_type})>"


class SecurityGuardRequirement(Base):
    """Service-specific details for Security Guard requests."""
    __tablename__ = "security_guard_requirements"

    id = Column(Integer, primary_key=True, autoincrement=True)
    requirement_id = Column(
        Integer,
        ForeignKey("requirements.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
        index=True,
    )
    shift = Column(String(50), nullable=True)
    site_type = Column(String(50), nullable=True)

    requirement = relationship("Requirement", back_populates="security_guard_requirement")

    @property
    def lead(self):
        return self.requirement

    @lead.setter
    def lead(self, val):
        self.requirement = val

    def __repr__(self):
        return f"<SecurityGuardRequirement req_id={self.requirement_id} ({self.shift})>"
