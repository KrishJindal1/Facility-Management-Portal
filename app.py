import streamlit as st
from streamlit_float import *
from storage.excel_handler import create_excel_if_not_exists, get_excel_export_bytes
from forms.Cook_Requirement import render_cook_form
from forms.Driver_Requirement import render_driver_form
from forms.Security_Gaurd_Requirement import render_security_guard_form
from component.chatbot_widget import render_chatbot
from utils.local_storage import get_request, save_request, delete_request
from services.lead_lookup import find_lead_by_mobile
from services.auth_service import (
    authenticate_user,
    register_user,
    is_authenticated,
    get_current_user,
    login_session,
    logout_session,
    is_normal_user,
    is_organization_user,
    is_admin_user,
)
from database.repository import (
    get_controlled_categories,
    get_requirements_for_organization,
    get_user_requirements,
    get_all_organizations_with_categories,
    get_all_requirements_for_admin,
    update_requirement_status,
    VALID_REQUIREMENT_STATUSES,
    mask_contact_info,
    CATEGORY_NAME_TO_SERVICE,
)

st.set_page_config(
    page_title="HomeDesk — Hire Trusted Help",
    page_icon="🗝️",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# Startup initialization & database health check
try:
    create_excel_if_not_exists()
except Exception as _init_err:
    import logging
    logging.getLogger("homedesk.app").error("Startup initialization warning: %s", _init_err)

from database.connection import check_connection
_db_ok, _db_msg = check_connection()
if not _db_ok:
    st.error(f"⚠️ **Database Unavailable**: {_db_msg}. Please verify your `DATABASE_URL` configuration.")

if "selected_service" not in st.session_state:
    st.session_state.selected_service = None


def inject_css():
    st.markdown(
        """
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Fraunces:opsz,wght@9..144,500;9..144,600&family=Inter:wght@400;500;600&family=IBM+Plex+Mono:wght@500;600&display=swap');

        :root {
            --ink: #16243F;
            --ink-soft: #2B3A55;
            --paper: #F5F6F3;
            --card: #FFFFFF;
            --amber: #E8A33D;
            --amber-deep: #C77F1F;
            --teal: #1F7A5C;
            --muted: #5B6573;
            --border: #D9DDE2;
        }

        html, body, [data-testid="stAppViewContainer"] {
            background: var(--paper);
            font-family: 'Inter', sans-serif;
            color: var(--ink);
        }
        [data-testid="stHeader"] { background: transparent; }
        footer, #MainMenu { visibility: hidden; }
        .block-container { padding-top: 2rem; max-width: 1100px; }

        h1, h2, h3 { font-family: 'Fraunces', serif; letter-spacing: -0.01em; }

        /* --- Brand bar --- */
        .brand-bar {
            display: flex;
            align-items: center;
            justify-content: space-between;
            padding-bottom: 1.4rem;
            border-bottom: 1px solid var(--border);
            margin-bottom: 2.2rem;
        }
        .brand-bar .brand {
            font-family: 'Fraunces', serif;
            font-size: 1.35rem;
            font-weight: 600;
            color: var(--ink);
        }
        .brand-bar .brand span { color: var(--amber-deep); }
        .brand-bar .tagline { font-size: 0.85rem; color: var(--muted); }

        /* --- Hero --- */
        .hero-eyebrow {
            text-transform: uppercase;
            letter-spacing: 0.12em;
            font-size: 0.75rem;
            color: var(--amber-deep);
            font-weight: 600;
            margin-bottom: 0.6rem;
        }
        .hero-title {
            font-size: 2.5rem;
            line-height: 1.18;
            font-weight: 600;
            color: var(--ink);
            margin-bottom: 0.8rem;
        }
        .hero-sub {
            font-size: 1.02rem;
            color: var(--muted);
            max-width: 30rem;
            line-height: 1.55;
        }

        /* --- Token card: signature element ---
             This used to be a plain markdown div (.token-stub). It's now
             the outer Streamlit container itself that carries the card
             look, so a real text input / button can sit inside the same
             bordered box instead of floating below it. Visual appearance
             (colors, radius, shadow, spacing) is unchanged. */
        div[class*="st-key-token_card"] {
            background: var(--card);
            border: 1px solid var(--border);
            border-radius: 14px;
            padding: 1.4rem 1.6rem 1.2rem;
            box-shadow: 0 18px 40px -24px rgba(22,36,63,0.35);
            position: relative;
            max-width: 320px;
            margin-left: auto;
        }
        .token-eyebrow {
            font-size: 0.68rem;
            text-transform: uppercase;
            letter-spacing: 0.1em;
            color: var(--muted);
        }
        .token-number {
            font-family: 'IBM Plex Mono', monospace;
            font-size: 1.6rem;
            font-weight: 600;
            color: var(--ink);
            margin: 0.15rem 0 0.9rem;
            line-height: 1.3;
        }
        .token-perforation {
            border-top: 2px dashed var(--border);
            position: relative;
            margin: 0 -1.6rem;
        }
        .token-perforation::before,
        .token-perforation::after {
            content: "";
            position: absolute;
            top: -8px;
            width: 16px;
            height: 16px;
            border-radius: 50%;
            background: var(--paper);
        }
        .token-perforation::before { left: -8px; }
        .token-perforation::after { right: -8px; }
        .token-status-row {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-top: 0.9rem;
            font-family: 'IBM Plex Mono', monospace;
            font-size: 0.72rem;
        }
        .token-pill {
            background: rgba(31,122,92,0.12);
            color: var(--teal);
            padding: 0.15rem 0.55rem;
            border-radius: 999px;
            font-weight: 600;
        }
        /* the mobile lookup input + buttons, embedded inside the same card */
        div[class*="st-key-token_card"] .stTextInput {
            margin-top: 0.9rem;
        }
        div[class*="st-key-token_card"] .stButton > button {
            margin-top: 0.6rem;
            background: var(--ink);
            color: white;
            border: none;
        }
        div[class*="st-key-token_card"] .stButton > button:hover { background: var(--amber-deep); }
        div[class*="st-key-token_card"] .streamlit-expanderHeader {
            font-size: 0.82rem;
        }

        /* --- Section label --- */
        .section-label {
            font-size: 0.78rem;
            text-transform: uppercase;
            letter-spacing: 0.1em;
            color: var(--muted);
            margin: 2.6rem 0 1rem;
            display: flex;
            align-items: center;
            gap: 0.6rem;
            color: var(--ink) !important;
        }
        .section-label::after { content: ""; flex: 1; height: 1px; background: var(--border); }

        /* --- Service cards: floating, elevated cards --- */
        .service-card {
            background: var(--card);
            border: 1px solid var(--border);
            border-radius: 16px;
            padding: 1.6rem 1.2rem 1.1rem;
            text-align: center;
            position: relative;
            overflow: hidden;
            box-shadow: 0 14px 34px -22px rgba(22,36,63,0.28);
            transition: border-color 0.25s ease, transform 0.3s ease, box-shadow 0.3s ease;
        }
        /* soft glowing blob tucked behind each card for depth */
        .service-card::before {
            content: "";
            position: absolute;
            top: -46px;
            right: -46px;
            width: 130px;
            height: 130px;
            background: radial-gradient(circle, rgba(232,163,61,0.18), transparent 70%);
            border-radius: 50%;
            pointer-events: none;
        }
        .service-card .icon-badge {
            width: 56px;
            height: 56px;
            margin: 0 auto 0.9rem;
            border-radius: 50%;
            background: linear-gradient(145deg, var(--amber), var(--amber-deep));
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 1.5rem;
            position: relative;
            box-shadow: 0 14px 24px -12px rgba(199,127,31,0.55);
            animation: badgeFloat 3.6s ease-in-out infinite;
        }
        /* stagger each card's float so they don't bob in lockstep */
        div[class*="st-key-card_cook"] .icon-badge { animation-delay: 0s; }
        div[class*="st-key-card_driver"] .icon-badge { animation-delay: 0.5s; }
        div[class*="st-key-card_security_guard"] .icon-badge { animation-delay: 1s; }

        @keyframes badgeFloat {
            0%, 100% { transform: translateY(0); }
            50% { transform: translateY(-6px); }
        }

        .service-card h3 { font-size: 1.08rem; margin: 0 0 0.3rem; position: relative; }
        .service-card p { font-size: 0.85rem; color: var(--muted); margin: 0; min-height: 2.4rem; position: relative; }

        div[class*="st-key-card_"]:hover .service-card {
            border-color: var(--amber-deep);
            transform: translateY(-8px);
            box-shadow: 0 30px 48px -20px rgba(22,36,63,0.35);
        }

        @media (prefers-reduced-motion: reduce) {
            .service-card .icon-badge { animation: none; }
            .service-card, div[class*="st-key-card_"]:hover .service-card { transition: none; }
        }

        /* --- Buttons --- */
        .stButton > button {
            border-radius: 9px;
            border: 1px solid var(--border);
            font-weight: 500;
            padding: 0.5rem 1rem;
        }
        div[class*="st-key-card_"] .stButton > button {
            width: 100%;
            margin-top: 0.7rem;
            background: var(--ink);
            color: white;
            border: none;
        }
        div[class*="st-key-card_"] .stButton > button:hover { background: var(--amber-deep); }

        div[class*="st-key-nav_back"] button {
        background: white !important;
        color: #16243F !important;
        border: 1px solid var(--border) !important;
        }

        div[class*="st-key-nav_back"] button p {
        color: #16243F !important;
        }
        

        div[data-testid="stFormSubmitButton"] button {
            background: var(--ink) !important;
            color: white !important;
            border: none !important;
            border-radius: 9px !important;
            padding: 0.6rem 1.6rem !important;
            font-weight: 600 !important;
        }
        div[data-testid="stFormSubmitButton"] button:hover { background: var(--amber-deep) !important; }

        .stTextInput input,
        .stNumberInput input,
        .stTextArea textarea,
        .stSelectbox div[data-baseweb="select"],
        .stDateInput input {
            border-radius: 8px !important;
            border: 1px solid var(--border) !important;
            background: var(--card) !important;
            color: var(--ink) !important;
        }
        .stTextInput input::placeholder,
        .stTextArea textarea::placeholder {
            color: var(--muted) !important;
        }

        .footer-note {
            text-align: center;
            color: var(--muted);
            font-size: 0.78rem;
            margin-top: 3rem;
            padding-top: 1.2rem;
            border-top: 1px solid var(--border);
        }
       [data-testid="stWidgetLabel"] {
    color: var(--ink) !important;
    font-weight: 500 !important;
}

[data-testid="stWidgetLabel"] p {
    color: var(--ink) !important;
}

/* Form Container */

[data-testid="stForm"] {
    background: white;
    padding: 1.5rem;
    border-radius: 16px;
    border: 1px solid var(--border);
}

/* Inline validation / helper hints (used by field_renderer + hero lookup) */
.field-hint {
    font-size: 0.78rem;
    margin-top: 0.4rem;
    margin-bottom: 0.2rem;
    line-height: 1.3;
}
.field-hint.warning { color: var(--amber-deep); }
.field-hint.error { color: #C0392B; }
.field-hint.info { color: var(--muted); }

/* Cursor Color */

.stTextInput input,
.stNumberInput input,
.stTextArea textarea {
    caret-color: var(--ink) !important;
}

/* Focus Animation */

.stTextInput input:focus,
.stNumberInput input:focus,
.stTextArea textarea:focus,
.stDateInput input:focus {
    border: 1px solid var(--amber) !important;
    box-shadow: 0 0 0 3px rgba(232,163,61,0.2) !important;
    outline: none !important;
}
/* Floating Chat */

div[data-testid="stChatMessage"]{
    background: var(--card);
    border: 1px solid var(--border);
    border-radius:12px;
    padding:10px;
}

/* The chat text was inheriting an invisible color from Streamlit's own
   theme — force it to the brand ink color everywhere text can appear
   inside a chat bubble. */
div[data-testid="stChatMessage"] p,
div[data-testid="stChatMessage"] span,
div[data-testid="stChatMessage"] li,
div[data-testid="stChatMessage"] [data-testid="stMarkdownContainer"],
div[data-testid="stChatMessageContent"] p {
    color: var(--ink) !important;
}

/* ================= CHAT INPUT ================= */

/* Entire chat input area */
div[data-testid="stChatInput"]{
    background: var(--card) !important;
    border: 1px solid var(--border) !important;
    border-radius: 14px !important;
    padding: 0.35rem !important;
    margin-top: 0.7rem !important;
}

/* Inner container */
div[data-testid="stChatInput"] > div{
    background: var(--card) !important;
}

/* Textarea */
div[data-testid="stChatInput"] textarea{
    background: var(--card) !important;
    color: var(--ink) !important;
    caret-color: var(--ink) !important;
    border: none !important;
    box-shadow: none !important;
}

/* Placeholder */
div[data-testid="stChatInput"] textarea::placeholder{
    color: var(--muted) !important;
    opacity: 1 !important;
}

/* Remove black focus */
div[data-testid="stChatInput"] textarea:focus{
    background: var(--card) !important;
    color: var(--ink) !important;
    outline: none !important;
    box-shadow: none !important;
}

/* Send button */
div[data-testid="stChatInput"] button{
    background: var(--amber) !important;
    color: white !important;
    border-radius: 10px !important;
    border: none !important;
}

div[data-testid="stChatInput"] button:hover{
    background: var(--amber-deep) !important;
}
        </style>
        """,
        unsafe_allow_html=True,
    )


def render_brand_bar():
    authenticated = is_authenticated()
    user = get_current_user()

    col_brand, col_auth = st.columns([1.4, 1.6])
    with col_brand:
        if is_organization_user() and user:
            tagline = f"Organization Portal &middot; <b>{user['organization_name']}</b>"
        elif is_admin_user() and user:
            tagline = "Platform Administration Portal"
        else:
            tagline = "Facility Services &middot; <b>Hire Trusted Help</b>"

        st.markdown(
            f"""
            <div class="brand-bar" style="margin-bottom: 0.4rem; padding-bottom: 0.4rem; border-bottom: none;">
                <div class="brand">Home<span>Desk</span></div>
                <div class="tagline">{tagline}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with col_auth:
        if authenticated and user:
            role = user.get("role", "user")
            col_info, col_btn1, col_logout = st.columns([1.6, 1.0, 0.8])
            with col_info:
                if role == "organization":
                    badge_text = f"ORG: {user.get('category_name', 'SERVICE')}"
                    sub_text = f"🏢 {user.get('organization_name', 'Org')} (Locked)"
                elif role == "admin":
                    badge_text = "PLATFORM ADMIN"
                    sub_text = "🛡️ Global Management"
                else:
                    badge_text = "NORMAL USER"
                    sub_text = "👤 Customer"

                st.markdown(
                    f"""
                    <div style="text-align: right; padding-top: 0.3rem; font-size: 0.82rem; color: var(--ink);">
                        <span>👤 <b>{user['name']}</b></span>
                        <span style="background: rgba(31,122,92,0.12); color: var(--teal); padding: 0.15rem 0.5rem; border-radius: 999px; margin-left: 0.3rem; font-weight: 600; font-size: 0.70rem;">{badge_text}</span>
                        <div style="font-size: 0.72rem; color: var(--muted); margin-top: 0.1rem;">{sub_text}</div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

            with col_btn1:
                if role == "user":
                    if st.button("My Requests", key="nav_my_req_btn", use_container_width=True):
                        st.session_state.current_view = "my_requests"
                        st.session_state.selected_service = None
                        st.rerun()
                elif role in ("organization", "admin"):
                    if st.button("Public Site", key="nav_public_site_btn", use_container_width=True):
                        st.session_state.current_view = "home"
                        st.session_state.selected_service = None
                        st.rerun()

            with col_logout:
                if st.button("Sign Out", key="nav_logout_btn", use_container_width=True):
                    logout_session()
                    delete_request()
                    st.session_state.current_view = "home"
                    st.session_state.selected_service = None
                    st.rerun()
        else:
            col_spacer, col_login_btn = st.columns([1.5, 1.5])
            with col_login_btn:
                if st.session_state.get("current_view") == "auth":
                    if st.button("← Back to Public Forms", key="nav_back_to_public", use_container_width=True):
                        st.session_state.current_view = "home"
                        st.rerun()
                else:
                    if st.button("🏢 Sign In / Organization Portal", key="nav_login_entry_btn", use_container_width=True):
                        st.session_state.current_view = "auth"
                        st.session_state.selected_service = None
                        st.rerun()

    st.markdown('<div style="border-bottom: 1px solid var(--border); margin-bottom: 1.8rem;"></div>', unsafe_allow_html=True)


def render_auth_screen():
    col1, col2, col3 = st.columns([1, 1.6, 1])
    with col2:
        st.markdown(
            """
            <div style="text-align: center; margin-bottom: 1.5rem; margin-top: 0.5rem;">
                <h2 style="font-family: 'Fraunces', serif; color: var(--ink); margin-bottom: 0.3rem;">Portal Authentication</h2>
                <p style="color: var(--muted); font-size: 0.9rem;">Sign in or register as a Normal User or Service Provider Organization.</p>
            </div>
            """,
            unsafe_allow_html=True,
        )

        tab_login, tab_register = st.tabs(["🔑 Sign In", "📝 Register Account"])

        with tab_login:
            with st.form("login_form"):
                email = st.text_input("Email Address", placeholder="name@domain.com", key="login_email")
                password = st.text_input("Password", type="password", placeholder="Enter your password", key="login_pwd")
                login_submitted = st.form_submit_button("Sign In", use_container_width=True)

            if login_submitted:
                success, msg, user_data = authenticate_user(email, password)
                if success and user_data:
                    login_session(user_data)
                    st.session_state.current_view = "home"
                    st.success(f"Welcome back, {user_data['name']}! Entering portal...")
                    st.rerun()
                else:
                    st.error(msg)

            with st.expander("ℹ️ Demo Organization, Admin & User Accounts"):
                st.markdown(
                    """
                    **Platform Administrator:**
                    - Email: `admin@homedesk.com` | Password: `Password123!`

                    **Cook Organization (HomeDesk Primary):**
                    - Email: `cooks@homedesk.com` | Password: `Password123!`

                    **Driver Organization (Acme Facilities):**
                    - Email: `admin@acme.com` | Password: `Password123!`

                    **Security Guard Organization (IronShield Security):**
                    - Email: `guards@ironshield.com` | Password: `Password123!`

                    **Normal User (Customer):**
                    - Email: `user@homedesk.com` | Password: `Password123!`
                    """
                )

        with tab_register:
            account_type = st.radio(
                "Account Type",
                options=["Normal User (Customer / Household)", "Service Provider Organization"],
                key="reg_account_type",
                horizontal=True,
            )

            with st.form("register_form"):
                reg_name = st.text_input("Full Name", placeholder="e.g. Jane Doe", key="reg_name")
                reg_email = st.text_input("Email Address", placeholder="jane@domain.com", key="reg_email")
                reg_mobile = st.text_input("Mobile Number", placeholder="10-digit number", max_chars=10, key="reg_mobile")
                reg_pwd = st.text_input("Password (min 8 chars, 1 letter, 1 number)", type="password", key="reg_pwd")
                reg_confirm = st.text_input("Confirm Password", type="password", key="reg_confirm")

                new_org_name = None
                selected_cat_name = None

                if account_type == "Service Provider Organization":
                    st.markdown("---")
                    st.markdown("##### 🏢 Organization Profile")
                    new_org_name = st.text_input("Organization Name", placeholder="e.g. Apex Cooks & Chefs", key="reg_org_name")
                    st.caption("Each organization must register for exactly ONE service category.")
                    selected_cat_name = st.selectbox(
                        "Service Category (Controlled)",
                        options=["Cook", "Driver", "Security Guard"],
                        key="reg_org_cat",
                    )

                reg_submitted = st.form_submit_button("Register & Create Account", use_container_width=True)

            if reg_submitted:
                if reg_pwd != reg_confirm:
                    st.error("Passwords do not match. Please re-enter your password.")
                elif account_type == "Service Provider Organization" and not (new_org_name and new_org_name.strip()):
                    st.error("Organization Name is required for organization registration.")
                else:
                    is_org = (account_type == "Service Provider Organization")
                    success, msg, user_data = register_user(
                        name=reg_name,
                        email=reg_email,
                        mobile=reg_mobile,
                        password=reg_pwd,
                        new_org_name=new_org_name if is_org else None,
                        category_name=selected_cat_name if is_org else None,
                        role="organization" if is_org else "user",
                    )
                    if success and user_data:
                        login_session(user_data)
                        st.session_state.current_view = "home"
                        st.success(f"Account registered successfully! Entering portal...")
                        st.rerun()
                    else:
                        st.error(msg)


def render_organization_dashboard(user: Dict[str, Any]):
    """
    Dedicated dashboard for Organization users (Phase 5).
    Core business rule: Automatically uses the authenticated organization's registered category.
    organization.category_id == requirement.category_id

    Requirements:
    1. Organization name
    2. Registered service category (locked, non-editable)
    3. Number of available requirements
    4. List/table of matching requirements
    5. Requirement details
    6. Requirement status
    7. Relevant actions: Status progression / update & Excel export
    """
    if not user or not is_organization_user(user):
        st.error("⛔ **Access Denied**: Organization authentication required to access this dashboard.")
        return

    org_id = user.get("organization_id")
    if not org_id:
        st.error("⛔ **Access Denied**: No registered organization is linked to this account.")
        return

    org_name = user.get("organization_name", "Organization")
    cat_name = user.get("category_name", "UNKNOWN")
    cat_display = CATEGORY_NAME_TO_SERVICE.get(cat_name, cat_name)

    # 1 & 2. Organization Header Banner with Immutable Category Lock
    st.markdown(
        f"""
        <div style="background: white; border: 1px solid var(--border); border-radius: 16px; padding: 1.6rem; margin-bottom: 1.5rem; box-shadow: 0 10px 30px -15px rgba(22,36,63,0.15);">
            <div style="display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 0.8rem;">
                <div>
                    <div style="font-size: 0.72rem; text-transform: uppercase; letter-spacing: 0.1em; color: var(--muted); font-weight: 600;">Service Organization Portal</div>
                    <h2 style="margin: 0.2rem 0; font-family: 'Fraunces', serif; color: var(--ink);">🏢 {org_name}</h2>
                    <div style="font-size: 0.85rem; color: var(--muted);">Managing requirements strictly for your registered category in PostgreSQL.</div>
                </div>
                <div style="text-align: right;">
                    <span style="background: rgba(232,163,61,0.18); color: var(--amber-deep); padding: 0.45rem 1.1rem; border-radius: 999px; font-weight: 700; font-size: 0.85rem; border: 1px solid var(--amber); display: inline-flex; align-items: center; gap: 0.4rem;">
                        🔒 CATEGORY: {cat_name} (LOCKED)
                    </span>
                    <div style="font-size: 0.72rem; color: var(--muted); margin-top: 0.35rem;">Controlled system category &middot; Non-editable</div>
                </div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # Automatically query strictly matching category from PostgreSQL (Authorization enforced at DB level)
    requirements = get_requirements_for_organization(org_id)

    # 3. KPI Metrics / Number of available requirements
    total_count = len(requirements)
    new_count = sum(1 for r in requirements if r.get("Status") == "New")
    active_count = sum(1 for r in requirements if r.get("Status") in ("Claimed", "In Progress"))
    completed_count = sum(1 for r in requirements if r.get("Status") == "Completed")

    col_m1, col_m2, col_m3, col_m4 = st.columns(4)
    with col_m1:
        st.metric(f"Total {cat_display} Requirements", total_count)
    with col_m2:
        st.metric("New Requests", new_count)
    with col_m3:
        st.metric("Claimed / In Progress", active_count)
    with col_m4:
        st.metric("Completed", completed_count)

    st.markdown("---")

    # Action Toolbar: Search, Status Filter, and Excel Export
    col_filter, col_search, col_export = st.columns([1.2, 1.4, 1.2])
    with col_filter:
        status_filter = st.selectbox(
            "Filter by Status",
            options=["All Statuses", "New", "Claimed", "In Progress", "Completed", "Cancelled"],
            key="org_dash_status_filter",
        )
    with col_search:
        search_query = st.text_input(
            "Search Requirements",
            placeholder="Search by Lead ID or City...",
            key="org_dash_search",
        )
    with col_export:
        st.markdown("<div style='height: 1.7rem;'></div>", unsafe_allow_html=True)
        try:
            excel_bytes = get_excel_export_bytes(organization_id=org_id)
            st.download_button(
                label=f"📥 Export {cat_display} Leads (.xlsx)",
                data=excel_bytes,
                file_name=f"{org_name.lower().replace(' ', '_')}_{cat_name.lower()}_leads.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True,
                key="org_dash_export_btn",
            )
        except Exception as exc:
            st.caption(f"Export unavailable: {exc}")

    # Apply filters locally on the already category-isolated dataset
    filtered = requirements
    if status_filter != "All Statuses":
        filtered = [r for r in filtered if r.get("Status") == status_filter]
    if search_query and search_query.strip():
        q = search_query.strip().lower()
        filtered = [
            r for r in filtered
            if q in str(r.get("Lead ID", "")).lower()
            or q in str(r.get("City", "")).lower()
            or q in str(r.get("Name", "")).lower()
        ]

    # Empty Result State handling
    if total_count == 0:
        st.markdown(
            f"""
            <div style="background: white; border: 2px dashed var(--border); border-radius: 16px; padding: 3rem 1.5rem; text-align: center; margin: 1.5rem 0;">
                <div style="font-size: 2.5rem; margin-bottom: 0.6rem;">📋</div>
                <h3 style="font-family: 'Fraunces', serif; color: var(--ink); margin-bottom: 0.4rem;">No {cat_display} Requirements Available</h3>
                <p style="color: var(--muted); font-size: 0.92rem; max-width: 480px; margin: 0 auto; line-height: 1.5;">
                    There are currently no customer submissions for your registered category (<b>{cat_display}</b>).
                    New requirements submitted by normal users through public forms will appear here automatically in real time.
                </p>
            </div>
            """,
            unsafe_allow_html=True,
        )
        return

    if not filtered:
        st.info(f"No requirements found matching the status '{status_filter}' or search criteria.")
        return

    # 4. Summary Table View (Sensitive info masked for high-level overview)
    tab_list, tab_table = st.tabs(["📌 Detailed Requirements List", "📊 Summary Table View"])

    with tab_table:
        table_rows = []
        for r in filtered:
            # Privacy protection: mask customer contact number in overview table
            masked_phone = mask_contact_info(r.get("Mobile"))
            table_rows.append({
                "Lead ID": r.get("Lead ID"),
                "Date": str(r.get("Date Time", ""))[:16],
                "Customer": r.get("Name"),
                "Contact (Masked)": masked_phone,
                "City": r.get("City"),
                "Budget": f"₹{r.get('Budget', 0):,.0f}",
                "Status": r.get("Status", "New"),
            })
        st.dataframe(table_rows, use_container_width=True)

    with tab_list:
        # 5, 6 & 7. Detailed Matching Requirements Cards with Status & Relevant Actions
        for idx, req in enumerate(filtered):
            lead_id = req.get("Lead ID", f"REQ-{idx+1}")
            customer_name = req.get("Name", "Customer")
            city = req.get("City", "N/A")
            budget = req.get("Budget", 0)
            date_time = req.get("Date Time", "")
            current_status = req.get("Status", "New")

            # Status pill color mapping
            status_colors = {
                "New": ("rgba(232,163,61,0.15)", "#C77F1F"),
                "Claimed": ("rgba(52,152,219,0.15)", "#2980B9"),
                "In Progress": ("rgba(155,89,182,0.15)", "#8E44AD"),
                "Completed": ("rgba(31,122,92,0.15)", "#1F7A5C"),
                "Cancelled": ("rgba(127,140,141,0.15)", "#7F8C8D"),
            }
            bg_col, text_col = status_colors.get(current_status, ("rgba(22,36,63,0.1)", "#16243F"))

            expander_title = (
                f"📌 {lead_id} — {customer_name} ({city}) &middot; Budget: ₹{budget:,.0f} &middot; [{current_status}]"
            )

            with st.expander(expander_title, expanded=(idx == 0 and len(filtered) == 1)):
                c1, c2 = st.columns(2)
                with c1:
                    st.markdown(f"**Customer Name:** {customer_name}")
                    st.markdown(f"**Mobile Contact:** `{req.get('Mobile', '')}`")
                    if req.get("Email"):
                        st.markdown(f"**Email Address:** {req.get('Email')}")
                    st.markdown(f"**Location / City:** {city}, {req.get('State', '')} (PIN: {req.get('Pincode', 'N/A')})")
                    if req.get("Address"):
                        st.markdown(f"**Full Address:** {req.get('Address')}")

                with c2:
                    st.markdown(f"**Submitted Date:** {date_time}")
                    st.markdown(f"**Budget:** ₹{budget:,.0f}")
                    st.markdown(f"**Preferred Timing:** {req.get('Preferred Timing', 'Flexible')}")
                    if req.get("Start Date"):
                        st.markdown(f"**Expected Start Date:** {req.get('Start Date')}")
                    st.markdown(
                        f"""
                        <div style="margin-top: 0.4rem;">
                            <b>Current Status:</b>
                            <span style="background: {bg_col}; color: {text_col}; padding: 0.2rem 0.6rem; border-radius: 999px; font-weight: 700; font-size: 0.78rem;">
                                {current_status}
                            </span>
                        </div>
                        """,
                        unsafe_allow_html=True,
                    )

                # Category-Specific Details
                st.markdown("---")
                st.markdown("##### 🔍 Service Requirement Specifications")
                sc1, sc2 = st.columns(2)
                with sc1:
                    if cat_name == "COOK":
                        st.markdown(f"**Cuisine Type:** {req.get('Cuisine Type', 'Not specified')}")
                        st.markdown(f"**Meals Per Day:** {req.get('Meals Per Day', 'Not specified')}")
                    elif cat_name == "DRIVER":
                        st.markdown(f"**Vehicle Type:** {req.get('Vehicle Type', 'Not specified')}")
                        st.markdown(f"**License Required:** {req.get('License Required', 'Not specified')}")
                    elif cat_name == "SECURITY_GUARD":
                        st.markdown(f"**Duty Shift:** {req.get('Day/Night Shift', 'Not specified')}")
                        st.markdown(f"**Site Type:** {req.get('Residential/Commercial', 'Not specified')}")

                with sc2:
                    if req.get("Additional Notes"):
                        st.markdown(f"**Additional Customer Notes:** {req.get('Additional Notes')}")
                    else:
                        st.caption("No additional customer notes provided.")

                # 7. Relevant Actions: Status Progression / Update
                st.markdown("---")
                st.markdown("##### ⚡ Manage Requirement Status")
                act_col1, act_col2 = st.columns([1.5, 1])

                with act_col1:
                    status_idx = (
                        VALID_REQUIREMENT_STATUSES.index(current_status)
                        if current_status in VALID_REQUIREMENT_STATUSES
                        else 0
                    )
                    selected_status = st.selectbox(
                        "Change Status To:",
                        options=VALID_REQUIREMENT_STATUSES,
                        index=status_idx,
                        key=f"status_select_{lead_id}",
                    )

                with act_col2:
                    st.markdown("<div style='height: 1.7rem;'></div>", unsafe_allow_html=True)
                    if st.button("Update Status", key=f"btn_update_status_{lead_id}", use_container_width=True):
                        if selected_status == current_status:
                            st.info("Status is already set to this value.")
                        else:
                            success, msg, _ = update_requirement_status(
                                lead_id=lead_id,
                                new_status=selected_status,
                                organization_id=org_id,
                            )
                            if success:
                                st.success(f"Status for {lead_id} updated to '{selected_status}' successfully!")
                                st.rerun()
                            else:
                                st.error(msg)


def render_admin_dashboard(user: Dict[str, Any]):
    """
    Dedicated dashboard for Platform Administrators.
    Can manage and view all categories, all organizations, and all requirements.
    """
    if not user or not is_admin_user(user):
        st.error("⛔ **Access Denied**: Platform Administrator credentials required to access this dashboard.")
        return
    st.markdown(
        """
        <div style="background: white; border: 1px solid var(--border); border-radius: 16px; padding: 1.6rem; margin-bottom: 1.5rem; box-shadow: 0 10px 30px -15px rgba(22,36,63,0.15);">
            <div style="font-size: 0.72rem; text-transform: uppercase; letter-spacing: 0.1em; color: var(--muted); font-weight: 600;">Platform Administration</div>
            <h2 style="margin: 0.2rem 0; font-family: 'Fraunces', serif; color: var(--ink);">Global Management Console</h2>
            <div style="font-size: 0.85rem; color: var(--muted);">Full access across all service categories, organizations, and customer requirements.</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    categories = get_controlled_categories()
    organizations = get_all_organizations_with_categories()
    all_reqs = get_all_requirements_for_admin()

    c1, c2, c3 = st.columns(3)
    with c1:
        st.metric("Service Categories", len(categories))
    with c2:
        st.metric("Registered Organizations", len(organizations))
    with c3:
        st.metric("Total Platform Requirements", len(all_reqs))

    st.markdown("---")

    tab_reqs, tab_orgs, tab_cats, tab_export = st.tabs([
        "📋 All Requirements",
        "🏢 Registered Organizations",
        "🏷️ Controlled Categories",
        "📊 Master Export",
    ])

    with tab_reqs:
        cat_filter = st.selectbox("Filter by Category", options=["All Categories"] + [c["name"] for c in categories], key="admin_cat_filter")
        filtered_reqs = all_reqs
        if cat_filter != "All Categories":
            filtered_reqs = [r for r in all_reqs if r.get("category_id") == next((c["id"] for c in categories if c["name"] == cat_filter), None)]

        st.caption(f"Displaying {len(filtered_reqs)} requirement(s)")
        for r in filtered_reqs:
            with st.expander(f"📌 {r.get('Lead ID')} — {r.get('Service Type')} &middot; {r.get('Name')} ({r.get('City')})"):
                st.write(r)

    with tab_orgs:
        st.markdown("#### Organizations & Category Bindings")
        for o in organizations:
            st.markdown(
                f"- **{o['organization_name']}** (Slug: `{o['slug']}`) &middot; Category: **{o['category_name']}** &middot; Status: `{o['status']}`"
            )

    with tab_cats:
        st.markdown("#### Controlled System Categories")
        st.caption("Category values are controlled system entities and cannot be modified arbitrarily.")
        for c in categories:
            st.markdown(f"- **ID {c['id']}:** `{c['name']}` ({c['display_name']})")

    with tab_export:
        st.markdown("#### Platform-Wide Data Export")
        try:
            excel_bytes = get_excel_export_bytes()
            st.download_button(
                label="📥 Download Master Portal Requirements (.xlsx)",
                data=excel_bytes,
                file_name="master_facility_management_export.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True,
                key="admin_master_export_btn",
            )
        except Exception as exc:
            st.caption(f"Master export error: {exc}")


def render_my_requests(user: Dict[str, Any]):
    """
    Customer portal allowing normal users to track only their own submissions.
    Normal users CANNOT access organization dashboards or other users' requirements.
    """
    if not user:
        st.error("⛔ **Access Denied**: Please sign in to view your submissions.")
        return

    user_id = user.get("id")
    user_phone = user.get("phone")
    my_reqs = get_user_requirements(user_id=user_id, mobile=user_phone)

    st.markdown("### 📋 My Service Submissions")
    st.caption("You can track your service requests below. Normal users can only view their own submissions.")

    if not my_reqs:
        st.info("You haven't submitted any service requests yet.")
        if st.button("Browse Public Services", key="btn_my_reqs_browse"):
            st.session_state.current_view = "home"
            st.rerun()
    else:
        for r in my_reqs:
            with st.expander(f"📌 {r.get('Lead ID')} — {r.get('Service Type')} ({r.get('City')}) &middot; Status: {r.get('Status')}"):
                st.markdown(f"**Service:** {r.get('Service Type')}")
                st.markdown(f"**City:** {r.get('City')}")
                st.markdown(f"**Budget:** ₹{r.get('Budget', 0):,.0f}")
                st.markdown(f"**Date Submitted:** {r.get('Date Time')}")
                st.markdown(f"**Status:** `{r.get('Status')}`")


def render_hero():
    left, right = st.columns([1.3, 1], gap="large")

    with left:
        st.markdown(
            """<div class="hero-eyebrow">Household staffing, simplified</div><div class="hero-title">Tell us who you need.<br>We'll take it from there.</div><p class="hero-sub">Share a few details about the help you're looking for — a cook, a driver, or a security guard — and your request joins our queue with its own tracked token.</p>""",
            unsafe_allow_html=True,
        )

    with right:
        request = get_request()

        with st.container(key="token_card"):
            if request:
                lead_id = request.get("lead_id") or "—"
                service = (request.get("service") or "").upper()

                st.markdown(
                    f"""<div class="token-eyebrow">YOUR REQUEST</div><div class="token-number">{lead_id}</div><div class="token-perforation"></div><div class="token-status-row"><span>{service}</span><span class="token-pill">SUBMITTED</span></div>""",
                    unsafe_allow_html=True,
                )

                with st.expander("View request details"):
                    details = find_lead_by_mobile(request.get("mobile"))
                    if details:
                        for field_key, field_value in details.items():
                            st.markdown(f"**{field_key}:** {field_value}")
                    else:
                        st.caption("We couldn't load the full details for this request right now — please check back later.")

                if st.button("Not you? Clear this", key="clear_request_btn", use_container_width=True):
                    delete_request()
                    st.rerun()

            else:
                st.markdown(
                    """<div class="token-eyebrow">FIND YOUR REQUEST</div><div class="token-number">Track an existing request</div><div class="token-perforation"></div>""",
                    unsafe_allow_html=True,
                )

                mobile_input = st.text_input(
                    "Mobile number",
                    key="hero_lookup_mobile",
                    placeholder="10-digit mobile number",
                    label_visibility="collapsed",
                    max_chars=10,
                )

                if st.button("Find my request", key="hero_lookup_btn", use_container_width=True):
                    mobile_clean = (mobile_input or "").strip()

                    if not mobile_clean:
                        st.markdown(
                            '<div class="field-hint warning">⚠ Enter your mobile number first</div>',
                            unsafe_allow_html=True,
                        )
                    else:
                        found = find_lead_by_mobile(mobile_clean)

                        if found:
                            save_request(
                                found.get("Lead ID"),
                                mobile_clean,
                                found.get("Service"),
                            )
                            st.rerun()
                        else:
                            st.markdown(
                                '<div class="field-hint warning">⚠ No request found for that mobile number.</div>',
                                unsafe_allow_html=True,
                            )


SERVICES = [
    {"key": "Cook", "icon": "🍳", "desc": "Daily meals, cooked your way."},
    {"key": "Driver", "icon": "🚗", "desc": "Reliable drivers, on your schedule."},
    {"key": "Security Guard", "icon": "🛡️", "desc": "Trained guards for home or office."},
]


def render_service_cards():
    st.markdown('<div class="section-label">Choose a service</div>', unsafe_allow_html=True)
    cols = st.columns(3, gap="medium")
    for col, service in zip(cols, SERVICES):
        slug = service["key"].lower().replace(" ", "_").replace("/", "_")
        with col:
            with st.container(key=f"card_{slug}"):
                st.markdown(
                    f"""
                    <div class="service-card">
                        <div class="icon-badge">{service['icon']}</div>
                        <h3>{service['key']}</h3>
                        <p>{service['desc']}</p>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
                if st.button("Select", key=f"select_{slug}", use_container_width=True):
                    st.session_state.selected_service = service["key"]
                    st.rerun()


def render_home():
    render_hero()
    render_service_cards()
    st.markdown(
        '<div class="footer-note">HomeDesk v2.2 — No spam calls. Just genuine requests, routed straight to verified service providers.</div>',
        unsafe_allow_html=True,
    )


SERVICE_RENDERERS = {
    "Cook": render_cook_form,
    "Driver": render_driver_form,
    "Security Guard": render_security_guard_form,
}


def main():
    inject_css()
    render_brand_bar()
    float_init()

    user = get_current_user()

    # 1. Organization Role -> Organization Dashboard
    if is_organization_user() and user:
        render_organization_dashboard(user)
        render_chatbot()
        return

    # 2. Admin Role -> Admin Dashboard
    if is_admin_user() and user:
        render_admin_dashboard(user)
        render_chatbot()
        return

    # 3. Normal User or Public Visitor Views
    current_view = st.session_state.get("current_view")

    # Explicit view manipulation guards
    if current_view == "admin" and not (is_admin_user() and user):
        st.error("⛔ **Access Denied**: Platform Administrator credentials required.")
        st.session_state.current_view = "home"
        st.rerun()
        return

    if current_view == "organization" and not (is_organization_user() and user):
        st.error("⛔ **Access Denied**: Organization credentials required.")
        st.session_state.current_view = "home"
        st.rerun()
        return

    if current_view == "auth":
        render_auth_screen()
        render_chatbot()
        return

    if current_view == "my_requests":
        if user:
            render_my_requests(user)
        else:
            st.session_state.current_view = "auth"
            st.rerun()
        render_chatbot()
        return

    if "chat_open" not in st.session_state:
        st.session_state.chat_open = False

    if "messages" not in st.session_state:
        st.session_state.messages = []

    selected = st.session_state.selected_service
    if selected is None:
        render_home()
    else:
        SERVICE_RENDERERS[selected]()

    render_chatbot()


if __name__ == "__main__":
    main()