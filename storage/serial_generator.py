from openpyxl import load_workbook
from pathlib import Path

EXCEL_FILE = Path("data/requirements.xlsx")

def generate_serial():

    wb = load_workbook(EXCEL_FILE)

    ws = wb["All Leads"]

    serial = ws.max_row

    wb.close()

    return serial