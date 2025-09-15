# requirements: pywin32
# install via: pip install pywin32

import win32com.client

def create_and_open_excel():
    # Hardcoded table-like content
    content = [
        ["Name", "Role", "Score"],
        ["Parth", "Developer", 95],
        ["Alex", "Designer", 88],
        ["Sam", "Tester", 91],
    ]

    # Start Excel
    excel = win32com.client.Dispatch("Excel.Application")
    excel.Visible = True

    # Create a new workbook
    workbook = excel.Workbooks.Add()
    sheet = workbook.Sheets(1)  # First sheet

    # Write content into cells
    for row_idx, row in enumerate(content, start=1):
        for col_idx, value in enumerate(row, start=1):
            sheet.Cells(row_idx, col_idx).Value = value

    print("✅ Excel workbook created and opened (not saved).")

if __name__ == "__main__":
    create_and_open_excel()
