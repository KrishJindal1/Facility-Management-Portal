"""
SQLAlchemy ORM models for HomeDesk Facility Management Portal.
Enforces multi-tenant data architecture where users and leads belong strictly to an organization.
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


class Organization(Base):
    """Tenant/Organization entity representing a platform tenant."""
    __tablename__ = "organizations"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(100), nullable=False)
    slug = Column(String(100), unique=True, nullable=False, index=True)
    created_at = Column(DateTime, default=get_utc_now, nullable=False)

    users = relationship("User", back_populates="organization", cascade="all, delete-orphan")
    leads = relationship("Lead", back_populates="organization", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Organization {self.name} ({self.slug})>"


class User(Base):
    """User entity belonging to an organization."""
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, autoincrement=True)
    organization_id = Column(
        Integer,
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    name = Column(String(100), nullable=False)
    mobile = Column(String(20), nullable=False, index=True)
    email = Column(String(120), unique=True, nullable=True, index=True)
    password_hash = Column(String(255), nullable=True)
    role = Column(String(30), default="customer", nullable=False)
    created_at = Column(DateTime, default=get_utc_now, nullable=False)

    organization = relationship("Organization", back_populates="users")
    leads = relationship("Lead", back_populates="user")

    __table_args__ = (
        Index("idx_users_org_mobile", "organization_id", "mobile"),
        Index("idx_users_org_email", "organization_id", "email"),
    )

    def __repr__(self):
        return f"<User {self.name} ({self.email}) - Org {self.organization_id}>"


class Lead(Base):
    """Core lead entity storing customer request information strictly scoped to a tenant."""
    __tablename__ = "leads"

    id = Column(Integer, primary_key=True, autoincrement=True)
    lead_id = Column(String(30), nullable=False, index=True)
    organization_id = Column(
        Integer,
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    service_type = Column(String(50), nullable=False, index=True)
    name = Column(String(100), nullable=False)
    mobile = Column(String(20), nullable=False, index=True)
    email = Column(String(120), nullable=True)
    address = Column(Text, nullable=True)
    city = Column(String(100), nullable=False)
    state = Column(String(100), nullable=True)
    pincode = Column(String(10), nullable=True)
    start_date = Column(Date, nullable=True)
    preferred_timing = Column(String(50), nullable=True)
    budget = Column(Float, nullable=False)
    additional_notes = Column(Text, nullable=True)
    status = Column(String(30), default="New", nullable=False)
    created_at = Column(DateTime, default=get_utc_now, nullable=False)
    updated_at = Column(DateTime, default=get_utc_now, onupdate=get_utc_now, nullable=False)

    organization = relationship("Organization", back_populates="leads")
    user = relationship("User", back_populates="leads")

    cook_requirement = relationship(
        "CookRequirement",
        back_populates="lead",
        uselist=False,
        cascade="all, delete-orphan",
    )
    driver_requirement = relationship(
        "DriverRequirement",
        back_populates="lead",
        uselist=False,
        cascade="all, delete-orphan",
    )
    security_guard_requirement = relationship(
        "SecurityGuardRequirement",
        back_populates="lead",
        uselist=False,
        cascade="all, delete-orphan",
    )

    __table_args__ = (
        Index("idx_leads_org_mobile", "organization_id", "mobile"),
        Index("idx_leads_org_lead_id", "organization_id", "lead_id", unique=True),
        Index("idx_leads_org_service", "organization_id", "service_type"),
    )

    def __repr__(self):
        return f"<Lead {self.lead_id} (Org {self.organization_id}) - {self.service_type} - {self.name}>"


class CookRequirement(Base):
    """Service-specific details for Cook requests."""
    __tablename__ = "cook_requirements"

    id = Column(Integer, primary_key=True, autoincrement=True)
    lead_id = Column(Integer, ForeignKey("leads.id", ondelete="CASCADE"), unique=True, nullable=False, index=True)
    cuisine_type = Column(String(100), nullable=True)
    meals_per_day = Column(Integer, nullable=True)

    lead = relationship("Lead", back_populates="cook_requirement")

    def __repr__(self):
        return f"<CookRequirement lead_id={self.lead_id} ({self.cuisine_type})>"


class DriverRequirement(Base):
    """Service-specific details for Driver requests."""
    __tablename__ = "driver_requirements"

    id = Column(Integer, primary_key=True, autoincrement=True)
    lead_id = Column(Integer, ForeignKey("leads.id", ondelete="CASCADE"), unique=True, nullable=False, index=True)
    vehicle_type = Column(String(100), nullable=True)
    license_required = Column(String(20), nullable=True)

    lead = relationship("Lead", back_populates="driver_requirement")

    def __repr__(self):
        return f"<DriverRequirement lead_id={self.lead_id} ({self.vehicle_type})>"


class SecurityGuardRequirement(Base):
    """Service-specific details for Security Guard requests."""
    __tablename__ = "security_guard_requirements"

    id = Column(Integer, primary_key=True, autoincrement=True)
    lead_id = Column(Integer, ForeignKey("leads.id", ondelete="CASCADE"), unique=True, nullable=False, index=True)
    shift = Column(String(50), nullable=True)
    site_type = Column(String(50), nullable=True)

    lead = relationship("Lead", back_populates="security_guard_requirement")

    def __repr__(self):
        return f"<SecurityGuardRequirement lead_id={self.lead_id} ({self.shift})>"
