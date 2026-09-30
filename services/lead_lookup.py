"""
Lead / Requirement lookup service.
Queries PostgreSQL database for customer requirements strictly from PostgreSQL.
"""
from typing import Optional, Dict, Any
from database.repository import get_latest_lead_by_mobile
from services.tenant_service import get_current_tenant


def find_lead_by_mobile(
    mobile: str,
    organization_id: Optional[int] = None,
    category_id: Optional[int] = None,
) -> Optional[Dict[str, Any]]:
    """
    Queries PostgreSQL for the most recent requirement matching the given mobile number.
    If an organization context is provided, filters strictly by that organization's category.
    For normal users and public lookups, searches by mobile number without forcing an organization filter.
    """
    clean_mobile = str(mobile or "").strip()
    if not clean_mobile:
        return None

    org_id = organization_id
    if org_id is None and category_id is None:
        try:
            from services.auth_service import get_current_user
            user = get_current_user()
            if user and user.get("role") == "organization" and user.get("organization_id"):
                org_id = user["organization_id"]
        except Exception:
            pass

    return get_latest_lead_by_mobile(
        clean_mobile,
        organization_id=org_id,
        category_id=category_id,
    )