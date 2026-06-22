import streamlit as st

from storage.excel_handler import create_excel_if_not_exists
from forms.Cook_Requirement import render_cook_form
from forms.Driver_Requirement import render_driver_form
from forms.Security_Gaurd_Requirement import render_security_guard_form

st.set_page_config(
    page_title="HomeDesk — Hire Trusted Help",
    page_icon="🗝️",
    layout="wide",
    initial_sidebar_state="collapsed",
)

create_excel_if_not_exists()

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

        /* --- Token stub: signature element --- */
        .token-stub {
            background: var(--card);
            border: 1px solid var(--border);
            border-radius: 14px;
            padding: 1.4rem 1.6rem 1.2rem;
            box-shadow: 0 18px 40px -24px rgba(22,36,63,0.35);
            position: relative;
            max-width: 280px;
            margin-left: auto;
        }
        .token-stub .eyebrow {
            font-size: 0.68rem;
            text-transform: uppercase;
            letter-spacing: 0.1em;
            color: var(--muted);
        }
        .token-stub .number {
            font-family: 'IBM Plex Mono', monospace;
            font-size: 1.9rem;
            font-weight: 600;
            color: var(--ink);
            margin: 0.15rem 0 0.9rem;
        }
        .token-stub .perforation {
            border-top: 2px dashed var(--border);
            position: relative;
            margin: 0 -1.6rem;
        }
        .token-stub .perforation::before,
        .token-stub .perforation::after {
            content: "";
            position: absolute;
            top: -8px;
            width: 16px;
            height: 16px;
            border-radius: 50%;
            background: var(--paper);
        }
        .token-stub .perforation::before { left: -8px; }
        .token-stub .perforation::after { right: -8px; }
        .token-stub .status-row {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-top: 0.9rem;
            font-family: 'IBM Plex Mono', monospace;
            font-size: 0.72rem;
        }
        .token-stub .pill {
            background: rgba(31,122,92,0.12);
            color: var(--teal);
            padding: 0.15rem 0.55rem;
            border-radius: 999px;
            font-weight: 600;
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

        /* --- Service cards --- */
        .service-card {
            background: var(--card);
            border: 1px solid var(--border);
            border-radius: 16px;
            padding: 1.6rem 1.2rem 1.1rem;
            text-align: center;
            transition: border-color 0.15s ease, transform 0.15s ease;
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
        }
        .service-card h3 { font-size: 1.08rem; margin: 0 0 0.3rem; }
        .service-card p { font-size: 0.85rem; color: var(--muted); margin: 0; min-height: 2.4rem; }

        div[class*="st-key-card_"]:hover .service-card {
            border-color: var(--amber-deep);
            transform: translateY(-3px);
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
        </style>
        """,
        unsafe_allow_html=True,
    )


def render_brand_bar():
    st.markdown(
        """
        <div class="brand-bar">
            <div class="brand">Home<span>Desk</span></div>
            <div class="tagline">Verified household help, on your terms</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_hero():
    left, right = st.columns([1.3, 1], gap="large")
    with left:
        st.markdown(
            """
            <div class="hero-eyebrow">Household staffing, simplified</div>
            <div class="hero-title">Tell us who you need.<br>We'll take it from there.</div>
            <p class="hero-sub">
                Share a few details about the help you're looking for —
                a cook, a driver, or a security guard — and your request
                joins our queue with its own tracked token.
            </p>
            """,
            unsafe_allow_html=True,
        )
    with right:
        st.markdown(
            """
            <div class="token-stub">
                <div class="eyebrow">Sample token</div>
                <div class="number">No. 014</div>
                <div class="perforation"></div>
                <div class="status-row">
                    <span>SECURITY GUARD</span>
                    <span class="pill">NEW</span>
                </div>
            </div>
            """,
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
        '<div class="footer-note">No spam calls. Just genuine requests, routed straight to your inbox.</div>',
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

    selected = st.session_state.selected_service
    if selected is None:
        render_home()
    else:
        SERVICE_RENDERERS[selected]()


if __name__ == "__main__":
    main()