"""
Data repository layer for HomeDesk Facility Management Portal.
Enforces strict multi-tenant isolation at the data access layer.
Every query and write operation is scoped to an organization_id.
"""
from datetime import datetime, date, timezone
from typing import Optional, Dict, Any, List
import logging
from sqlalchemy import select, and_
from database.connection import get_db, engine, check_connection
from database.models import (
    Base,
    Organization,
    User,
    Lead,
    CookRequirement,
    DriverRequirement,
    SecurityGuardRequirement,
)

logger = logging.getLogger(__name__)

SERVICE_PREFIX_MAP = {
    "Cook": "Cook",
    "Driver": "Driver",
    "Security Guard": "Security",
}


def _resolve_tenant_id(organization_id: Optional[int]) -> int:
    """Helper to ensure a valid tenant ID is provided or resolved."""
    if organization_id is not None:
        try:
            val = int(organization_id)
            if val > 0:
                return val
        except (ValueError, TypeError):
            pass
        raise ValueError(f"Invalid organization_id: {organization_id}. Positive integer required.")

    try:
        from services.tenant_service import get_current_tenant
        tenant = get_current_tenant()
        if tenant and tenant.get("id"):
            return int(tenant["id"])
    except Exception:
        pass
    raise ValueError("organization_id is required to enforce tenant isolation")


def init_database() -> bool:
    """
    Initializes database tables and default multi-tenant organizations.
    Safe to call multiple times.
    """
    try:
        Base.metadata.create_all(bind=engine)
        with get_db() as db:
            # Seed default primary tenant
            org1 = db.query(Organization).filter_by(slug="homedesk").first()
            if not org1:
                org1 = Organization(name="HomeDesk Primary", slug="homedesk")
                db.add(org1)

            # Seed secondary tenant for testing isolation
            org2 = db.query(Organization).filter_by(slug="acme").first()
            if not org2:
                org2 = Organization(name="Acme Facilities Group", slug="acme")
                db.add(org2)
            db.flush()

            # Seed default admin user for Tenant 1 (HomeDesk)
            user1 = db.query(User).filter_by(email="admin@homedesk.com").first()
            if not user1:
                from services.auth_service import hash_password
                user1 = User(
                    organization_id=org1.id,
                    name="HomeDesk Admin",
                    mobile="9800000001",
                    email="admin@homedesk.com",
                    password_hash=hash_password("Password123!"),
                    role="admin",
                )
                db.add(user1)

            # Seed default admin user for Tenant 2 (Acme)
            user2 = db.query(User).filter_by(email="admin@acme.com").first()
            if not user2:
                from services.auth_service import hash_password
                user2 = User(
                    organization_id=org2.id,
                    name="Acme Admin",
                    mobile="9800000002",
                    email="admin@acme.com",
                    password_hash=hash_password("Password123!"),
                    role="admin",
                )
                db.add(user2)

        return True
    except Exception as exc:
        logger.error("Database initialization failed: %s", exc)
        return False


def generate_next_lead_id(service_name: str, organization_id: Optional[int] = None) -> str:
    """
    Generates the next sequential Lead ID for a service within a tenant's scope.
    Tenant isolation is enforced: IDs are scoped to the specific organization.
    """
    org_id = _resolve_tenant_id(organization_id)
    prefix = SERVICE_PREFIX_MAP.get(service_name, service_name)
    used_numbers = set()

    try:
        with get_db() as db:
            # Filter strictly by organization_id and service prefix
            leads = (
                db.query(Lead.lead_id)
                .filter(
                    and_(
                        Lead.organization_id == org_id,
                        Lead.lead_id.like(f"{prefix}-%"),
                    )
                )
                .all()
            )
            for (lid,) in leads:
                try:
                    num = int(str(lid).split("-")[-1])
                    used_numbers.add(num)
                except (ValueError, IndexError):
                    continue
    except Exception as exc:
        logger.warning("Could not query Lead IDs for tenant %s: %s", org_id, exc)

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


def save_lead_to_db(
    service_name: str,
    lead_data: Dict[str, Any],
    organization_id: Optional[int] = None,
) -> Dict[str, Any]:
    """
    Saves a lead and its service-specific details into PostgreSQL strictly scoped to a tenant.
    Enforces tenant association on the Lead and User records.
    """
    org_id = _resolve_tenant_id(organization_id)
    lead_id = lead_data.get("Lead ID") or generate_next_lead_id(service_name, org_id)
    name = (lead_data.get("Name") or "").strip()
    mobile = str(lead_data.get("Mobile") or lead_data.get("Mobile Number") or "").strip()
    email = (lead_data.get("Email") or "").strip() or None
    address = lead_data.get("Address")
    city = (lead_data.get("City") or "").strip()
    state = lead_data.get("State")
    pincode = str(lead_data.get("Pincode") or "").strip() or None
    start_date = _parse_date(lead_data.get("Start Date"))
    preferred_timing = lead_data.get("Preferred Timing")
    budget = float(lead_data.get("Budget") or lead_data.get("Budget (INR)") or 0.0)
    additional_notes = lead_data.get("Additional Notes")
    status = lead_data.get("Status") or "New"
    created_at = _parse_datetime(lead_data.get("Date Time"))

    with get_db() as db:
        # Verify tenant organization exists
        org = db.query(Organization).filter_by(id=org_id).first()
        if not org:
            raise ValueError(f"Organization with ID {org_id} does not exist.")

        # Attach authenticated user_id or resolve customer user
        user_id = lead_data.get("user_id")
        if not user_id:
            try:
                from services.auth_service import get_current_user
                curr = get_current_user()
                if curr and curr.get("organization_id") == org_id:
                    user_id = curr.get("id")
            except Exception:
                pass

        if not user_id and mobile:
            user = db.query(User).filter_by(organization_id=org_id, mobile=mobile).first()
            if not user and email:
                user = db.query(User).filter_by(organization_id=org_id, email=email).first()

            if not user:
                user_email = email
                if user_email and db.query(User).filter_by(email=user_email).first():
                    user_email = None  # Prevent unique email constraint collision
                user = User(
                    organization_id=org_id,
                    name=name or "Valued Customer",
                    mobile=mobile,
                    email=user_email,
                    role="customer",
                )
                db.add(user)
                db.flush()

            user_id = user.id if user else None

        # Create or update Lead strictly scoped to tenant
        lead = db.query(Lead).filter_by(organization_id=org_id, lead_id=lead_id).first()
        if not lead:
            lead = Lead(
                lead_id=lead_id,
                organization_id=org_id,
                user_id=user_id,
                service_type=service_name,
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
            db.add(lead)
            db.flush()

        # Service-specific requirements
        if service_name == "Cook":
            cuisine = lead_data.get("Cuisine Type")
            meals = lead_data.get("Meals Per Day")
            meals_int = int(meals) if meals is not None and str(meals).isdigit() else None

            if not lead.cook_requirement:
                lead.cook_requirement = CookRequirement(
                    cuisine_type=cuisine,
                    meals_per_day=meals_int,
                )
            else:
                lead.cook_requirement.cuisine_type = cuisine
                lead.cook_requirement.meals_per_day = meals_int

        elif service_name == "Driver":
            vehicle = lead_data.get("Vehicle Type")
            license_req = lead_data.get("License Required")

            if not lead.driver_requirement:
                lead.driver_requirement = DriverRequirement(
                    vehicle_type=vehicle,
                    license_required=license_req,
                )
            else:
                lead.driver_requirement.vehicle_type = vehicle
                lead.driver_requirement.license_required = license_req

        elif service_name == "Security Guard":
            shift = lead_data.get("Day/Night Shift")
            site = lead_data.get("Residential/Commercial")

            if not lead.security_guard_requirement:
                lead.security_guard_requirement = SecurityGuardRequirement(
                    shift=shift,
                    site_type=site,
                )
            else:
                lead.security_guard_requirement.shift = shift
                lead.security_guard_requirement.site_type = site

    lead_data["Lead ID"] = lead_id
    lead_data["Date Time"] = created_at.strftime("%Y-%m-%d %H:%M:%S")
    lead_data["Status"] = status
    lead_data["Organization ID"] = org_id
    return lead_data


def get_latest_lead_by_mobile(
    mobile: str,
    organization_id: Optional[int] = None,
) -> Optional[Dict[str, Any]]:
    """
    Finds the latest submitted lead for a given mobile number strictly within the specified tenant.
    Tenant isolation is enforced: records belonging to other tenants are NEVER returned.
    """
    org_id = _resolve_tenant_id(organization_id)
    mobile_clean = str(mobile or "").strip()
    if not mobile_clean:
        return None

    try:
        with get_db() as db:
            lead = (
                db.query(Lead)
                .filter(
                    and_(
                        Lead.organization_id == org_id,
                        Lead.mobile == mobile_clean,
                    )
                )
                .order_by(Lead.created_at.desc(), Lead.id.desc())
                .first()
            )
            if not lead:
                return None

            result: Dict[str, Any] = {
                "Lead ID": lead.lead_id,
                "Organization ID": lead.organization_id,
                "Service": lead.service_type,
                "Service Type": lead.service_type,
                "Name": lead.name,
                "Mobile": lead.mobile,
                "Email": lead.email or "",
                "Address": lead.address or "",
                "City": lead.city,
                "State": lead.state or "",
                "Pincode": lead.pincode or "",
                "Start Date": lead.start_date.strftime("%Y-%m-%d") if lead.start_date else "",
                "Preferred Timing": lead.preferred_timing or "",
                "Budget": lead.budget,
                "Status": lead.status,
                "Date Time": lead.created_at.strftime("%Y-%m-%d %H:%M:%S"),
                "Additional Notes": lead.additional_notes or "",
            }

            if lead.service_type == "Cook" and lead.cook_requirement:
                result["Cuisine Type"] = lead.cook_requirement.cuisine_type or ""
                result["Meals Per Day"] = lead.cook_requirement.meals_per_day

            elif lead.service_type == "Driver" and lead.driver_requirement:
                result["Vehicle Type"] = lead.driver_requirement.vehicle_type or ""
                result["License Required"] = lead.driver_requirement.license_required or ""

            elif lead.service_type == "Security Guard" and lead.security_guard_requirement:
                result["Day/Night Shift"] = lead.security_guard_requirement.shift or ""
                result["Residential/Commercial"] = lead.security_guard_requirement.site_type or ""

            return result

    except Exception as exc:
        logger.error("Failed to query lead by mobile for tenant %s: %s", org_id, exc)
        return None


def get_lead_by_id(
    lead_id: str,
    organization_id: Optional[int] = None,
) -> Optional[Dict[str, Any]]:
    """
    Finds a lead by its Lead ID strictly within the specified tenant.
    Tenant isolation is enforced: Lead IDs belonging to other tenants are inaccessible.
    """
    org_id = _resolve_tenant_id(organization_id)
    if not lead_id:
        return None

    try:
        with get_db() as db:
            lead = (
                db.query(Lead)
                .filter(
                    and_(
                        Lead.organization_id == org_id,
                        Lead.lead_id == lead_id.strip(),
                    )
                )
                .first()
            )
            if not lead:
                return None

            result: Dict[str, Any] = {
                "Lead ID": lead.lead_id,
                "Organization ID": lead.organization_id,
                "Service": lead.service_type,
                "Service Type": lead.service_type,
                "Name": lead.name,
                "Mobile": lead.mobile,
                "Email": lead.email or "",
                "Address": lead.address or "",
                "City": lead.city,
                "State": lead.state or "",
                "Pincode": lead.pincode or "",
                "Start Date": lead.start_date.strftime("%Y-%m-%d") if lead.start_date else "",
                "Preferred Timing": lead.preferred_timing or "",
                "Budget": lead.budget,
                "Status": lead.status,
                "Date Time": lead.created_at.strftime("%Y-%m-%d %H:%M:%S"),
                "Additional Notes": lead.additional_notes or "",
            }
            return result
    except Exception as exc:
        logger.error("Failed to query lead by id for tenant %s: %s", org_id, exc)
        return None


def get_all_leads_for_export(organization_id: Optional[int] = None) -> Dict[str, List[Dict[str, Any]]]:
    """
    Retrieves all leads strictly for the given tenant partitioned by worksheet structure.
    Tenant isolation is enforced: leads belonging to other tenants are NEVER included in export.
    """
    org_id = _resolve_tenant_id(organization_id)
    data: Dict[str, List[Dict[str, Any]]] = {
        "All Leads": [],
        "Cook": [],
        "Driver": [],
        "Security Guard": [],
    }

    try:
        with get_db() as db:
            leads = (
                db.query(Lead)
                .filter(Lead.organization_id == org_id)
                .order_by(Lead.id.asc())
                .all()
            )

            for lead in leads:
                dt_str = lead.created_at.strftime("%Y-%m-%d %H:%M:%S")
                date_str = lead.start_date.strftime("%Y-%m-%d") if lead.start_date else ""

                # Summary sheet entry
                data["All Leads"].append({
                    "Lead ID": lead.lead_id,
                    "Date Time": dt_str,
                    "Name": lead.name,
                    "Mobile": lead.mobile,
                    "Service Type": lead.service_type,
                    "City": lead.city,
                    "Budget": lead.budget,
                    "Status": lead.status,
                })

                # Base detail entry
                base_detail = {
                    "Lead ID": lead.lead_id,
                    "Date Time": dt_str,
                    "Name": lead.name,
                    "Mobile": lead.mobile,
                    "Email": lead.email or "",
                    "Address": lead.address or "",
                    "City": lead.city,
                    "State": lead.state or "",
                    "Pincode": lead.pincode or "",
                    "Start Date": date_str,
                    "Preferred Timing": lead.preferred_timing or "",
                    "Budget": lead.budget,
                    "Additional Notes": lead.additional_notes or "",
                    "Status": lead.status,
                }

                if lead.service_type == "Cook":
                    cook_entry = dict(base_detail)
                    cook_entry["Cuisine Type"] = lead.cook_requirement.cuisine_type if lead.cook_requirement else ""
                    cook_entry["Meals Per Day"] = lead.cook_requirement.meals_per_day if lead.cook_requirement else ""
                    data["Cook"].append(cook_entry)

                elif lead.service_type == "Driver":
                    driver_entry = dict(base_detail)
                    driver_entry["Vehicle Type"] = lead.driver_requirement.vehicle_type if lead.driver_requirement else ""
                    driver_entry["License Required"] = lead.driver_requirement.license_required if lead.driver_requirement else ""
                    data["Driver"].append(driver_entry)

                elif lead.service_type == "Security Guard":
                    guard_entry = dict(base_detail)
                    guard_entry["Day/Night Shift"] = lead.security_guard_requirement.shift if lead.security_guard_requirement else ""
                    guard_entry["Residential/Commercial"] = lead.security_guard_requirement.site_type if lead.security_guard_requirement else ""
                    data["Security Guard"].append(guard_entry)

    except Exception as exc:
        logger.error("Failed to fetch leads for export for tenant %s: %s", org_id, exc)

    return data
