import re
import streamlit as st
from datetime import date


def _is_valid_mobile(value):
    return bool(re.fullmatch(r"\d{10}", value or ""))


def _is_valid_pincode(value):
    return bool(re.fullmatch(r"\d{6}", value or ""))


def _hint(message, tone="warning"):
    """A small, brand-colored inline hint under a field — kept subtle and
    on-theme rather than Streamlit's default red alert box."""
    st.markdown(
        f'<div class="field-hint {tone}">{message}</div>',
        unsafe_allow_html=True,
    )


def render_field(field):
    """Draws one Streamlit widget based on a schema field dict.

    Supported optional schema keys (all optional, all backward compatible):
      - "help": tooltip text shown on the (i) hover icon
      - "placeholder": placeholder copy for text/number/select/textarea
      - "default": default value for date fields (defaults to today)
      - "min_date" / "max_date": bounds for date fields
      - "show_char_count": show a live character counter under a textarea
    """

    key = field["key"]
    label = field["label"]
    field_type = field["type"]
    help_text = field.get("help")

    if field_type == "text":

        # Mobile Number
        if key == "Mobile":
            value = st.text_input(
                label,
                max_chars=field.get("max_chars", 10),
                key=key,
                placeholder=field.get("placeholder", "10-digit mobile number"),
                help=help_text or "We'll only use this to confirm your request.",
            )
            if value and not _is_valid_mobile(value):
                _hint("⚠ Enter a valid 10-digit mobile number")
            return value

        # Pincode
        elif key == "Pincode":
            value = st.text_input(
                label,
                max_chars=6,
                key=key,
                placeholder=field.get("placeholder", "6-digit area pincode"),
                help=help_text,
            )
            if value and not _is_valid_pincode(value):
                _hint("⚠ Pincode should be exactly 6 digits")
            return value

        # Normal Text Field
        return st.text_input(
            label,
            key=key,
            placeholder=field.get("placeholder"),
            help=help_text,
        )

    elif field_type == "date":
        return str(
            st.date_input(
                label,
                value=field.get("default", date.today()),
                min_value=field.get("min_date"),
                max_value=field.get("max_date"),
                key=key,
                help=help_text,
            )
        )

    elif field_type == "select":
        return st.selectbox(
            label,
            field["options"],
            key=key,
            help=help_text,
        )

    elif field_type == "number":
        return st.number_input(
            label,
            min_value=field.get("min", 0),
            max_value=field.get("max", None),
            step=field.get("step", 1),
            key=key,
            help=help_text,
        )

    elif field_type == "textarea":
        value = st.text_area(
            label,
            key=key,
            placeholder=field.get("placeholder", "Add any details we should know..."),
            help=help_text,
        )
        if field.get("show_char_count") and value:
            st.caption(f"{len(value)} characters")
        return value

    raise ValueError(f"Unknown field type '{field_type}' for field '{key}'")