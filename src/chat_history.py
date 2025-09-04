import os
import json
import google.generativeai as genai

def find_project_root(marker_file='pyproject.toml') -> str:
    """Find the project root by searching upwards for the marker file."""
    current_dir = os.path.dirname(os.path.abspath(__file__))
    while current_dir != os.path.dirname(current_dir):  # Stop at system root
        if os.path.exists(os.path.join(current_dir, marker_file)):
            return current_dir
        current_dir = os.path.dirname(current_dir)
    raise FileNotFoundError("Project root not found. Ensure 'pyproject.toml' exists at the root.")

project_root = find_project_root()
HISTORY_FILE = os.path.join(project_root, 'knowledge', 'chat_history.json')

genai.configure(api_key=os.getenv('GEMINI_API_KEY'))

class ChatHistory:
    @staticmethod
    def load_history():
        if os.path.exists(HISTORY_FILE):
            with open(HISTORY_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        return []

    @staticmethod
    def save_history(history):
        os.makedirs(os.path.dirname(HISTORY_FILE), exist_ok=True)
        with open(HISTORY_FILE, 'w', encoding='utf-8') as f:
            json.dump(history, f, indent=2)

    @staticmethod
    def summarize(history):
        if len(history) < 2:
            return "No significant history."
        model = genai.GenerativeModel('gemini-1.5-flash')
        prompt = "Summarize this chat history concisely (100-300 tokens), focusing on key topics, user intents, and recent exchanges:\n" + json.dumps(history)
        response = model.generate_content(prompt)
        return response.text.strip() or "Summary failed."