import os
import json
from datetime import date
import google.generativeai as genai
from common_functions.Find_project_root import find_project_root

project_root = find_project_root()
SHORT_TERM_DIR = os.path.join(project_root, 'knowledge', 'memory', 'short_term')
genai.configure(api_key=os.getenv('GEMINI_API_KEY1'))

class ChatHistory:
    @staticmethod
    def get_history_file():
        today = date.today().isoformat()
        return os.path.join(SHORT_TERM_DIR, f'session_{today}.json')

    @staticmethod
    def load_history():
        history_file = ChatHistory.get_history_file()
        if os.path.exists(history_file):
            with open(history_file, 'r', encoding='utf-8') as f:
                content = f.read().strip()
                if content:
                    try:
                        history = json.loads(content)
                        # Limit to last 20 turns for token budget
                        return history[-20:]
                    except json.JSONDecodeError as e:
                        print(f"Warning: Invalid JSON in {history_file} ({e}). Returning empty history.")
                        return []
                else:
                    print(f"Warning: Empty file {history_file}. Returning empty history.")
                    return []
        print(f"Warning: History file not found {history_file}. Returning empty history.")
        return []

    @staticmethod
    def save_history(history):
        history_file = ChatHistory.get_history_file()
        os.makedirs(os.path.dirname(history_file), exist_ok=True)
        with open(history_file, 'w', encoding='utf-8') as f:
            json.dump(history, f, indent=2)

    @staticmethod
    def summarize(history):
        if len(history) < 2:
            return "No significant history."
        model = genai.GenerativeModel('gemini-1.5-flash')
        prompt = (
            "Summarize this chat history concisely (100-300 tokens), "
            "focusing on key topics, user intents, and recent exchanges:\n"
            + json.dumps(history)
        )
        try:
            response = model.generate_content(prompt)
            summary = response.text.strip() or "Summary failed."
            # Approximate token check (len / 0.75 ~ tokens)
            if len(summary) > 400:  # ~300 tokens
                summary = summary[:400] + "... (truncated)"
            return summary
        except Exception as e:
            print(f"Error summarizing history: {e}. Returning default summary.")
            return "History summary unavailable."