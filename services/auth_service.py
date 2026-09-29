"""
Authentication and identity service for HomeDesk Facility Management Portal.
Provides secure password hashing (bcrypt with PBKDF2 fallback), user registration,
credential verification, and Streamlit session state management.
"""
from typing import Optional, Dict, Any, Tuple
import logging
import re
import secrets
import hashlib
from database.connection import get_db
from database.models import User, Organization
from utils.validators import validate_email, validate_mobile

logger = logging.getLogger(__name__)

# Try importing bcrypt, fallback to hashlib if unavailable
try:
    import bcrypt
    _HAS_BCRYPT = True
except ImportError:
    _HAS_BCRYPT = False
    logger.warning("bcrypt module not found; falling back to hashlib PBKDF2.")


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


def register_user(
    name: str,
    email: str,
    mobile: str,
    password: str,
    organization_id: Optional[int] = None,
    new_org_name: Optional[str] = None,
    role: str = "staff",
) -> Tuple[bool, str, Optional[Dict[str, Any]]]:
    """
    Registers a new user belonging to an existing or newly created organization.
    Enforces password complexity, email uniqueness, and valid organization binding.
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

    try:
        with get_db() as db:
            # 1. Check if email already exists
            existing = db.query(User).filter_by(email=clean_email).first()
            if existing:
                return False, f"An account with email '{clean_email}' already exists.", None

            # 2. Resolve or create organization
            org = None
            if organization_id is not None and int(organization_id) > 0:
                org = db.query(Organization).filter_by(id=int(organization_id)).first()
                if not org:
                    return False, f"Organization ID {organization_id} does not exist.", None
            elif new_org_name and new_org_name.strip():
                org_title = new_org_name.strip()
                base_slug = re.sub(r"[^a-z0-9]+", "-", org_title.lower()).strip("-") or "org"
                slug = base_slug
                counter = 1
                while db.query(Organization).filter_by(slug=slug).first():
                    slug = f"{base_slug}-{counter}"
                    counter += 1

                org = Organization(name=org_title, slug=slug)
                db.add(org)
                db.flush()
            else:
                return False, "Please select an existing organization or provide a new organization name.", None

            # 3. Hash password and save user
            pwd_hash = hash_password(password)
            user = User(
                organization_id=org.id,
                name=clean_name,
                mobile=clean_mobile,
                email=clean_email,
                password_hash=pwd_hash,
                role=role or "staff",
            )
            db.add(user)
            db.flush()

            user_data = {
                "id": user.id,
                "name": user.name,
                "email": user.email,
                "mobile": user.mobile,
                "role": user.role,
                "organization_id": org.id,
                "organization_name": org.name,
                "organization_slug": org.slug,
            }
            logger.info("User registered successfully: user_id=%s, org_id=%s", user.id, org.id)
            return True, "Account created successfully.", user_data

    except Exception as exc:
        logger.error("Registration error: %s", exc)
        return False, "An error occurred during registration. Please try again.", None


def authenticate_user(email: str, password: str) -> Tuple[bool, str, Optional[Dict[str, Any]]]:
    """
    Authenticates a user by email and password.
    Returns (success, message, user_dict).
    Never logs or discloses password credentials.
    """
    clean_email = (email or "").strip().lower()
    if not clean_email or not password:
        return False, "Email and password are required.", None

    try:
        with get_db() as db:
            user = db.query(User).filter_by(email=clean_email).first()
            if not user or not user.password_hash:
                # Use constant message to avoid account enumeration
                return False, "Invalid email or password.", None

            if not verify_password(password, user.password_hash):
                return False, "Invalid email or password.", None

            org = user.organization
            user_data = {
                "id": user.id,
                "name": user.name,
                "email": user.email,
                "mobile": user.mobile,
                "role": user.role,
                "organization_id": user.organization_id,
                "organization_name": org.name if org else "Default Org",
                "organization_slug": org.slug if org else "homedesk",
            }
            logger.info("User authenticated: user_id=%s, org_id=%s", user.id, user.organization_id)
            return True, "Login successful.", user_data

    except Exception as exc:
        logger.error("Authentication error: %s", exc)
        return False, "Authentication service error. Please try again later.", None


# Streamlit Session Management Helpers

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


def login_session(user_dict: Dict[str, Any]):
    """
    Sets session state for authenticated user.
    Strictly locks the tenant context to the user's organization.
    """
    try:
        import streamlit as st
        st.session_state["authenticated"] = True
        st.session_state["user"] = user_dict
        st.session_state["current_tenant_id"] = user_dict["organization_id"]
        st.session_state["current_tenant_slug"] = user_dict["organization_slug"]
        if hasattr(st, "query_params"):
            # Enforce tenant query param reflects authenticated user's org
            st.query_params["tenant"] = user_dict["organization_slug"]
    except Exception as exc:
        logger.warning("Could not set session state: %s", exc)


def logout_session():
    """
    Clears authentication and user session state securely.
    """
    try:
        import streamlit as st
        st.session_state["authenticated"] = False
        st.session_state["user"] = None
        st.session_state.pop("current_tenant_id", None)
        st.session_state.pop("current_tenant_slug", None)
        st.session_state.pop("selected_service", None)
        if hasattr(st, "query_params"):
            st.query_params.clear()
    except Exception as exc:
        logger.warning("Could not clear session state: %s", exc)
