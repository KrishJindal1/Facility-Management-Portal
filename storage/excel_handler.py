from pathlib import Path
from datetime import datetime
from openpyxl import load_workbook, Workbook

from storage.serial_generator import generate_serial

Excel_File = Path("data/requirements.xlsx")

Sheets = {
    "All Leads": [
        "Serial No",
        "Date Time",
        "Name",
        "Mobile",
        "Service Type",
        "City",
        "Budget",
        "Status"
    ],

    "Cook": [
        "Serial No",
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
        "Status"
    ],

    "Driver": [
        "Serial No",
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
        "Status"
    ],

    "Security Guard": [
        "Serial No",
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
        "Status"
    ]
}


def create_excel_if_not_exists():
        if Excel_File.exists():
         return
        Excel_File.parent.mkdir(parents=True, exist_ok=True)
        wb = Workbook()
        wb.remove(wb.active)  # Remove the default sheet created by openpyxl
        for sheet_name, headers in Sheets.items():
            sheet = wb.create_sheet(title=sheet_name)
            sheet.append(headers)
        wb.save(Excel_File)

def auto_adjust_columns(ws):

    from openpyxl.utils import get_column_letter

    for column in ws.columns:

        max_length = 0

        column_letter = get_column_letter(column[0].column)

        for cell in column:

            if cell.value:

                max_length = max(
                    max_length,
                    len(str(cell.value))
                )

        ws.column_dimensions[column_letter].width = max_length + 3

def append_to_sheet(sheet_name, data):

    wb = load_workbook(Excel_File)
    ws = wb[sheet_name]
    headers = [cell.value for cell in ws[1]]  # Get headers from the first row
    row = [data.get(header, "") for header in headers]  # Ensure data matches header order
    ws.append(row)
    auto_adjust_columns(ws)
    wb.save(Excel_File)
    wb.close()


def save_lead(service_name, lead_data):
    # Auto-fill Serial No, Date Time, and Status if the caller didn't
    # already supply them.
    if "Serial No" not in lead_data:
        lead_data["Serial No"] = generate_serial()

    lead_data.setdefault("Date Time", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    lead_data.setdefault("Status", "New")

    print("Saving service sheet")
    append_to_sheet(service_name, lead_data)

    print("Saving All Leads")
    append_to_sheet(
        "All Leads",
        {
            "Serial No": lead_data["Serial No"],
            "Date Time": lead_data["Date Time"],
            "Name": lead_data["Name"],
            "Mobile": lead_data["Mobile"],
            "Service Type": service_name,
            "City": lead_data["City"],
            "Budget": lead_data["Budget"],
            "Status": lead_data["Status"]
        }
    )