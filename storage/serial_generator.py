from openpyxl import load_workbook
from storage.config import EXCEL_FILE


def generate_serial(service_name):

    

    wb = load_workbook(EXCEL_FILE)

    ws = wb[service_name]

    serial_number = ws.max_row

    wb.close()

    prefix_map = {
        "Cook": "Cook",
        "Driver": "Driver",
        "Security Guard": "Security"
    }

    prefix = prefix_map[service_name]

    return f"{prefix}-{serial_number:03d}"