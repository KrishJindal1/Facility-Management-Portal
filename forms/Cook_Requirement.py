import streamlit as st

from storage.excel_handler import save_lead
from utils.validators import validate_form
from forms.cook_schema import COOK_FIELDS, SERVICE_NAME
from forms.field_renderer import render_field
from storage.serial_generator import generate_serial

# Badge shown in the page header — matches the icon already used for this
# service on the home page card, so the same visual "character" carries
# through into the form itself.
SERVICE_ICON = "🍳"
SERVICE_TAGLINE = (
    "Tell us about your kitchen needs — meal times, cuisine, and "
    "schedule — and we'll match a vetted cook to your household."
)


def _inject_page_css():
    """Styling scoped to this page only, injected locally so nothing
    outside this file needs to change."""
    st.markdown(
        """
        <style>
        /* ---- Page header ---- */
        .form-page-header {
            display: flex;
            align-items: flex-start;
            gap: 1.1rem;
            margin: 0.4rem 0 1.5rem;
        }
        .form-page-header .badge {
            width: 54px;
            height: 54px;
            flex-shrink: 0;
            border-radius: 50%;
            background: linear-gradient(145deg, var(--amber), var(--amber-deep));
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 1.4rem;
            box-shadow: 0 12px 22px -10px rgba(199,127,31,0.55);
        }
        .form-page-header .copy .eyebrow {
            text-transform: uppercase;
            letter-spacing: 0.12em;
            font-size: 0.72rem;
            font-weight: 600;
            color: var(--amber-deep);
            margin-bottom: 0.2rem;
        }
        .form-page-header .copy h2 {
            font-family: 'Fraunces', serif;
            font-size: 1.65rem;
            font-weight: 600;
            color: var(--ink);
            margin: 0 0 0.3rem;
            line-height: 1.2;
        }
        .form-page-header .copy p {
            font-size: 0.92rem;
            color: var(--muted);
            max-width: 36rem;
            line-height: 1.55;
            margin: 0;
        }

        /* ---- Mini token preview, echoing the homepage's signature token-stub ---- */
        .mini-token {
            background: var(--card);
            border: 1px solid var(--border);
            border-radius: 12px;
            padding: 0.85rem 1.1rem;
            margin-bottom: 1.6rem;
            display: flex;
            align-items: center;
            justify-content: space-between;
            gap: 1rem;
        }
        .mini-token .label {
            font-size: 0.68rem;
            text-transform: uppercase;
            letter-spacing: 0.08em;
            color: var(--muted);
            margin-bottom: 0.15rem;
        }
        .mini-token .value {
            font-family: 'IBM Plex Mono', monospace;
            font-weight: 600;
            font-size: 0.92rem;
            color: var(--ink);
        }
        .mini-token .pill {
            background: rgba(31,122,92,0.12);
            color: var(--teal);
            font-family: 'IBM Plex Mono', monospace;
            font-size: 0.66rem;
            font-weight: 600;
            letter-spacing: 0.03em;
            padding: 0.2rem 0.6rem;
            border-radius: 999px;
            white-space: nowrap;
        }

        /* ---- A thin brand-gradient accent along the top of the form ---- */
        div[data-testid="stForm"] {
            position: relative;
            overflow: hidden;
        }
        div[data-testid="stForm"]::before {
            content: "";
            position: absolute;
            top: 0; left: 0; right: 0;
            height: 4px;
            background: linear-gradient(90deg, var(--amber), var(--teal));
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def _render_header():
    st.markdown(
        f"""
        <div class="form-page-header">
            <div class="badge">{SERVICE_ICON}</div>
            <div class="copy">
                <div class="eyebrow">Household Staffing</div>
                <h2>{SERVICE_NAME} Requirement</h2>
                <p>{SERVICE_TAGLINE}</p>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.markdown(
        """
        <div class="mini-token">
            <div>
                <div class="label">Once submitted</div>
                <div class="value">You'll get a tracked request token</div>
            </div>
            <div class="pill">ON SUBMIT</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def _render_field_grid(fields):
    """Lays fields out two-per-row for a tighter, less 'one box per line'
    feel. Textareas always take the full row since they need the space;
    everything else pairs up in the order the schema defines them."""

    lead_data = {}
    pending = None

    for field in fields:
        if field["type"] == "textarea":
            if pending is not None:
                lead_data[pending["key"]] = render_field(pending)
                pending = None
            lead_data[field["key"]] = render_field(field)
            continue

        if pending is None:
            pending = field
            continue

        left, right = st.columns(2, gap="medium")
        with left:
            lead_data[pending["key"]] = render_field(pending)
        with right:
            lead_data[field["key"]] = render_field(field)
        pending = None

    if pending is not None:
        lead_data[pending["key"]] = render_field(pending)

    return lead_data


def render_cook_form():
    _inject_page_css()

    if st.button("← Back", key="nav_back"):
        st.session_state.selected_service = None
        st.rerun()

    _render_header()

    with st.form("cook_form"):
        lead_data = _render_field_grid(COOK_FIELDS)
        submitted = st.form_submit_button("Submit Request", use_container_width=True)

    if submitted:
        errors = validate_form(lead_data)

        if errors:
            for error in errors:
                st.error(error)
        else:
            lead_data["Lead ID"] = generate_serial(SERVICE_NAME)
            save_lead(SERVICE_NAME, lead_data)
            st.success("Your requirement has been submitted successfully!")