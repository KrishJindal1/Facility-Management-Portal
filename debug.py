from openpyxl import load_workbook

wb = load_workbook("data/requirements.xlsx")

for sheet in wb.sheetnames:
    print(f"\n--- {sheet} ---")

    ws = wb[sheet]

    for row in ws.iter_rows(values_only=True):
        print(row)