from storage.config import EXCEL_FILE
from datetime import datetime
from openpyxl import load_workbook, Workbook



Sheets = {
    "All Leads": [
        "Lead ID",
        "Date Time",
        "Name",
        "Mobile",
        "Service Type",
        "City",
        "Budget",
        "Status"
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
        "Status"
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
        "Status"
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
        "Status"
    ]
}


def create_excel_if_not_exists():
        if EXCEL_FILE.exists():
         return
        EXCEL_FILE.parent.mkdir(parents=True, exist_ok=True)
        wb = Workbook()
        wb.remove(wb.active)  # Remove the default sheet created by openpyxl
        for sheet_name, headers in Sheets.items():
            sheet = wb.create_sheet(title=sheet_name)
            sheet.append(headers)
        wb.save(EXCEL_FILE)

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

    wb = load_workbook(EXCEL_FILE)
    ws = wb[sheet_name]
    headers = [cell.value for cell in ws[1]]  # Get headers from the first row
    row = [data.get(header, "") for header in headers]  # Ensure data matches header order
    ws.append(row)
    auto_adjust_columns(ws)
    wb.save(EXCEL_FILE)
    wb.close()


def save_lead(service_name, lead_data):
    # Auto-fill Lead ID, Date Time, and Status if the caller didn't
    # already supply them.
    

    lead_data.setdefault("Date Time", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    lead_data.setdefault("Status", "New")

    print("Saving service sheet")
    append_to_sheet(service_name, lead_data)

    print("Saving All Leads")
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
            "Status": lead_data["Status"]
        }
    )


def find_latest_request_by_mobile(mobile):

    workbook = load_workbook(EXCEL_FILE)

    for sheet_name in workbook.sheetnames[::-1]:

        sheet = workbook[sheet_name]

        headers = [cell.value for cell in sheet[1]]

        if "Mobile" not in headers:
            continue

        mobile_col = headers.index("Mobile") + 1

        for row in range(sheet.max_row, 1, -1):

            if str(sheet.cell(row, mobile_col).value).strip() == str(mobile).strip():

                data = {}

                for col, header in enumerate(headers, start=1):
                    data[header] = sheet.cell(row, col).value

                data["Service"] = sheet_name

                return data

    workbook.close()

    return None