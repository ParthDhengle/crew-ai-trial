# src/tools/operations/office/create_word.py
import win32com.client as win32
from ....utils.logger import setup_logger
import os

logger = setup_logger()

def create_word_doc(content: str, path: str = None) -> tuple[bool, str]:
    """Create or edit Word document using pywin32 (Windows only)."""
    try:
        if os.name != 'nt':
            logger.warning("Word automation: Non-Windows OS detected.")  # Log
            return False, "Word automation supported on Windows only."
        
        word = win32.Dispatch("Word.Application")
        word.Visible = True
        doc = word.Documents.Add()
        para = doc.Paragraphs.Add()
        para.Range.Text = content
        if path:
            doc.SaveAs(path)
            logger.info(f"Saved Word doc to {path}")  # Log save
        else:
            logger.info("Word doc created (not saved).")  # Log
        return True, "Word document created/opened."
    except Exception as e:
        logger.error(f"Word create error: {str(e)}")  # Log error
        return False, str(e)