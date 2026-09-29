"""
Tenant context management service.
Provides tenant discovery, active tenant resolution, and session tenant switching.
"""
from typing import Optional, Dict, Any, List
import logging
from database.connection import get_db
from database.models import Organization

logger = logging.getLogger(__name__)

DEFAULT_TENANT_SLUG = "homedesk"


def get_all_tenants() -> List[Dict[str, Any]]:
    """Retrieves all registered tenant organizations from the database."""
    try:
        with get_db() as db:
            orgs = db.query(Organization).order_by(Organization.id.asc()).all()
            return [{"id": o.id, "name": o.name, "slug": o.slug} for o in orgs]
    except Exception as exc:
        logger.error("Failed to fetch tenants: %s", exc)
        return [{"id": 1, "name": "HomeDesk Primary", "slug": DEFAULT_TENANT_SLUG}]


def get_tenant_by_slug(slug: str) -> Optional[Dict[str, Any]]:
    """Finds an organization by slug."""
    if not slug:
        return None
    try:
        with get_db() as db:
            org = db.query(Organization).filter_by(slug=slug.strip().lower()).first()
            if org:
                return {"id": org.id, "name": org.name, "slug": org.slug}
    except Exception as exc:
        logger.error("Failed to lookup tenant by slug '%s': %s", slug, exc)
    return None


def get_tenant_by_id(tenant_id: int) -> Optional[Dict[str, Any]]:
    """Finds an organization by ID."""
    if not tenant_id:
        return None
    try:
        with get_db() as db:
            org = db.query(Organization).filter_by(id=tenant_id).first()
            if org:
                return {"id": org.id, "name": org.name, "slug": org.slug}
    except Exception as exc:
        logger.error("Failed to lookup tenant by id %s: %s", tenant_id, exc)
    return None


def get_default_tenant() -> Dict[str, Any]:
    """Returns the default platform tenant."""
    tenant = get_tenant_by_slug(DEFAULT_TENANT_SLUG)
    if tenant:
        return tenant
    tenants = get_all_tenants()
    if tenants:
        return tenants[0]
    return {"id": 1, "name": "HomeDesk Primary", "slug": DEFAULT_TENANT_SLUG}


def get_current_tenant() -> Dict[str, Any]:
    """
    Resolves the currently active tenant.
    SECURITY RULE: If a user is authenticated, their bound organization ALWAYS determines
    the tenant context. Query parameters or manual tampering cannot override this.
    For unauthenticated/guest contexts, query parameters and defaults are used.
    Safe to invoke both inside and outside of Streamlit runtime.
    """
    try:
        import streamlit as st

        # 1. Authenticated user check: Org is locked to user's bound organization
        if st.session_state.get("authenticated") is True and st.session_state.get("user"):
            user = st.session_state["user"]
            org_id = user.get("organization_id")
            if org_id:
                tenant = get_tenant_by_id(org_id)
                if tenant:
                    st.session_state["current_tenant_id"] = tenant["id"]
                    st.session_state["current_tenant_slug"] = tenant["slug"]
                    if hasattr(st, "query_params") and st.query_params.get("tenant") != tenant["slug"]:
                        st.query_params["tenant"] = tenant["slug"]
                    return tenant

        # 2. Check query parameter (for pre-auth tenant selection/landing)
        query_tenant = None
        if hasattr(st, "query_params"):
            query_tenant = st.query_params.get("tenant") or st.query_params.get("org")

        if query_tenant:
            tenant = get_tenant_by_slug(str(query_tenant).strip())
            if tenant:
                st.session_state["current_tenant_id"] = tenant["id"]
                st.session_state["current_tenant_slug"] = tenant["slug"]
                return tenant

        # 3. Check session state
        active_id = st.session_state.get("current_tenant_id")
        if active_id:
            tenant = get_tenant_by_id(active_id)
            if tenant:
                return tenant

        active_slug = st.session_state.get("current_tenant_slug")
        if active_slug:
            tenant = get_tenant_by_slug(active_slug)
            if tenant:
                st.session_state["current_tenant_id"] = tenant["id"]
                return tenant

        # 4. Default tenant fallback
        default_tenant = get_default_tenant()
        st.session_state["current_tenant_id"] = default_tenant["id"]
        st.session_state["current_tenant_slug"] = default_tenant["slug"]
        return default_tenant

    except Exception:
        # Fallback for standalone/test execution outside Streamlit
        return get_default_tenant()


def set_current_tenant(tenant_id_or_slug: Any) -> Dict[str, Any]:
    """
    Switches the active tenant.
    SECURITY RULE: Authenticated users CANNOT switch to another organization's tenant context.
    """
    try:
        import streamlit as st
        # Prevent tenant switching if user is logged in
        if st.session_state.get("authenticated") is True and st.session_state.get("user"):
            user = st.session_state["user"]
            user_org_id = user.get("organization_id")
            user_tenant = get_tenant_by_id(user_org_id)
            if user_tenant:
                logger.warning(
                    "Blocked unauthorized attempt to change tenant by user %s to %s",
                    user.get("email"),
                    tenant_id_or_slug,
                )
                return user_tenant
    except Exception:
        pass

    tenant = None
    if isinstance(tenant_id_or_slug, int) or (isinstance(tenant_id_or_slug, str) and tenant_id_or_slug.isdigit()):
        tenant = get_tenant_by_id(int(tenant_id_or_slug))
    elif isinstance(tenant_id_or_slug, str):
        tenant = get_tenant_by_slug(tenant_id_or_slug)

    if not tenant:
        tenant = get_default_tenant()

    try:
        import streamlit as st
        st.session_state["current_tenant_id"] = tenant["id"]
        st.session_state["current_tenant_slug"] = tenant["slug"]
        if hasattr(st, "query_params"):
            st.query_params["tenant"] = tenant["slug"]
    except Exception:
        pass

    return tenant
