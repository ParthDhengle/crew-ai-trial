import os
import json
import google.generativeai as genai

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
HISTORY_FILE = os.path.join(PROJECT_ROOT, 'knowledge', 'chat_history.json')

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