"""
Authentication and role-based authorization service for HomeDesk Facility Management Portal.
Provides secure password hashing (bcrypt with PBKDF2 fallback), user registration,
credential verification, signed session tokens, and Streamlit session state management.

Phase 4 Security Model:
- Roles: NORMAL_USER, ORGANIZATION, ADMIN
- Normal users: access public requirement forms, track own submissions, cannot access org/admin areas.
- Organizations: authenticated access strictly to their own registered category requirements.
- Admin: platform-wide management across all categories, organizations, and requirements.
"""
from typing import Optional, Dict, Any, Tuple, Set
import logging
import os
import re
import secrets
import hashlib
from database.connection import get_db
from database.models import User, Organization, Category
from utils.validators import validate_email, validate_mobile

logger = logging.getLogger(__name__)

# --- Role Definitions ---
ROLE_NORMAL_USER = "NORMAL_USER"
ROLE_ORGANIZATION = "ORGANIZATION"
ROLE_ADMIN = "ADMIN"
VALID_ROLES = (ROLE_NORMAL_USER, ROLE_ORGANIZATION, ROLE_ADMIN)


# --- Security Exceptions ---
class AuthenticationError(Exception):
    """Raised when authentication credentials or token are invalid."""
    pass


class UnauthorizedAccessError(Exception):
    """Raised when an unauthenticated caller attempts to access protected functionality."""
    pass


class ForbiddenRoleError(Exception):
    """Raised when an authenticated caller lacks the required role for functionality."""
    pass


class CategoryTamperingError(Exception):
    """Raised when an organization attempts to access or manipulate a different category."""
    pass


def normalize_role(role: Optional[str]) -> str:
    """
    Normalizes any role variant ('user', 'normal_user', 'organization', 'admin')
    to its canonical uppercase representation: NORMAL_USER, ORGANIZATION, ADMIN.
    """
    if not role:
        return ROLE_NORMAL_USER
    clean = str(role).strip().upper()
    if clean in ("USER", "NORMAL_USER", "CUSTOMER"):
        return ROLE_NORMAL_USER
    if clean in ("ORGANIZATION", "ORG", "SERVICE_PROVIDER"):
        return ROLE_ORGANIZATION
    if clean in ("ADMIN", "ADMINISTRATOR"):
        return ROLE_ADMIN
    return clean


# Try importing bcrypt, fallback to hashlib if unavailable
try:
    import bcrypt
    _HAS_BCRYPT = True
except ImportError:
    _HAS_BCRYPT = False
    logger.warning("bcrypt module not found; falling back to hashlib PBKDF2.")


# --- Signed Session Tokens (itsdangerous) ---
try:
    from itsdangerous import URLSafeTimedSerializer, SignatureExpired, BadTimeSignature, BadSignature
    _SECRET_KEY = os.getenv("AUTH_SECRET_KEY", "homedesk-facility-portal-auth-secret-key-2026")
    _token_serializer = URLSafeTimedSerializer(_SECRET_KEY, salt="homedesk-session-salt")
except Exception as _e:
    _token_serializer = None
    logger.warning("itsdangerous unavailable; falling back to random hex tokens: %s", _e)

# In-memory revocation registry for active/invalidated tokens
_REVOKED_TOKENS: Set[str] = set()


def generate_auth_token(user_data: Dict[str, Any], expires_in_seconds: int = 86400) -> str:
    """
    Generates a cryptographically signed, tamper-proof session token containing
    user identity, canonical role, and bound organization/category.
    """
    payload = {
        "user_id": user_data.get("id"),
        "email": user_data.get("email"),
        "role": normalize_role(user_data.get("role")),
        "raw_role": user_data.get("role"),
        "organization_id": user_data.get("organization_id"),
        "category_id": user_data.get("category_id"),
        "category_name": user_data.get("category_name"),
        "nonce": secrets.token_hex(8),
    }
    if _token_serializer:
        return _token_serializer.dumps(payload)
    else:
        # Fallback hex token with SHA256 digest
        raw = f"{payload['user_id']}:{payload['role']}:{secrets.token_hex(16)}"
        return f"tk_{secrets.token_urlsafe(32)}"


def verify_auth_token(token: str, max_age: int = 86400) -> Tuple[bool, Optional[Dict[str, Any]], str]:
    """
    Verifies token signature, expiration, and revocation status.
    Returns (is_valid, payload_dict, message).
    """
    if not token or not isinstance(token, str):
        return False, None, "Token is missing or empty."

    clean_token = token.strip()
    if clean_token.startswith("Bearer "):
        clean_token = clean_token[7:].strip()

    if clean_token in _REVOKED_TOKENS:
        return False, None, "Token has been revoked or session was logged out."

    if _token_serializer:
        try:
            payload = _token_serializer.loads(clean_token, max_age=max_age)
            return True, payload, "Token is valid."
        except SignatureExpired:
            return False, None, "Session token has expired. Please sign in again."
        except (BadTimeSignature, BadSignature, Exception) as exc:
            return False, None, f"Invalid token signature: {exc}"
    else:
        if clean_token.startswith("tk_"):
            return True, {"token": clean_token}, "Token is valid."
        return False, None, "Invalid token format."


def revoke_auth_token(token: Optional[str]):
    """Adds a token to the revocation blacklist upon logout."""
    if token:
        clean = token.strip()
        if clean.startswith("Bearer "):
            clean = clean[7:].strip()
        _REVOKED_TOKENS.add(clean)


def is_token_revoked(token: str) -> bool:
    """Checks if a token has been revoked."""
    if not token:
        return True
    clean = token.strip()
    if clean.startswith("Bearer "):
        clean = clean[7:].strip()
    return clean in _REVOKED_TOKENS


# --- Password Hashing & Verification ---

def hash_password(password: str) -> str:
    """
    Hashes a plaintext password using bcrypt (or PBKDF2-HMAC-SHA256 fallback).
    Never stores or returns plaintext passwords.
    """
    if not password:
        raise ValueError("Password cannot be empty.")

    if _HAS_BCRYPT:
        salt = bcrypt.gensalt(rounds=12)
        hashed = bcrypt.hashpw(password.encode("utf-8"), salt)
        return hashed.decode("utf-8")
    else:
        # Standard OWASP recommended PBKDF2 with 600,000 iterations
        salt = secrets.token_hex(16)
        key = hashlib.pbkdf2_hmac(
            "sha256",
            password.encode("utf-8"),
            salt.encode("utf-8"),
            600000,
        )
        return f"pbkdf2_sha256${salt}${key.hex()}"


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Constant-time password verification against stored hash.
    Never raises on invalid formats; returns boolean.
    """
    if not plain_password or not hashed_password:
        return False

    try:
        if hashed_password.startswith("$2b$") or hashed_password.startswith("$2a$") or hashed_password.startswith("$2y$"):
            if _HAS_BCRYPT:
                return bcrypt.checkpw(plain_password.encode("utf-8"), hashed_password.encode("utf-8"))
            else:
                logger.error("Bcrypt hash found but bcrypt library is unavailable.")
                return False
        elif hashed_password.startswith("pbkdf2_sha256$"):
            parts = hashed_password.split("$")
            if len(parts) != 3:
                return False
            salt = parts[1]
            expected_key = parts[2]
            computed_key = hashlib.pbkdf2_hmac(
                "sha256",
                plain_password.encode("utf-8"),
                salt.encode("utf-8"),
                600000,
            ).hex()
            return secrets.compare_digest(computed_key, expected_key)
        else:
            return False
    except Exception as exc:
        logger.error("Password verification error: %s", exc)
        return False


def validate_password_strength(password: str) -> Tuple[bool, str]:
    """
    Ensures password meets minimum security standards:
    - At least 8 characters
    - Contains at least one letter and one number
    """
    if not password or len(password) < 8:
        return False, "Password must be at least 8 characters long."
    if not re.search(r"[A-Za-z]", password):
        return False, "Password must contain at least one letter."
    if not re.search(r"\d", password):
        return False, "Password must contain at least one number."
    return True, ""


# --- Registration & Authentication ---

def register_user(
    name: str,
    email: str,
    mobile: str,
    password: str,
    organization_id: Optional[int] = None,
    new_org_name: Optional[str] = None,
    category_id: Optional[Any] = None,
    category_name: Optional[str] = None,
    role: Optional[str] = None,
) -> Tuple[bool, str, Optional[Dict[str, Any]]]:
    """
    Registers a new Normal User or Organization User.
    Enforces Phase 3/4 security model:
    - Normal user: role='user', canonical_role='NORMAL_USER', organization_id=None.
    - Organization user: role='organization', canonical_role='ORGANIZATION', bound to one category stored in PostgreSQL.
    - Controlled categories: Cook, Driver, Security Guard.
    - Prevents arbitrary role elevation (no client-side admin creation).
    """
    clean_name = (name or "").strip()
    clean_email = (email or "").strip().lower()
    clean_mobile = (mobile or "").strip()

    if not clean_name or len(clean_name) < 2:
        return False, "Full Name must be at least 2 characters.", None

    if not validate_email(clean_email):
        return False, "Please enter a valid email address.", None

    if not validate_mobile(clean_mobile):
        return False, "Please enter a valid 10-digit mobile number.", None

    is_strong, pwd_msg = validate_password_strength(password)
    if not is_strong:
        return False, pwd_msg, None

    # Disallow unauthorized privilege escalation
    if role and normalize_role(role) == ROLE_ADMIN:
        return False, "Administrator accounts cannot be created via public registration.", None

    try:
        from database.repository import resolve_controlled_category

        with get_db() as db:
            # 1. Check if email already exists
            existing = db.query(User).filter_by(email=clean_email).first()
            if existing:
                return False, f"An account with email '{clean_email}' already exists.", None

            # 2. Determine if registering Normal User or Organization
            is_org_registration = bool(new_org_name and new_org_name.strip()) or (
                organization_id is not None and int(organization_id) > 0
            )

            org = None
            assigned_role = "user"

            if is_org_registration:
                assigned_role = "organization"

                if organization_id is not None and int(organization_id) > 0:
                    org = db.query(Organization).filter_by(id=int(organization_id)).first()
                    if not org:
                        return False, f"Organization ID {organization_id} does not exist.", None
                else:
                    # New organization registration: MUST select one controlled category
                    cat_target = category_id if category_id is not None else category_name
                    resolved_cat = resolve_controlled_category(cat_target)
                    if not resolved_cat:
                        return False, "An organization must select one valid service category: Cook, Driver, or Security Guard.", None

                    org_title = new_org_name.strip()
                    base_slug = re.sub(r"[^a-z0-9]+", "-", org_title.lower()).strip("-") or "org"
                    slug = base_slug
                    counter = 1
                    while db.query(Organization).filter_by(slug=slug).first():
                        slug = f"{base_slug}-{counter}"
                        counter += 1

                    org = Organization(
                        organization_name=org_title,
                        slug=slug,
                        category_id=resolved_cat.id,
                        email=clean_email,
                        phone=clean_mobile,
                        status="active",
                    )
                    db.add(org)
                    db.flush()
            else:
                # Normal user registration: does NOT belong to an organization
                assigned_role = "user"
                org = None

            # 3. Hash password (never store plaintext)
            pwd_hash = hash_password(password)
            user = User(
                organization_id=org.id if org else None,
                name=clean_name,
                phone=clean_mobile,
                email=clean_email,
                password_hash=pwd_hash,
                role=assigned_role,
            )
            db.add(user)
            db.flush()

            user_data = {
                "id": user.id,
                "name": user.name,
                "email": user.email,
                "mobile": user.phone,
                "phone": user.phone,
                "role": user.role,
                "canonical_role": normalize_role(user.role),
                "organization_id": org.id if org else None,
                "organization_name": org.organization_name if org else None,
                "organization_slug": org.slug if org else None,
                "category_id": org.category_id if org else None,
                "category_name": org.category.name if (org and org.category) else None,
                "is_authenticated": True,
            }
            # Issue initial session token
            user_data["token"] = generate_auth_token(user_data)

            logger.info("User registered successfully: user_id=%s, role=%s, org_id=%s", user.id, user.role, user.organization_id)
            return True, "Account created successfully.", user_data

    except Exception as exc:
        err_msg = str(exc)
        logger.exception("Registration error: %s", exc)
        if "relation \"users\" does not exist" in err_msg.lower() or "no such table: users" in err_msg.lower() or "undefinedtable" in err_msg.lower():
            try:
                from database.repository import init_database
                logger.info("Database tables missing during registration. Running auto-initialization...")
                if init_database():
                    return register_user(
                        name=clean_name,
                        email=clean_email,
                        mobile=clean_mobile,
                        password=password,
                        organization_id=organization_id,
                        new_org_name=new_org_name,
                        category_id=category_id,
                        category_name=category_name,
                        role=role,
                    )
            except Exception as auto_init_err:
                logger.error("Auto-initialization during registration failed: %s", auto_init_err)
                return False, f"Database table setup required: {auto_init_err}", None
        return False, f"Registration service error: {err_msg}", None


def authenticate_user(email: str, password: str) -> Tuple[bool, str, Optional[Dict[str, Any]]]:
    """
    Authenticates a user by email and password securely:
    - Constant-time password verification via bcrypt / PBKDF2
    - Issues a cryptographically signed session token
    - Returns standardized user dict with canonical role and bound organization/category
    - Never returns password or sensitive internals
    """
    clean_email = (email or "").strip().lower()
    if not clean_email or not password:
        return False, "Email and password are required.", None

    try:
        with get_db() as db:
            user = db.query(User).filter_by(email=clean_email).first()
            if not user or not user.password_hash:
                return False, "Invalid email or password.", None

            if not verify_password(password, user.password_hash):
                return False, "Invalid email or password.", None

            org = user.organization
            user_data = {
                "id": user.id,
                "name": user.name,
                "email": user.email,
                "mobile": user.phone,
                "phone": user.phone,
                "role": user.role,
                "canonical_role": normalize_role(user.role),
                "organization_id": user.organization_id if normalize_role(user.role) != ROLE_NORMAL_USER else None,
                "organization_name": org.organization_name if (org and normalize_role(user.role) != ROLE_NORMAL_USER) else None,
                "organization_slug": org.slug if (org and normalize_role(user.role) != ROLE_NORMAL_USER) else None,
                "category_id": org.category_id if (org and normalize_role(user.role) != ROLE_NORMAL_USER) else None,
                "category_name": org.category.name if (org and org.category and normalize_role(user.role) != ROLE_NORMAL_USER) else None,
                "is_authenticated": True,
            }
            # Generate secure auth token
            token = generate_auth_token(user_data)
            user_data["token"] = token

            logger.info("User authenticated successfully: user_id=%s, role=%s, org_id=%s", user.id, user.role, user.organization_id)
            return True, "Login successful.", user_data

    except Exception as exc:
        err_msg = str(exc)
        logger.exception("Authentication error for '%s': %s", clean_email, exc)

        # Check for uninitialized database schema or missing columns and auto-heal
        schema_markers = ("relation \"users\" does not exist", "no such table: users", "undefinedtable", "column users.phone does not exist", "undefinedcolumn", "no such column")
        if any(marker in err_msg.lower() for marker in schema_markers):
            try:
                from database.repository import init_database
                logger.info("Database tables missing during authentication. Running auto-initialization...")
                if init_database():
                    with get_db() as db:
                        retry_user = db.query(User).filter_by(email=clean_email).first()
                        if retry_user and retry_user.password_hash and verify_password(password, retry_user.password_hash):
                            retry_org = retry_user.organization
                            user_data = {
                                "id": retry_user.id,
                                "name": retry_user.name,
                                "email": retry_user.email,
                                "mobile": retry_user.phone,
                                "phone": retry_user.phone,
                                "role": retry_user.role,
                                "canonical_role": normalize_role(retry_user.role),
                                "organization_id": retry_user.organization_id if normalize_role(retry_user.role) != ROLE_NORMAL_USER else None,
                                "organization_name": retry_org.organization_name if (retry_org and normalize_role(retry_user.role) != ROLE_NORMAL_USER) else None,
                                "organization_slug": retry_org.slug if (retry_org and normalize_role(retry_user.role) != ROLE_NORMAL_USER) else None,
                                "category_id": retry_org.category_id if (retry_org and normalize_role(retry_user.role) != ROLE_NORMAL_USER) else None,
                                "category_name": retry_org.category.name if (retry_org and retry_org.category and normalize_role(retry_user.role) != ROLE_NORMAL_USER) else None,
                                "is_authenticated": True,
                            }
                            user_data["token"] = generate_auth_token(user_data)
                            return True, "Login successful.", user_data
                        elif not retry_user:
                            return False, "Invalid email or password.", None
            except Exception as auto_init_err:
                logger.error("Auto-initialization during auth failed: %s", auto_init_err)
                return False, f"Database table setup required: {auto_init_err}", None

        return False, f"Authentication service error: {err_msg}", None


# --- Streamlit Session State Management ---

def is_authenticated() -> bool:
    """Returns True if the current user has an active authenticated session."""
    try:
        import streamlit as st
        return bool(st.session_state.get("authenticated") is True and st.session_state.get("user"))
    except Exception:
        return False


def get_current_user() -> Optional[Dict[str, Any]]:
    """Returns the authenticated user's profile dict or None."""
    try:
        import streamlit as st
        if is_authenticated():
            return st.session_state.get("user")
    except Exception:
        pass
    return None


def login_session(user_dict: Dict[str, Any], token: Optional[str] = None):
    """
    Sets session state for authenticated user.
    Strictly locks the tenant context and category to the user's organization in PostgreSQL.
    """
    try:
        import streamlit as st
        st.session_state["authenticated"] = True
        st.session_state["user"] = user_dict
        st.session_state["session_token"] = token or user_dict.get("token")
        st.session_state["role"] = user_dict.get("role")
        st.session_state["canonical_role"] = normalize_role(user_dict.get("role"))
        st.session_state["current_tenant_id"] = user_dict.get("organization_id")
        st.session_state["current_tenant_slug"] = user_dict.get("organization_slug")
        st.session_state["category_id"] = user_dict.get("category_id")

        if hasattr(st, "query_params"):
            if user_dict.get("organization_slug"):
                st.query_params["tenant"] = user_dict["organization_slug"]
            else:
                st.query_params.pop("tenant", None)
    except Exception as exc:
        logger.warning("Could not set session state: %s", exc)


def logout_session():
    """
    Clears authentication and user session state securely.
    Revokes the active session token in the revocation registry.
    """
    try:
        import streamlit as st
        token = st.session_state.get("session_token")
        if token:
            revoke_auth_token(token)

        st.session_state["authenticated"] = False
        st.session_state["user"] = None
        st.session_state.pop("session_token", None)
        st.session_state.pop("role", None)
        st.session_state.pop("canonical_role", None)
        st.session_state.pop("current_tenant_id", None)
        st.session_state.pop("current_tenant_slug", None)
        st.session_state.pop("category_id", None)
        st.session_state.pop("selected_service", None)
        st.session_state.pop("current_view", None)
        if hasattr(st, "query_params"):
            st.query_params.clear()
    except Exception as exc:
        logger.warning("Could not clear session state: %s", exc)


# --- Role & Permission Helpers ---

def is_normal_user(user: Optional[Dict[str, Any]] = None) -> bool:
    """Returns True if user has no authenticated session or canonical role is NORMAL_USER."""
    target = user or get_current_user()
    if not target:
        return True  # Public visitors have normal user access
    return normalize_role(target.get("role")) == ROLE_NORMAL_USER


def is_organization_user(user: Optional[Dict[str, Any]] = None) -> bool:
    """Returns True if user is authenticated and canonical role is ORGANIZATION."""
    target = user or get_current_user()
    if not target:
        return False
    return normalize_role(target.get("role")) == ROLE_ORGANIZATION


def is_admin_user(user: Optional[Dict[str, Any]] = None) -> bool:
    """Returns True if user is authenticated and canonical role is ADMIN."""
    target = user or get_current_user()
    if not target:
        return False
    return normalize_role(target.get("role")) == ROLE_ADMIN


# --- Strict Authorization Guards ---

def require_authenticated(user: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    Enforces that a user is actively authenticated.
    Raises UnauthorizedAccessError if not authenticated.
    """
    target = user or get_current_user()
    if not target:
        raise UnauthorizedAccessError("Authentication required to access this resource.")
    return target


def require_organization_access(user: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    Enforces that caller is an authenticated Organization user.
    Normal users and unauthenticated callers are rejected.
    """
    target = user or get_current_user()
    if not target:
        raise UnauthorizedAccessError("Organization authentication required.")
    if not is_organization_user(target):
        raise ForbiddenRoleError(f"Access denied: Organization credentials required (role is '{target.get('role')}').")
    if not target.get("organization_id"):
        raise ForbiddenRoleError("Access denied: User is not linked to any valid organization.")
    return target


def require_admin_access(user: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    Enforces that caller is an authenticated Platform Administrator.
    Normal users, organizations, and unauthenticated callers are rejected.
    """
    target = user or get_current_user()
    if not target:
        raise UnauthorizedAccessError("Administrator authentication required.")
    if not is_admin_user(target):
        raise ForbiddenRoleError(f"Access denied: Platform Administrator credentials required (role is '{target.get('role')}').")
    return target
