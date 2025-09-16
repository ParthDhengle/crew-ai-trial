# src/tools/operations/office/create_excel.py
import win32com.client as win32
from ....utils.logger import setup_logger
import os
logger = setup_logger()

def create_excel(data_json: str, path: str = None) -> tuple[bool, str]:
    """Create Excel with data from JSON (e.g., [['Header1', 'Header2'], [1, 2]]). Uses pywin32 (Windows only)."""
    try:
        if os.name != 'nt':
            logger.warning("Excel automation: Non-Windows OS detected.")
            return False, "Excel automation supported on Windows only."
        
        data = json.loads(data_json)  # Expect list of lists (rows)
        excel = win32.Dispatch("Excel.Application")
        excel.Visible = True
        workbook = excel.Workbooks.Add()
        sheet = workbook.ActiveSheet
        for row_idx, row in enumerate(data, start=1):
            for col_idx, value in enumerate(row, start=1):
                sheet.Cells(row_idx, col_idx).Value = value
        if path:
            workbook.SaveAs(path)
            logger.info(f"Saved Excel to {path}")
        else:
            logger.info("Excel created (not saved).")
        return True, "Excel created/opened."
    except Exception as e:
        logger.error(f"Excel create error: {str(e)}")
        return False, str(e)