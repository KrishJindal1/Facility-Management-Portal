import streamlit as st

from storage.excel_handler import save_lead
from utils.validators import validate_form
from forms.driver_schema import DRIVER_FIELDS, SERVICE_NAME
from forms.field_renderer import render_field


def render_driver_form():
    st.subheader("Driver Service Requirement")

    if st.button("← Back", key="nav_back"):
        st.session_state.selected_service = None
        st.rerun()

    with st.form("driver_form", clear_on_submit=True):
        lead_data = {}
        for field in DRIVER_FIELDS:
            lead_data[field["key"]] = render_field(field)

        submitted = st.form_submit_button("Submit")

    if submitted:
        errors = validate_form(lead_data)

        if errors:
            for error in errors:
                st.error(error)
        else:
            save_lead(SERVICE_NAME, lead_data)
            st.success("Your requirement has been submitted successfully!")