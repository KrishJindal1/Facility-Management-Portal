import streamlit as st
from streamlit_float import *
from storage.excel_handler import create_excel_if_not_exists
from forms.Cook_Requirement import render_cook_form
from forms.Driver_Requirement import render_driver_form
from forms.Security_Gaurd_Requirement import render_security_guard_form
from component.chatbot_widget import render_chatbot
from utils.local_storage import get_request, save_request, delete_request
from services.lead_lookup import find_lead_by_mobile

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
                        st.caption(
                            "We couldn't load the full details for this "
                            "request right now — please check back later."
                        )

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
                                '<div class="field-hint warning">⚠ No request found for that number</div>',
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
    float_init()
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