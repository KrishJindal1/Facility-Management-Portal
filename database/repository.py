"""
Data repository layer for HomeDesk Facility Management Portal.
Implements Phase 2 business model:
1. Requirements belong to a Category and the Normal User who submitted them.
2. Requirements do NOT belong directly to an organization.
3. An organization accesses requirements matching its category:
   organization.category_id == requirement.category_id
4. Excel exports are dynamically generated from PostgreSQL data.
"""
from __future__ import annotations
from datetime import datetime, date, timezone
import re
from typing import Optional, Dict, Any, List, Union, Tuple
import logging
from sqlalchemy import select, and_
from database import connection as db_conn
from database.connection import get_db
from database.models import (
    Base,
    Category,
    Organization,
    User,
    Requirement,
    CookRequirement,
    DriverRequirement,
    SecurityGuardRequirement,
    Lead,  # Compatibility alias
    get_utc_now,
)

logger = logging.getLogger(__name__)

# Category and Service Mappings
CATEGORY_NAMES = ["COOK", "DRIVER", "SECURITY_GUARD"]

SERVICE_TO_CATEGORY_NAME = {
    "Cook": "COOK",
    "Driver": "DRIVER",
    "Security Guard": "SECURITY_GUARD",
    "COOK": "COOK",
    "DRIVER": "DRIVER",
    "SECURITY_GUARD": "SECURITY_GUARD",
    "cook": "COOK",
    "driver": "DRIVER",
    "security_guard": "SECURITY_GUARD",
    "Security": "SECURITY_GUARD",
}

CATEGORY_NAME_TO_SERVICE = {
    "COOK": "Cook",
    "DRIVER": "Driver",
    "SECURITY_GUARD": "Security Guard",
}

SERVICE_PREFIX_MAP = {
    "Cook": "Cook",
    "Driver": "Driver",
    "Security Guard": "Security",
    "COOK": "Cook",
    "DRIVER": "Driver",
    "SECURITY_GUARD": "Security",
}


CONTROLLED_CATEGORIES = ("COOK", "DRIVER", "SECURITY_GUARD")


def normalize_category_name(service_or_cat: str) -> str:
    """Normalizes any service label or category string to 'COOK', 'DRIVER', or 'SECURITY_GUARD'."""
    clean = str(service_or_cat or "").strip()
    return SERVICE_TO_CATEGORY_NAME.get(clean, clean.upper().replace(" ", "_"))


def get_controlled_categories() -> List[Dict[str, Any]]:
    """
    Returns the list of controlled service categories from PostgreSQL.
    Categories are controlled system entities, not arbitrary user strings.
    """
    with get_db() as db:
        cats = db.query(Category).order_by(Category.id.asc()).all()
        return [
            {
                "id": c.id,
                "name": c.name,
                "display_name": c.display_name or CATEGORY_NAME_TO_SERVICE.get(c.name, c.name),
            }
            for c in cats
            if c.name in CONTROLLED_CATEGORIES
        ]


def resolve_controlled_category(category_name_or_id: Any) -> Optional[Category]:
    """
    Resolves a category identifier (ID or name string) against controlled categories in PostgreSQL.
    Returns the Category model if valid, or None if arbitrary/unauthorized.
    """
    if category_name_or_id is None:
        return None

    with get_db() as db:
        cat = None
        if isinstance(category_name_or_id, int) or (isinstance(category_name_or_id, str) and category_name_or_id.isdigit()):
            found = db.query(Category).filter_by(id=int(category_name_or_id)).first()
            if found and found.name in CONTROLLED_CATEGORIES:
                cat = found
        else:
            cat_code = normalize_category_name(str(category_name_or_id))
            if cat_code in CONTROLLED_CATEGORIES:
                cat = db.query(Category).filter_by(name=cat_code).first()

        if cat:
            _ = (cat.id, cat.name, cat.display_name)
            db.expunge(cat)
            return cat

    return None


def init_database() -> bool:
    """
    Initializes database schema tables and seeds default categories,
    organizations, and admin user. Safe to invoke multiple times.
    """
    try:
        from sqlalchemy import inspect
        active_engine = db_conn.engine
        inspector = inspect(active_engine)
        existing_tables = inspector.get_table_names()
        if "organizations" in existing_tables:
            cols = [c["name"] for c in inspector.get_columns("organizations")]
            if "organization_name" not in cols or "category_id" not in cols:
                logger.info("Upgrading legacy database schema to Phase 2 models...")
                Base.metadata.drop_all(bind=active_engine)

        Base.metadata.create_all(bind=active_engine)
        with get_db() as db:
            # 1. Seed Categories
            category_defs = [
                ("COOK", "Cook"),
                ("DRIVER", "Driver"),
                ("SECURITY_GUARD", "Security Guard"),
            ]
            cat_map = {}
            for code, display in category_defs:
                cat = db.query(Category).filter_by(name=code).first()
                if not cat:
                    cat = Category(name=code, display_name=display)
                    db.add(cat)
                    db.flush()
                cat_map[code] = cat.id

            # 2. Seed Default Organizations bound to categories
            org1 = db.query(Organization).filter_by(slug="homedesk").first()
            if not org1:
                org1 = Organization(
                    organization_name="HomeDesk Primary",
                    slug="homedesk",
                    category_id=cat_map["COOK"],
                    email="admin@homedesk.com",
                    status="active",
                )
                db.add(org1)

            org2 = db.query(Organization).filter_by(slug="acme").first()
            if not org2:
                org2 = Organization(
                    organization_name="Acme Facilities Group",
                    slug="acme",
                    category_id=cat_map["DRIVER"],
                    email="admin@acme.com",
                    status="active",
                )
                db.add(org2)
            else:
                if org2.organization_name != "Acme Facilities Group":
                    org2.organization_name = "Acme Facilities Group"

            org3 = db.query(Organization).filter_by(slug="ironshield").first()
            if not org3:
                org3 = Organization(
                    organization_name="IronShield Security",
                    slug="ironshield",
                    category_id=cat_map["SECURITY_GUARD"],
                    email="guards@ironshield.com",
                    status="active",
                )
                db.add(org3)

            db.flush()

            # 3. Seed Default Admin User
            admin_user = db.query(User).filter_by(email="admin@homedesk.com").first()
            if not admin_user:
                from services.auth_service import hash_password
                admin_user = User(
                    organization_id=org1.id,
                    name="HomeDesk Admin",
                    phone="9800000001",
                    email="admin@homedesk.com",
                    password_hash=hash_password("Password123!"),
                    role="admin",
                )
                db.add(admin_user)

            # 4. Seed Default Category Org Users
            acme_user = db.query(User).filter_by(email="admin@acme.com").first()
            if not acme_user:
                from services.auth_service import hash_password
                acme_user = User(
                    organization_id=org2.id,
                    name="Acme Admin",
                    phone="9800000002",
                    email="admin@acme.com",
                    password_hash=hash_password("Password123!"),
                    role="organization",
                )
                db.add(acme_user)

            cook_user = db.query(User).filter_by(email="cooks@homedesk.com").first()
            if not cook_user:
                from services.auth_service import hash_password
                cook_user = User(
                    organization_id=org1.id,
                    name="HomeDesk Cook Org User",
                    phone="9800000003",
                    email="cooks@homedesk.com",
                    password_hash=hash_password("Password123!"),
                    role="organization",
                )
                db.add(cook_user)

            sec_user = db.query(User).filter_by(email="guards@ironshield.com").first()
            if not sec_user:
                from services.auth_service import hash_password
                sec_user = User(
                    organization_id=org3.id,
                    name="IronShield Guard Admin",
                    phone="9800000004",
                    email="guards@ironshield.com",
                    password_hash=hash_password("Password123!"),
                    role="organization",
                )
                db.add(sec_user)

            # 5. Seed Demo Normal User
            normal_user = db.query(User).filter_by(email="user@homedesk.com").first()
            if not normal_user:
                from services.auth_service import hash_password
                normal_user = User(
                    organization_id=None,
                    name="Demo Customer",
                    phone="9800000005",
                    email="user@homedesk.com",
                    password_hash=hash_password("Password123!"),
                    role="user",
                )
                db.add(normal_user)

        return True
    except Exception as exc:
        logger.error("Database initialization failed: %s", exc)
        return False


def get_category_id_by_service_or_name(service_or_name: str) -> Optional[int]:
    """Resolves category ID from service label ('Cook', 'Driver', 'Security Guard') or category code."""
    cat_code = normalize_category_name(service_or_name)
    try:
        with get_db() as db:
            cat = db.query(Category).filter_by(name=cat_code).first()
            if cat:
                return cat.id
    except Exception as exc:
        logger.error("Failed to query category by name '%s': %s", cat_code, exc)
    return None


def generate_next_lead_id(service_name: str, organization_id: Optional[int] = None) -> str:
    """
    Generates the next sequential Lead ID (e.g. Cook-001, Driver-001, Security-001).
    Scans the database requirements pool.
    """
    prefix = SERVICE_PREFIX_MAP.get(service_name, service_name.split()[0])
    used_numbers = set()

    try:
        with get_db() as db:
            reqs = (
                db.query(Requirement.lead_id)
                .filter(Requirement.lead_id.like(f"{prefix}-%"))
                .all()
            )
            for (lid,) in reqs:
                try:
                    num = int(str(lid).split("-")[-1])
                    used_numbers.add(num)
                except (ValueError, IndexError):
                    continue
    except Exception as exc:
        logger.warning("Could not query Lead IDs for prefix %s: %s", prefix, exc)

    serial_number = 1
    while serial_number in used_numbers:
        serial_number += 1

    return f"{prefix}-{serial_number:03d}"


def _parse_date(val: Any) -> Optional[date]:
    """Helper to safely parse dates from string or date objects."""
    if not val:
        return None
    if isinstance(val, date):
        return val
    if isinstance(val, str):
        val = val.strip()
        for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%m/%d/%Y", "%d-%m-%Y"):
            try:
                return datetime.strptime(val, fmt).date()
            except ValueError:
                continue
    return None


def _parse_datetime(val: Any) -> datetime:
    """Helper to safely parse datetimes or default to current UTC time."""
    if not val:
        return datetime.now(timezone.utc)
    if isinstance(val, datetime):
        return val
    if isinstance(val, str):
        val = val.strip()
        for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d"):
            try:
                return datetime.strptime(val, fmt)
            except ValueError:
                continue
    return datetime.now(timezone.utc)


def _resolve_tenant_id(organization_id: Optional[int] = None) -> int:
    """Helper for backward compatibility."""
    if organization_id is not None:
        if organization_id <= 0:
            raise ValueError(f"Invalid organization_id {organization_id}")
        return organization_id
    from services.tenant_service import get_active_tenant_id
    tid = get_active_tenant_id()
    if tid:
        return tid
    return 1


def save_requirement_to_db(
    service_name: str,
    lead_data: Dict[str, Any],
    user_id: Optional[int] = None,
    organization_id: Optional[int] = None,
) -> Dict[str, Any]:
    """
    Saves a customer requirement to PostgreSQL.
    Enforces business model:
    - Requirement belongs to a Category (category_id).
    - Requirement belongs to the Normal User who submitted it (user_id).
    - Requirement does NOT belong directly to an organization.
    """
    if organization_id is not None:
        with get_db() as db:
            org = db.query(Organization).filter_by(id=organization_id).first()
            if not org:
                raise ValueError(f"Organization with id {organization_id} does not exist.")

    cat_code = normalize_category_name(service_name)
    display_service = CATEGORY_NAME_TO_SERVICE.get(cat_code, service_name)

    lead_id = lead_data.get("Lead ID") or generate_next_lead_id(display_service)
    name = (lead_data.get("Name") or "Valued Customer").strip()
    mobile = str(lead_data.get("Mobile") or lead_data.get("Mobile Number") or lead_data.get("phone") or "").strip()
    email = (lead_data.get("Email") or "").strip() or None
    address = lead_data.get("Address")
    city = (lead_data.get("City") or "").strip() or "Not Specified"
    state = lead_data.get("State")
    pincode = str(lead_data.get("Pincode") or "").strip() or None
    start_date = _parse_date(lead_data.get("Start Date"))
    preferred_timing = lead_data.get("Preferred Timing")
    budget = float(lead_data.get("Budget") or lead_data.get("Budget (INR)") or 0.0)
    additional_notes = lead_data.get("Additional Notes")
    status = lead_data.get("Status") or "New"
    created_at = _parse_datetime(lead_data.get("Date Time"))

    with get_db() as db:
        # 1. Resolve Category
        category = db.query(Category).filter_by(name=cat_code).first()
        if not category:
            category = Category(name=cat_code, display_name=display_service)
            db.add(category)
            db.flush()
        category_id = category.id

        # 2. Resolve or Create Normal User
        resolved_user_id = user_id
        if not resolved_user_id:
            # Check authenticated session
            try:
                from services.auth_service import get_current_user
                curr = get_current_user()
                if curr and curr.get("id"):
                    resolved_user_id = curr["id"]
            except Exception:
                pass

        if not resolved_user_id and mobile:
            user = db.query(User).filter_by(phone=mobile).first()
            if not user and email:
                user = db.query(User).filter_by(email=email).first()

            if not user:
                user_email = email
                if user_email and db.query(User).filter_by(email=user_email).first():
                    user_email = None  # prevent unique constraint collision
                user = User(
                    name=name,
                    phone=mobile,
                    email=user_email,
                    role="user",
                )
                db.add(user)
                db.flush()

            resolved_user_id = user.id

        if not resolved_user_id:
            # Fallback guest user
            guest = db.query(User).filter_by(phone="0000000000").first()
            if not guest:
                guest = User(name="Guest User", phone="0000000000", role="user")
                db.add(guest)
                db.flush()
            resolved_user_id = guest.id

        # 3. Create or Update Requirement
        req = db.query(Requirement).filter_by(lead_id=lead_id).first()
        if req:
            if req.category_id != category_id:
                raise ValueError(
                    f"Category tampering blocked: Requirement '{lead_id}' belongs to category ID {req.category_id} and cannot be changed to {category_id}."
                )
        else:
            req = Requirement(
                lead_id=lead_id,
                user_id=resolved_user_id,
                category_id=category_id,
                service_type=display_service,
                name=name,
                mobile=mobile,
                email=email,
                address=address,
                city=city,
                state=state,
                pincode=pincode,
                start_date=start_date,
                preferred_timing=preferred_timing,
                budget=budget,
                additional_notes=additional_notes,
                status=status,
                created_at=created_at,
            )
            db.add(req)
            db.flush()

        # 4. Service-Specific Child Details
        if cat_code == "COOK":
            cuisine = lead_data.get("Cuisine Type")
            meals = lead_data.get("Meals Per Day")
            meals_int = int(meals) if meals is not None and str(meals).isdigit() else None
            if not req.cook_requirement:
                req.cook_requirement = CookRequirement(
                    cuisine_type=cuisine,
                    meals_per_day=meals_int,
                )
            else:
                req.cook_requirement.cuisine_type = cuisine
                req.cook_requirement.meals_per_day = meals_int

        elif cat_code == "DRIVER":
            vehicle = lead_data.get("Vehicle Type")
            license_req = lead_data.get("License Required")
            if not req.driver_requirement:
                req.driver_requirement = DriverRequirement(
                    vehicle_type=vehicle,
                    license_required=license_req,
                )
            else:
                req.driver_requirement.vehicle_type = vehicle
                req.driver_requirement.license_required = license_req

        elif cat_code == "SECURITY_GUARD":
            shift = lead_data.get("Day/Night Shift")
            site = lead_data.get("Residential/Commercial")
            if not req.security_guard_requirement:
                req.security_guard_requirement = SecurityGuardRequirement(
                    shift=shift,
                    site_type=site,
                )
            else:
                req.security_guard_requirement.shift = shift
                req.security_guard_requirement.site_type = site

    lead_data["Lead ID"] = lead_id
    lead_data["Date Time"] = created_at.strftime("%Y-%m-%d %H:%M:%S")
    lead_data["Status"] = status
    lead_data["category_id"] = category_id
    lead_data["user_id"] = resolved_user_id
    lead_data["Service Type"] = display_service
    lead_data["Service"] = display_service
    return lead_data


# Backward-compatible alias
save_lead_to_db = save_requirement_to_db


def _requirement_to_dict(req: Requirement) -> Dict[str, Any]:
    """Helper to convert a Requirement ORM model into a standardized dictionary."""
    result: Dict[str, Any] = {
        "Lead ID": req.lead_id,
        "Service": req.service_type,
        "Service Type": req.service_type,
        "category_id": req.category_id,
        "user_id": req.user_id,
        "Name": req.name,
        "Mobile": req.mobile,
        "phone": req.mobile,
        "Email": req.email or "",
        "Address": req.address or "",
        "City": req.city,
        "State": req.state or "",
        "Pincode": req.pincode or "",
        "Start Date": req.start_date.strftime("%Y-%m-%d") if req.start_date else "",
        "Preferred Timing": req.preferred_timing or "",
        "Budget": req.budget,
        "Status": req.status,
        "Date Time": req.created_at.strftime("%Y-%m-%d %H:%M:%S"),
        "Additional Notes": req.additional_notes or "",
    }

    if req.service_type == "Cook" and req.cook_requirement:
        result["Cuisine Type"] = req.cook_requirement.cuisine_type or ""
        result["Meals Per Day"] = req.cook_requirement.meals_per_day

    elif req.service_type == "Driver" and req.driver_requirement:
        result["Vehicle Type"] = req.driver_requirement.vehicle_type or ""
        result["License Required"] = req.driver_requirement.license_required or ""

    elif req.service_type == "Security Guard" and req.security_guard_requirement:
        result["Day/Night Shift"] = req.security_guard_requirement.shift or ""
        result["Residential/Commercial"] = req.security_guard_requirement.site_type or ""

    return result


def get_latest_lead_by_mobile(
    mobile: str,
    organization_id: Optional[int] = None,
    category_id: Optional[int] = None,
) -> Optional[Dict[str, Any]]:
    """
    Retrieves the most recent requirement for a mobile number from PostgreSQL.
    If organization_id is provided, filters strictly by that organization's category_id.
    If category_id is provided, filters strictly by that category.
    """
    clean_mobile = str(mobile or "").strip()
    if not clean_mobile:
        return None

    resolved_cat_id = category_id
    if resolved_cat_id is None and organization_id:
        try:
            with get_db() as db:
                org = db.query(Organization).filter_by(id=organization_id).first()
                if org:
                    resolved_cat_id = org.category_id
        except Exception:
            pass

    try:
        with get_db() as db:
            query = db.query(Requirement).filter(Requirement.mobile == clean_mobile)
            if resolved_cat_id:
                query = query.filter(Requirement.category_id == resolved_cat_id)

            req = query.order_by(Requirement.created_at.desc(), Requirement.id.desc()).first()
            if not req:
                return None
            return _requirement_to_dict(req)

    except Exception as exc:
        logger.error("Failed to query requirement by mobile '%s': %s", clean_mobile, exc)
        return None


def get_lead_by_id(
    lead_id: str,
    organization_id: Optional[int] = None,
    category_id: Optional[int] = None,
) -> Optional[Dict[str, Any]]:
    """
    Retrieves a requirement by Lead ID from PostgreSQL.
    If organization_id is provided, enforces that the requirement matches the organization's category.
    """
    if not lead_id:
        return None

    resolved_cat_id = category_id
    if resolved_cat_id is None and organization_id:
        try:
            with get_db() as db:
                org = db.query(Organization).filter_by(id=organization_id).first()
                if org:
                    resolved_cat_id = org.category_id
        except Exception:
            pass

    try:
        with get_db() as db:
            query = db.query(Requirement).filter(Requirement.lead_id == lead_id.strip())
            if resolved_cat_id:
                query = query.filter(Requirement.category_id == resolved_cat_id)

            req = query.first()
            if not req:
                return None
            return _requirement_to_dict(req)

    except Exception as exc:
        logger.error("Failed to query requirement by id '%s': %s", lead_id, exc)
        return None


# Alias for requirement identifier
get_requirement_by_id = get_lead_by_id


def get_requirements_by_category(category_name_or_id: Union[str, int]) -> List[Dict[str, Any]]:
    """
    Retrieves all requirements matching a specific category from PostgreSQL.
    Enforces category filtering so organizations only see their registered service category.
    """
    cat_id = None
    if isinstance(category_name_or_id, int) or (isinstance(category_name_or_id, str) and category_name_or_id.isdigit()):
        cat_id = int(category_name_or_id)
    else:
        cat_code = normalize_category_name(str(category_name_or_id))
        with get_db() as db:
            cat = db.query(Category).filter_by(name=cat_code).first()
            if cat:
                cat_id = cat.id

    if not cat_id:
        return []

    try:
        with get_db() as db:
            reqs = (
                db.query(Requirement)
                .filter(Requirement.category_id == cat_id)
                .order_by(Requirement.id.desc())
                .all()
            )
            return [_requirement_to_dict(r) for r in reqs]
    except Exception as exc:
        logger.error("Failed to fetch requirements for category %s: %s", category_name_or_id, exc)
        return []


def get_requirements_for_organization(
    organization_id: int,
    requested_category: Optional[Any] = None,
) -> List[Dict[str, Any]]:
    """
    Core business logic: An organization sees requirements matching its category_id.
    organization.category_id == requirement.category_id
    A Cook organization sees Cook requirements.
    A Driver organization sees Driver requirements.
    A Security Guard organization sees Security Guard requirements.

    Security Rule: An organization CANNOT retrieve requirements of another category
    by manipulating UI state or request parameters. If a requested_category is passed,
    it MUST match the organization's stored category_id in PostgreSQL.
    """
    try:
        with get_db() as db:
            org = db.query(Organization).filter_by(id=organization_id).first()
            if not org:
                logger.warning("Organization with ID %s not found.", organization_id)
                return []
            cat_id = org.category_id

            if requested_category is not None:
                resolved_cat_id = None
                if isinstance(requested_category, int) or (isinstance(requested_category, str) and str(requested_category).isdigit()):
                    resolved_cat_id = int(requested_category)
                else:
                    norm = normalize_category_name(str(requested_category))
                    cat_obj = db.query(Category).filter_by(name=norm).first()
                    if cat_obj:
                        resolved_cat_id = cat_obj.id

                if resolved_cat_id is not None and resolved_cat_id != cat_id:
                    logger.warning(
                        "Blocked unauthorized attempt by organization %s (category %s) "
                        "to access category %s via parameter tampering.",
                        organization_id, cat_id, requested_category,
                    )
                    return []

        return get_requirements_by_category(cat_id)
    except Exception as exc:
        logger.error("Failed to fetch requirements for organization %s: %s", organization_id, exc)
        return []


def get_requirements_for_authenticated_user(
    user: Dict[str, Any],
    requested_category: Optional[Any] = None,
) -> List[Dict[str, Any]]:
    """
    Phase 4 RBAC-Guarded Data Access:
    - Enforces authentication: raises UnauthorizedAccessError if user is None or not authenticated.
    - NORMAL_USER: Raises ForbiddenRoleError (normal users cannot access organization requirements).
    - ORGANIZATION:
        * Resolves organization category strictly from PostgreSQL.
        * Rejects browser/widget category manipulation: raises CategoryTamperingError if mismatch.
        * Server/database-side queries strictly by PostgreSQL stored category.
        * Does NOT retrieve all requirements or filter on the client.
    - ADMIN: Allowed to access all platform requirements (or filtered by category).
    """
    from services.auth_service import (
        normalize_role,
        ROLE_NORMAL_USER,
        ROLE_ORGANIZATION,
        ROLE_ADMIN,
        UnauthorizedAccessError,
        ForbiddenRoleError,
        CategoryTamperingError,
    )

    if not user or not user.get("id"):
        raise UnauthorizedAccessError("Authentication required to access organization requirements.")

    role = normalize_role(user.get("role"))

    # 1. Normal User check
    if role == ROLE_NORMAL_USER:
        raise ForbiddenRoleError("Access denied: Normal users cannot access organization requirements.")

    # 2. Organization check
    if role == ROLE_ORGANIZATION:
        org_id = user.get("organization_id")
        if not org_id:
            raise ForbiddenRoleError("Access denied: Organization account is not linked to any valid organization.")

        with get_db() as db:
            org = db.query(Organization).filter_by(id=org_id).first()
            if not org:
                raise ForbiddenRoleError(f"Organization ID {org_id} does not exist.")

            stored_cat_id = org.category_id

            # Parameter manipulation / browser tampering detection
            if requested_category is not None:
                resolved_cat_id = None
                if isinstance(requested_category, int) or (isinstance(requested_category, str) and str(requested_category).isdigit()):
                    resolved_cat_id = int(requested_category)
                else:
                    norm = normalize_category_name(str(requested_category))
                    cat_obj = db.query(Category).filter_by(name=norm).first()
                    if cat_obj:
                        resolved_cat_id = cat_obj.id

                if resolved_cat_id is not None and resolved_cat_id != stored_cat_id:
                    logger.warning(
                        "SECURITY ALERT: Attempted category manipulation detected! Org %s (Category %s) attempted to access Category %s.",
                        org_id, stored_cat_id, requested_category
                    )
                    raise CategoryTamperingError(
                        f"Category manipulation blocked: Organization is locked to category {stored_cat_id} in PostgreSQL."
                    )

            # Query ONLY matching category directly in PostgreSQL (never filter in UI/memory)
            reqs = (
                db.query(Requirement)
                .filter(Requirement.category_id == stored_cat_id)
                .order_by(Requirement.created_at.desc(), Requirement.id.desc())
                .all()
            )
            return [_requirement_to_dict(r) for r in reqs]

    # 3. Admin check
    if role == ROLE_ADMIN:
        if requested_category is not None:
            resolved = resolve_controlled_category(requested_category)
            if resolved:
                return get_requirements_by_category(resolved.id)
        return get_all_requirements_for_admin()

    raise ForbiddenRoleError(f"Role '{user.get('role')}' is not authorized.")


def get_user_requirements(
    user_id: Optional[int] = None,
    mobile: Optional[str] = None,
    lead_id: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """
    Core business logic: Normal users can optionally track their own submissions.
    A normal user CANNOT see other users' requirements.
    """
    try:
        with get_db() as db:
            query = db.query(Requirement)
            if user_id:
                query = query.filter(Requirement.user_id == user_id)
            elif mobile:
                clean_mobile = str(mobile).strip()
                if not clean_mobile:
                    return []
                query = query.filter(Requirement.mobile == clean_mobile)
            elif lead_id:
                clean_lead_id = str(lead_id).strip()
                if not clean_lead_id:
                    return []
                query = query.filter(Requirement.lead_id == clean_lead_id)
            else:
                return []

            reqs = query.order_by(Requirement.created_at.desc()).all()
            return [_requirement_to_dict(r) for r in reqs]
    except Exception as exc:
        logger.error("Failed to fetch user requirements: %s", exc)
        return []


VALID_REQUIREMENT_STATUSES = ("New", "Claimed", "In Progress", "Completed", "Cancelled")


def mask_contact_info(contact: Optional[str]) -> str:
    """
    Masks sensitive contact information (phone number or email) for privacy.
    Prevents exposing sensitive customer details unnecessarily on public/summary views.
    Examples:
      - 9820099887 -> 98****9887
      - customer@example.com -> cu***@example.com
    """
    if not contact:
        return "—"
    s = str(contact).strip()
    if "@" in s:
        parts = s.split("@", 1)
        name, domain = parts[0], parts[1]
        if len(name) <= 2:
            return f"{name[0]}*@{domain}"
        return f"{name[:2]}***@{domain}"
    digits = re.sub(r"[^\d]", "", s)
    if len(digits) == 10:
        return f"{digits[:2]}****{digits[-4:]}"
    elif len(s) > 4:
        return f"{s[:2]}****{s[-2:]}"
    return "****"


def update_requirement_status(
    lead_id: str,
    new_status: str,
    organization_id: Optional[int] = None,
) -> Tuple[bool, str, Optional[Dict[str, Any]]]:
    """
    Updates the status of a requirement in PostgreSQL.
    Enforces Phase 5 business logic:
    1. If organization_id is provided, the requirement MUST belong to the organization's registered category in PostgreSQL.
    2. An organization CANNOT modify requirements belonging to another category.
    3. Status must be one of VALID_REQUIREMENT_STATUSES.
    """
    clean_lead_id = str(lead_id or "").strip()
    if not clean_lead_id:
        return False, "Lead ID is required.", None

    clean_status = str(new_status or "").strip()
    if clean_status not in VALID_REQUIREMENT_STATUSES:
        return False, f"Invalid status '{clean_status}'. Allowed statuses: {', '.join(VALID_REQUIREMENT_STATUSES)}.", None

    try:
        with get_db() as db:
            req = db.query(Requirement).filter_by(lead_id=clean_lead_id).first()
            if not req:
                return False, f"Requirement with Lead ID '{clean_lead_id}' not found.", None

            # Enforce organization category authorization
            if organization_id is not None:
                org = db.query(Organization).filter_by(id=organization_id).first()
                if not org:
                    return False, f"Organization ID {organization_id} does not exist.", None

                if req.category_id != org.category_id:
                    logger.warning(
                        "SECURITY ALERT: Organization %s (Category %s) attempted to update status of requirement %s (Category %s).",
                        organization_id, org.category_id, clean_lead_id, req.category_id
                    )
                    return False, "Unauthorized: An organization can only update requirements matching its registered category.", None

            req.status = clean_status
            req.updated_at = get_utc_now()
            db.flush()

            updated_dict = _requirement_to_dict(req)
            logger.info("Successfully updated status of %s to '%s' (org_id=%s)", clean_lead_id, clean_status, organization_id)
            return True, f"Requirement '{clean_lead_id}' status updated to '{clean_status}'.", updated_dict

    except Exception as exc:
        logger.error("Failed to update status for requirement %s: %s", clean_lead_id, exc)
        return False, f"Database error updating status: {exc}", None


def get_all_organizations_with_categories() -> List[Dict[str, Any]]:
    """Admin feature: view all registered organizations and their category."""
    try:
        with get_db() as db:
            orgs = db.query(Organization).order_by(Organization.id.asc()).all()
            return [
                {
                    "id": o.id,
                    "organization_name": o.organization_name,
                    "slug": o.slug,
                    "email": o.email,
                    "phone": o.phone,
                    "category_id": o.category_id,
                    "category_name": o.category.name if o.category else None,
                    "category_display": o.category.display_name if o.category else None,
                    "status": o.status,
                    "created_at": o.created_at.strftime("%Y-%m-%d %H:%M:%S") if o.created_at else "",
                }
                for o in orgs
            ]
    except Exception as exc:
        logger.error("Failed to query organizations for admin: %s", exc)
        return []


def get_all_requirements_for_admin() -> List[Dict[str, Any]]:
    """Admin feature: view all requirements across all categories."""
    try:
        with get_db() as db:
            reqs = db.query(Requirement).order_by(Requirement.created_at.desc()).all()
            return [_requirement_to_dict(r) for r in reqs]
    except Exception as exc:
        logger.error("Failed to query all requirements for admin: %s", exc)
        return []


def get_all_requirements_for_export(
    organization_id: Optional[int] = None,
    category_id: Optional[int] = None,
) -> Dict[str, List[Dict[str, Any]]]:
    """
    Retrieves requirements from PostgreSQL partitioned for Excel worksheet generation.
    If organization_id is provided, filters strictly by the organization's category.
    If category_id is provided, filters strictly by that category.
    If neither (Admin), exports across all categories.
    """
    resolved_cat_id = category_id
    if resolved_cat_id is None and organization_id:
        try:
            with get_db() as db:
                org = db.query(Organization).filter_by(id=organization_id).first()
                if org:
                    resolved_cat_id = org.category_id
        except Exception:
            pass

    data: Dict[str, List[Dict[str, Any]]] = {
        "All Leads": [],
        "Cook": [],
        "Driver": [],
        "Security Guard": [],
    }

    try:
        with get_db() as db:
            query = db.query(Requirement)
            if resolved_cat_id:
                query = query.filter(Requirement.category_id == resolved_cat_id)

            reqs = query.order_by(Requirement.id.asc()).all()

            for req in reqs:
                dt_str = req.created_at.strftime("%Y-%m-%d %H:%M:%S")
                date_str = req.start_date.strftime("%Y-%m-%d") if req.start_date else ""

                # Summary sheet entry
                data["All Leads"].append({
                    "Lead ID": req.lead_id,
                    "Date Time": dt_str,
                    "Name": req.name,
                    "Mobile": req.mobile,
                    "Service Type": req.service_type,
                    "City": req.city,
                    "Budget": req.budget,
                    "Status": req.status,
                })

                # Base detail entry
                base_detail = {
                    "Lead ID": req.lead_id,
                    "Date Time": dt_str,
                    "Name": req.name,
                    "Mobile": req.mobile,
                    "Email": req.email or "",
                    "Address": req.address or "",
                    "City": req.city,
                    "State": req.state or "",
                    "Pincode": req.pincode or "",
                    "Start Date": date_str,
                    "Preferred Timing": req.preferred_timing or "",
                    "Budget": req.budget,
                    "Additional Notes": req.additional_notes or "",
                    "Status": req.status,
                }

                if req.service_type == "Cook":
                    cook_entry = dict(base_detail)
                    cook_entry["Cuisine Type"] = req.cook_requirement.cuisine_type if req.cook_requirement else ""
                    cook_entry["Meals Per Day"] = req.cook_requirement.meals_per_day if req.cook_requirement else ""
                    data["Cook"].append(cook_entry)

                elif req.service_type == "Driver":
                    driver_entry = dict(base_detail)
                    driver_entry["Vehicle Type"] = req.driver_requirement.vehicle_type if req.driver_requirement else ""
                    driver_entry["License Required"] = req.driver_requirement.license_required if req.driver_requirement else ""
                    data["Driver"].append(driver_entry)

                elif req.service_type == "Security Guard":
                    guard_entry = dict(base_detail)
                    guard_entry["Day/Night Shift"] = req.security_guard_requirement.shift if req.security_guard_requirement else ""
                    guard_entry["Residential/Commercial"] = req.security_guard_requirement.site_type if req.security_guard_requirement else ""
                    data["Security Guard"].append(guard_entry)

    except Exception as exc:
        logger.error("Failed to fetch requirements for export: %s", exc)

    return data


# Compatibility alias
get_all_leads_for_export = get_all_requirements_for_export

