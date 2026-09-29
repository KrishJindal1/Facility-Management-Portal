"""
Excel storage and export handler.
PostgreSQL is the application's primary source of truth.
This module provides Excel generation, reporting export, and local sync.
"""
from datetime import datetime
import io
import logging
from pathlib import Path
from typing import Optional, Dict, Any
from openpyxl import load_workbook, Workbook
from openpyxl.utils import get_column_letter

from storage.config import EXCEL_FILE
from database.repository import (
    init_database,
    save_lead_to_db,
    get_latest_lead_by_mobile,
    get_all_leads_for_export,
)

logger = logging.getLogger(__name__)

Sheets = {
    "All Leads": [
        "Lead ID",
        "Date Time",
        "Name",
        "Mobile",
        "Service Type",
        "City",
        "Budget",
        "Status",
    ],
    "Cook": [
        "Lead ID",
        "Date Time",
        "Name",
        "Mobile",
        "Email",
        "Address",
        "City",
        "State",
        "Pincode",
        "Start Date",
        "Preferred Timing",
        "Budget",
        "Cuisine Type",
        "Meals Per Day",
        "Additional Notes",
        "Status",
    ],
    "Driver": [
        "Lead ID",
        "Date Time",
        "Name",
        "Mobile",
        "Email",
        "Address",
        "City",
        "State",
        "Pincode",
        "Start Date",
        "Preferred Timing",
        "Budget",
        "Vehicle Type",
        "License Required",
        "Additional Notes",
        "Status",
    ],
    "Security Guard": [
        "Lead ID",
        "Date Time",
        "Name",
        "Mobile",
        "Email",
        "Address",
        "City",
        "State",
        "Pincode",
        "Start Date",
        "Preferred Timing",
        "Budget",
        "Day/Night Shift",
        "Residential/Commercial",
        "Additional Notes",
        "Status",
    ],
}


def create_excel_if_not_exists():
    """Initializes the database schema and creates an empty Excel file if missing."""
    # Initialize PostgreSQL / database layer first
    init_database()

    target_file = Path(EXCEL_FILE)
    if target_file.exists():
        return

    target_file.parent.mkdir(parents=True, exist_ok=True)
    wb = Workbook()
    wb.remove(wb.active)  # Remove default sheet

    for sheet_name, headers in Sheets.items():
        sheet = wb.create_sheet(title=sheet_name)
        sheet.append(headers)

    wb.save(target_file)
    wb.close()


def auto_adjust_columns(ws):
    """Adjusts column widths dynamically based on content."""
    for column in ws.columns:
        max_length = 0
        column_letter = get_column_letter(column[0].column)
        for cell in column:
            if cell.value is not None:
                max_length = max(max_length, len(str(cell.value)))
        ws.column_dimensions[column_letter].width = max(max_length + 3, 12)


def append_to_sheet(sheet_name: str, data: Dict[str, Any]):
    """Appends a row to an Excel worksheet (reporting cache)."""
    target_file = Path(EXCEL_FILE)
    if not target_file.exists():
        create_excel_if_not_exists()

    try:
        wb = load_workbook(target_file)
        if sheet_name not in wb.sheetnames:
            ws = wb.create_sheet(title=sheet_name)
            ws.append(Sheets.get(sheet_name, list(data.keys())))
        else:
            ws = wb[sheet_name]

        headers = [cell.value for cell in ws[1]]
        row = [data.get(header, "") for header in headers]
        ws.append(row)
        auto_adjust_columns(ws)
        wb.save(target_file)
        wb.close()
    except Exception as exc:
        logger.warning("Could not append row to Excel reporting cache: %s", exc)


def save_lead(
    service_name: str,
    lead_data: Dict[str, Any],
    organization_id: Optional[int] = None,
) -> Dict[str, Any]:
    """
    Saves a lead to PostgreSQL scoped to an organization as the primary source of truth,
    then updates the Excel export file for reporting.
    """
    lead_data.setdefault("Date Time", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    lead_data.setdefault("Status", "New")

    # 1. Primary write: PostgreSQL database with tenant isolation
    try:
        saved = save_lead_to_db(service_name, lead_data, organization_id=organization_id)
        lead_data.update(saved)
    except Exception as exc:
        logger.error("Database save failed: %s", exc)
        raise

    # 2. Secondary write: Excel reporting file (kept for export compatibility)
    try:
        append_to_sheet(service_name, lead_data)
        append_to_sheet(
            "All Leads",
            {
                "Lead ID": lead_data["Lead ID"],
                "Date Time": lead_data["Date Time"],
                "Name": lead_data["Name"],
                "Mobile": lead_data["Mobile"],
                "Service Type": service_name,
                "City": lead_data["City"],
                "Budget": lead_data["Budget"],
                "Status": lead_data["Status"],
            },
        )
    except Exception as exc:
        logger.warning("Excel sync encountered error (database write succeeded): %s", exc)

    return lead_data


def find_latest_request_by_mobile(
    mobile: str,
    organization_id: Optional[int] = None,
) -> Optional[Dict[str, Any]]:
    """
    Retrieves the latest request for a mobile number strictly within the specified tenant.
    Queries PostgreSQL first; falls back to Excel if database is unreachable.
    """
    mobile_clean = str(mobile or "").strip()
    if not mobile_clean:
        return None

    # Primary: Query PostgreSQL with tenant filter
    try:
        db_lead = get_latest_lead_by_mobile(mobile_clean, organization_id=organization_id)
        if db_lead:
            return db_lead
    except Exception as exc:
        logger.warning("Database lookup failed, falling back to Excel: %s", exc)

    # Fallback: Query Excel if database did not find or failed
    target_file = Path(EXCEL_FILE)
    if not target_file.exists():
        return None

    try:
        workbook = load_workbook(target_file, data_only=True)
        for sheet_name in ("Cook", "Driver", "Security Guard", "All Leads"):
            if sheet_name not in workbook.sheetnames:
                continue

            sheet = workbook[sheet_name]
            headers = [cell.value for cell in sheet[1]] if sheet.max_row >= 1 else []
            if "Mobile" not in headers:
                continue

            mobile_col = headers.index("Mobile") + 1
            for row in range(sheet.max_row, 1, -1):
                cell_val = str(sheet.cell(row, mobile_col).value or "").strip()
                if cell_val == mobile_clean:
                    data = {}
                    for col, header in enumerate(headers, start=1):
                        data[header] = sheet.cell(row, col).value
                    data["Service"] = sheet_name if sheet_name != "All Leads" else data.get("Service Type", "Cook")
                    workbook.close()
                    return data

        workbook.close()
    except Exception as exc:
        logger.error("Excel fallback search failed: %s", exc)

    return None


def export_leads_to_excel(
    organization_id: Optional[int] = None,
    target_path: Optional[Path] = None,
) -> Path:
    """
    Reads leads strictly for the given tenant from PostgreSQL and generates
    an Excel workbook containing all 4 sheets: All Leads, Cook, Driver, Security Guard.
    """
    export_file = Path(target_path or EXCEL_FILE)
    export_file.parent.mkdir(parents=True, exist_ok=True)

    all_data = get_all_leads_for_export(organization_id=organization_id)

    wb = Workbook()
    wb.remove(wb.active)  # Remove default sheet

    for sheet_name, headers in Sheets.items():
        ws = wb.create_sheet(title=sheet_name)
        ws.append(headers)

        rows = all_data.get(sheet_name, [])
        for item in rows:
            row = [item.get(h, "") for h in headers]
            ws.append(row)

        auto_adjust_columns(ws)

    wb.save(export_file)
    wb.close()
    return export_file


def get_excel_export_bytes(organization_id: Optional[int] = None) -> bytes:
    """
    Generates the Excel file in-memory strictly for the given tenant from PostgreSQL
    and returns bytes for direct browser download in Streamlit.
    """
    all_data = get_all_leads_for_export(organization_id=organization_id)
    wb = Workbook()
    wb.remove(wb.active)

    for sheet_name, headers in Sheets.items():
        ws = wb.create_sheet(title=sheet_name)
        ws.append(headers)

        rows = all_data.get(sheet_name, [])
        for item in rows:
            row = [item.get(h, "") for h in headers]
            ws.append(row)

        auto_adjust_columns(ws)

    buffer = io.BytesIO()
    wb.save(buffer)
    wb.close()
    buffer.seek(0)
    return buffer.getvalue()