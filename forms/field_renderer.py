import streamlit as st
from datetime import date


def render_field(field):
    """Draws one Streamlit widget based on a schema field dict."""
    key = field["key"]
    label = field["label"]
    field_type = field["type"]

    if field_type == "text":
        return st.text_input(label)
    if field_type == "date":
        return str(st.date_input(label, value=date.today()))
    if field_type == "select":
        return st.selectbox(label, field["options"])
    if field_type == "number":
        return st.number_input(
            label,
            min_value=field.get("min", 0),
            max_value=field.get("max", None),
            step=field.get("step", 1),
        )
    if field_type == "textarea":
        return st.text_area(label)

    raise ValueError(f"Unknown field type '{field_type}' for field '{key}'")