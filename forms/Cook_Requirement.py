import streamlit as st

from storage.excel_handler import save_lead
from utils.validators import validate_form
from forms.cook_schema import COOK_FIELDS, SERVICE_NAME
from forms.field_renderer import render_field
from storage.serial_generator import generate_serial

def render_cook_form():
    st.subheader("Cook Service Requirement")

    if st.button("← Back", key="nav_back"):
        st.session_state.selected_service = None
        st.rerun()

    with st.form("cook_form"):
        lead_data = {}
        for field in COOK_FIELDS:
            lead_data[field["key"]] = render_field(field)

        submitted = st.form_submit_button("Submit")

    if submitted:
        errors = validate_form(lead_data)

        if errors:
            for error in errors:
                st.error(error)
        else:
            lead_data["Lead ID"] = generate_serial(SERVICE_NAME)
            save_lead(SERVICE_NAME, lead_data)
            st.success("Your requirement has been submitted successfully!")