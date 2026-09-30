"""
FastAPI Backend Application for HomeDesk Facility Management Portal.
Provides RESTful endpoints for the React frontend while utilizing the existing
multi-tenant PostgreSQL database layer, authentication system, and AI chatbot provider.
"""
from typing import Optional, Dict, Any, List
import logging
import os
from fastapi import FastAPI, HTTPException, Query, Depends, Response, status, Header
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from database.connection import check_connection, get_db
from database.repository import (
    init_database,
    get_controlled_categories,
    get_requirements_for_organization,
    get_user_requirements,
    get_all_organizations_with_categories,
    get_all_requirements_for_admin,
    update_requirement_status,
)
from database.models import Organization, Lead, Category
from services.tenant_service import (
    get_all_tenants,
    get_tenant_by_slug,
    get_tenant_by_id,
    get_default_tenant,
)
from services.auth_service import (
    register_user,
    authenticate_user,
    validate_password_strength,
    generate_auth_token,
    verify_auth_token,
    revoke_auth_token,
    normalize_role,
    ROLE_NORMAL_USER,
    ROLE_ORGANIZATION,
    ROLE_ADMIN,
    UnauthorizedAccessError,
    ForbiddenRoleError,
    CategoryTamperingError,
)
from services.lead_lookup import find_lead_by_mobile
from storage.excel_handler import (
    save_lead,
    get_excel_export_bytes,
)
from storage.serial_generator import generate_serial
from utils.validators import validate_form, validate_email
from ai.chatbot import ask_chatbot
from healthcheck import run_health_check

# Initialize logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("homedesk.api")

# Auto-initialize database tables and seeds on application start
try:
    init_database()
except Exception as _init_err:
    logger.warning("Database init on API startup warning: %s", _init_err)

app = FastAPI(
    title="HomeDesk Facility Management API",
    description="Backend API powering the HomeDesk Multi-Tenant React Frontend",
    version="1.0.0",
)

# Enable CORS for React frontend (Vite dev server and production origins)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# --- Pydantic Schemas ---

class RegisterRequest(BaseModel):
    name: str = Field(..., min_length=2)
    email: str = Field(..., min_length=5)
    mobile: str = Field(..., min_length=10, max_length=10)
    password: str = Field(..., min_length=8)
    organization_id: Optional[int] = None
    new_org_name: Optional[str] = None
    category_id: Optional[Any] = None
    category_name: Optional[str] = None
    role: Optional[str] = None


class LoginRequest(BaseModel):
    email: str = Field(..., min_length=5)
    password: str = Field(..., min_length=1)


class LeadSubmissionRequest(BaseModel):
    service_name: str
    organization_id: Optional[int] = None
    data: Dict[str, Any]


class ChatRequest(BaseModel):
    message: str


class UpdateStatusRequest(BaseModel):
    status: str


# --- Routes ---

@app.get("/api/health", tags=["Health"])
def health_endpoint():
    """Returns application health status, database connection, and AI provider status."""
    report = run_health_check()
    if report["status"] == "unhealthy":
        raise HTTPException(status_code=503, detail=report)
    return report


@app.get("/api/categories", tags=["Categories"])
def list_categories():
    """Returns controlled service categories (COOK, DRIVER, SECURITY_GUARD)."""
    return get_controlled_categories()


@app.get("/api/tenants", tags=["Tenants"])
def list_tenants():
    """Lists all tenant organizations for tenant switching and registration."""
    return get_all_tenants()


@app.get("/api/tenants/{slug_or_id}", tags=["Tenants"])
def get_tenant_details(slug_or_id: str):
    """Retrieves tenant info by slug or ID."""
    if slug_or_id.isdigit():
        tenant = get_tenant_by_id(int(slug_or_id))
    else:
        tenant = get_tenant_by_slug(slug_or_id)

    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant organization not found")
    return tenant


@app.post("/api/auth/register", tags=["Authentication"])
def register(payload: RegisterRequest):
    """Registers a new user and associates them with an existing or new organization."""
    success, msg, user_data = register_user(
        name=payload.name,
        email=payload.email,
        mobile=payload.mobile,
        password=payload.password,
        organization_id=payload.organization_id,
        new_org_name=payload.new_org_name,
        category_id=payload.category_id,
        category_name=payload.category_name,
        role=payload.role,
    )
    if not success:
        raise HTTPException(status_code=400, detail=msg)
    return {"message": msg, "user": user_data}


# --- Security Dependencies ---

def get_current_user_from_request(
    auth_header: Optional[str] = Header(None, alias="Authorization"),
    session_header: Optional[str] = Header(None, alias="X-Auth-Token"),
) -> Dict[str, Any]:
    """
    Extracts and validates signed session token from request headers.
    Returns decoded user payload or raises HTTP 401 Unauthorized.
    """
    token = auth_header or session_header
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required. Please provide a valid Authorization Bearer token.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    is_valid, payload, msg = verify_auth_token(token)
    if not is_valid or not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid or expired credentials: {msg}",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return payload


def require_organization_role(
    current_user: Dict[str, Any] = Depends(get_current_user_from_request),
) -> Dict[str, Any]:
    """
    Enforces that caller is an authenticated Organization user (or Admin).
    Normal users are strictly forbidden with HTTP 403.
    """
    role = normalize_role(current_user.get("role"))
    if role not in (ROLE_ORGANIZATION, ROLE_ADMIN):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Forbidden: Organization credentials required to access this resource.",
        )
    return current_user


def require_admin_role(
    current_user: Dict[str, Any] = Depends(get_current_user_from_request),
) -> Dict[str, Any]:
    """
    Enforces that caller is an authenticated Platform Administrator.
    Normal users and organizations are strictly forbidden with HTTP 403.
    """
    role = normalize_role(current_user.get("role"))
    if role != ROLE_ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Forbidden: Platform Administrator credentials required to access this resource.",
        )
    return current_user


@app.post("/api/auth/login", tags=["Authentication"])
def login(payload: LoginRequest):
    """Authenticates user credentials and returns user profile with signed session token."""
    success, msg, user_data = authenticate_user(
        email=payload.email,
        password=payload.password,
    )
    if not success:
        raise HTTPException(status_code=401, detail=msg)
    return {
        "message": msg,
        "user": user_data,
        "token": user_data.get("token") if user_data else None,
    }


@app.post("/api/auth/logout", tags=["Authentication"])
def logout(
    auth_header: Optional[str] = Header(None, alias="Authorization"),
    session_header: Optional[str] = Header(None, alias="X-Auth-Token"),
):
    """Revokes the current authentication token and invalidates the session."""
    token = auth_header or session_header
    if token:
        revoke_auth_token(token)
    return {"message": "Logged out successfully"}


@app.get("/api/auth/me", tags=["Authentication"])
def get_authenticated_profile(current_user: Dict[str, Any] = Depends(get_current_user_from_request)):
    """Returns the profile of the actively authenticated user."""
    return {"user": current_user}


@app.get("/api/organizations/{org_id}/requirements", tags=["Organizations"])
def get_org_requirements(
    org_id: int,
    category_id: Optional[int] = Query(None, description="Optional category parameter to test anti-tampering"),
    current_user: Dict[str, Any] = Depends(require_organization_role),
):
    """
    Retrieves requirements strictly matching the organization's registered category in PostgreSQL.
    Enforces RBAC:
    - Normal users: 403 Forbidden
    - Organization user: Can ONLY access their own organization's workspace
    - Attempted category manipulation: Strictly blocked with 403 Forbidden
    - Category filtering is executed server/database-side in PostgreSQL
    """
    user_role = normalize_role(current_user.get("role"))
    if user_role == ROLE_ORGANIZATION:
        user_org_id = current_user.get("organization_id")
        if user_org_id != org_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Forbidden: You cannot access organization ID {org_id}'s workspace.",
            )

    # Server-side validation against database-stored category
    with get_db() as db:
        org = db.query(Organization).filter_by(id=org_id).first()
        if not org:
            raise HTTPException(status_code=404, detail="Organization not found")
        if category_id is not None and int(category_id) != int(org.category_id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Forbidden: Attempted category manipulation detected. Access denied.",
            )

    reqs = get_requirements_for_organization(org_id, requested_category=category_id)
    return reqs


@app.patch("/api/organizations/{org_id}/requirements/{lead_id}/status", tags=["Organizations"])
def update_org_requirement_status_endpoint(
    org_id: int,
    lead_id: str,
    payload: UpdateStatusRequest,
    current_user: Dict[str, Any] = Depends(require_organization_role),
):
    """
    Updates status of a requirement within the organization's registered category.
    Enforces RBAC:
    - Normal users: 403 Forbidden
    - Organization user: Can ONLY modify their own organization's category requirements
    - Rejects cross-category manipulation
    """
    user_role = normalize_role(current_user.get("role"))
    if user_role == ROLE_ORGANIZATION:
        user_org_id = current_user.get("organization_id")
        if user_org_id != org_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Forbidden: You cannot modify organization ID {org_id}'s requirements.",
            )

    success, msg, updated = update_requirement_status(
        lead_id=lead_id,
        new_status=payload.status,
        organization_id=org_id if user_role == ROLE_ORGANIZATION else None,
    )
    if not success:
        if "Unauthorized" in msg:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=msg)
        elif "not found" in msg:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=msg)
        else:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=msg)

    return {"message": msg, "requirement": updated}


@app.get("/api/admin/overview", tags=["Admin"])
def admin_overview(current_user: Dict[str, Any] = Depends(require_admin_role)):
    """
    Platform-wide management: all categories, all organizations, and all requirements.
    Protected: Only platform administrators are authorized.
    """
    return {
        "categories": get_controlled_categories(),
        "organizations": get_all_organizations_with_categories(),
        "requirements": get_all_requirements_for_admin(),
    }


@app.get("/api/users/{user_id}/requirements", tags=["Users"])
def user_requirements(
    user_id: int,
    current_user: Dict[str, Any] = Depends(get_current_user_from_request),
):
    """
    Normal user can view only their own submitted requirements.
    Organizations cannot access user submission tracking.
    Users cannot view other users' submissions.
    """
    role = normalize_role(current_user.get("role"))
    if role == ROLE_ORGANIZATION:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Forbidden: Organizations cannot access customer submission tracking.",
        )
    if role == ROLE_NORMAL_USER and current_user.get("user_id") != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Forbidden: You cannot view other users' submissions.",
        )
    return get_user_requirements(user_id=user_id)


@app.get("/api/leads/lookup", tags=["Leads"])
def lookup_lead(
    mobile: str = Query(..., min_length=10, max_length=10, description="10-digit mobile number"),
    organization_id: int = Query(..., description="Tenant organization ID"),
):
    """Looks up the most recent requirement submitted for a mobile number within a tenant."""
    lead = find_lead_by_mobile(mobile.strip(), organization_id=organization_id)
    if not lead:
        raise HTTPException(status_code=404, detail="No request found for this mobile number in this organization.")
    return lead


@app.post("/api/leads", tags=["Leads"], status_code=status.HTTP_201_CREATED)
def submit_lead(payload: LeadSubmissionRequest):
    """
    Submits a requirement (Cook, Driver, or Security Guard), validates inputs,
    generates a sequential Lead ID, and persists to PostgreSQL with tenant isolation.
    """
    service = payload.service_name
    lead_data = payload.data
    org_id = payload.organization_id

    # 1. Input Validation
    errors = validate_form(lead_data)
    if errors:
        raise HTTPException(status_code=422, detail={"errors": errors})

    # 2. Sequential Lead ID Generation
    try:
        lead_id = generate_serial(service, organization_id=org_id)
        lead_data["Lead ID"] = lead_id
    except Exception as exc:
        logger.error("Failed to generate lead serial: %s", exc)
        lead_data["Lead ID"] = f"{service[:4]}-999"

    # 3. Save to database
    try:
        saved = save_lead(service, lead_data, organization_id=org_id)
        return {
            "message": "Requirement submitted successfully",
            "lead": saved,
        }
    except Exception as exc:
        logger.error("Failed to save lead: %s", exc)
        raise HTTPException(status_code=500, detail="Failed to save requirement to database")


@app.get("/api/leads/export", tags=["Reporting"])
def export_leads_excel(organization_id: int = Query(..., description="Tenant ID")):
    """Generates and downloads an Excel export (.xlsx) strictly for the requested tenant."""
    try:
        excel_bytes = get_excel_export_bytes(organization_id=organization_id)
        tenant = get_tenant_by_id(organization_id) or {"slug": "homedesk"}
        filename = f"{tenant.get('slug', 'leads')}_export.xlsx"

        return Response(
            content=excel_bytes,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={"Content-Disposition": f"attachment; filename={filename}"},
        )
    except Exception as exc:
        logger.error("Export error: %s", exc)
        raise HTTPException(status_code=500, detail="Failed to generate Excel export")


@app.post("/api/chat", tags=["AI Chatbot"])
def chat_with_assistant(payload: ChatRequest):
    """Invokes the cloud AI provider assistant with domain knowledge and system prompt."""
    if not payload.message or not payload.message.strip():
        raise HTTPException(status_code=400, detail="Message cannot be empty")
    reply = ask_chatbot(payload.message.strip())
    return {"reply": reply}


# Mount built React single-page frontend if available
_frontend_dist = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "frontend", "dist")
if os.path.exists(_frontend_dist):
    app.mount("/", StaticFiles(directory=_frontend_dist, html=True), name="frontend")

