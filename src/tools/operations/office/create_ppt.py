# src/tools/operations/office/create_ppt.py
import win32com.client as win32
from ....utils.logger import setup_logger
import os

logger = setup_logger()

def create_ppt(slides_json: str, path: str = None) -> tuple[bool, str]:
    """Create PPT with slides from JSON (e.g., [{'title': 'Slide1', 'content': 'Text'}]). Uses pywin32 (Windows only)."""
    try:
        if os.name != 'nt':
            logger.warning("PPT automation: Non-Windows OS detected.")
            return False, "PPT automation supported on Windows only."
        
        slides = json.loads(slides_json)  # Expect list of dicts
        ppt = win32.Dispatch("PowerPoint.Application")
        ppt.Visible = True
        presentation = ppt.Presentations.Add()
        for slide_data in slides:
            slide = presentation.Slides.Add(presentation.Slides.Count + 1, 1)  # Title and Content layout
            slide.Shapes[1].TextFrame.TextRange.Text = slide_data.get('title', 'Title')
            slide.Shapes[2].TextFrame.TextRange.Text = slide_data.get('content', 'Content')
        if path:
            presentation.SaveAs(path)
            logger.info(f"Saved PPT to {path}")
        else:
            logger.info("PPT created (not saved).")
        return True, "PPT created/opened."
    except Exception as e:
        logger.error(f"PPT create error: {str(e)}")
        return False, str(e)