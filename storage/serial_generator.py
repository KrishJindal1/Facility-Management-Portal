from openpyxl import load_workbook
from storage.config import EXCEL_FILE


def generate_serial(service_name):

    wb = load_workbook(EXCEL_FILE)
    ws = wb[service_name]

    prefix_map = {
        "Cook": "Cook",
        "Driver": "Driver",
        "Security Guard": "Security"
    }

    prefix = prefix_map[service_name]

    used_numbers = set()

    # Skip the header row
    for row in ws.iter_rows(min_row=2, values_only=True):

        lead_id = row[0]

        if not lead_id:
            continue

        try:
            number = int(str(lead_id).split("-")[-1])
            used_numbers.add(number)
        except (ValueError, IndexError):
            continue

    wb.close()

    serial_number = 1

    while serial_number in used_numbers:
        serial_number += 1

    return f"{prefix}-{serial_number:03d}"