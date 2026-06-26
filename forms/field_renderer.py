import streamlit as st
from datetime import date


def render_field(field):
    """Draws one Streamlit widget based on a schema field dict."""

    key = field["key"]
    label = field["label"]
    field_type = field["type"]

    if field_type == "text":

        # Mobile Number
        if key == "Mobile":
            
            return st.text_input(
                label,
                max_chars=field.get("max_chars"),
                key=key
            )

        # Pincode
        elif key == "Pincode":
            return st.text_input(
                label,
                max_chars=6,
                key=key
            )

        # Normal Text Field
        return st.text_input(
            label,
            key=key
        )

    elif field_type == "date":
        return str(
            st.date_input(
                label,
                value=date.today(),
                key=key
            )
        )

    elif field_type == "select":
        return st.selectbox(
            label,
            field["options"],
            key=key
        )

    elif field_type == "number":
        return st.number_input(
            label,
            min_value=field.get("min", 0),
            max_value=field.get("max", None),
            step=field.get("step", 1),
            key=key
        )

    elif field_type == "textarea":
        return st.text_area(
            label,
            key=key
        )

    raise ValueError(f"Unknown field type '{field_type}' for field '{key}'")