# requirements: pywin32
# install via: pip install pywin32

import win32com.client

def create_and_open_ppt():
    # Hardcoded content
    content = {
        "Slide 1": "Welcome to My Presentation\nThis is the introduction slide.",
        "Slide 2": "About Python-PPTX\n- Create and edit PowerPoint files\n- Automate presentations easily!"
    }

    # Start PowerPoint
    ppt = win32com.client.Dispatch("PowerPoint.Application")
    ppt.Visible = True

    # Create a new presentation
    presentation = ppt.Presentations.Add()

    # Add slides with text
    for title, text in content.items():
        slide = presentation.Slides.Add(presentation.Slides.Count + 1, 1)  # 1 = ppLayoutText
        slide.Shapes[0].TextFrame.TextRange.Text = title   # Title
        slide.Shapes[1].TextFrame.TextRange.Text = text    # Content

    print("✅ PPT created and opened in Microsoft PowerPoint (not saved, you can save manually).")

if __name__ == "__main__":
    create_and_open_ppt()
