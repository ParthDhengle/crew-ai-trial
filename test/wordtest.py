# requirements: pywin32
# install via: pip install pywin32

import win32com.client

def create_and_open_word():
    # Hardcoded content
    content = [
        "Welcome to My Document\n\nThis is the introduction section. Created using Python automation.",
        "About pywin32:\n- Automates Microsoft Office\n- Can control Word, Excel, PowerPoint\n- Very useful for repetitive tasks"
    ]

    # Start Word
    word = win32com.client.Dispatch("Word.Application")
    word.Visible = True

    # Create a new document
    doc = word.Documents.Add()

    # Add paragraphs with content
    for text in content:
        para = doc.Paragraphs.Add()
        para.Range.Text = text
        para.Range.InsertParagraphAfter()

    print("✅ Word document created and opened (not saved).")

if __name__ == "__main__":
    create_and_open_word()
