# Updated src/chat_history.py
# Now uses Firebase for storage, with session-based history (default to global session if none specified).
# Limits to last 20 turns for token efficiency.
# Summarization remains local via Gemini for speed.

import os
import json
from datetime import datetime
import google.generativeai as genai
from common_functions.Find_project_root import find_project_root
import uuid
from firebase_client import add_chat_message, get_chat_history  # Updated imports
from firebase_client import add_chat_message
import os
project_root = find_project_root()
genai.configure(api_key=os.getenv('GEMINI_API_KEY1'))
import asyncio

async def save_chat_message(session_id: str, uid: str, role: str, content: str, timestamp: str) -> str:
    """
    Save a single chat message to Firebase and return the session ID.
    Wrapper around add_chat_message to maintain compatibility with app.py.
    """
    if session_id is None:
        session_id = f"session_{datetime.now().strftime('%Y-%m-%d')}_{uuid.uuid4().hex[:8]}"
    await asyncio.get_event_loop().run_in_executor(
        None, lambda: add_chat_message(uid, role, content, session_id, timestamp)
    )
    print(f"Saved message to Firebase (session: {session_id}, role: {role}).")
    return session_id

class ChatHistory:
    @staticmethod
    def get_session_id():
        # Use a default session ID based on today + short UUID for persistence across runs.
        today = datetime.now().strftime('%Y-%m-%d')
        return f"session_{today}_{uuid.uuid4().hex[:8]}"

    @staticmethod
    def load_history(session_id: str = None):
        if session_id is None:
            session_id = ChatHistory.get_session_id()
        history_docs = get_chat_history(session_id)
        history_docs.sort(key=lambda x: x.get('timestamp', ''))
        history = [{"role": doc["role"], "content": doc["content"]} for doc in history_docs[-16:]]  # Up to 16 for 8 pairs
        if len(history) % 2 == 1:
            history = history[:-1]
        print(f"Loaded {len(history)//2} turns from Firebase (session: {session_id}).")
        return history

    @staticmethod
    def save_history(history: list, session_id: str = None, uid: str = None):
        if session_id is None:
            session_id = ChatHistory.get_session_id()
        if uid is None:
            uid = os.getenv("USER_ID", "default_uid")  # Fallback; in app.py, pass explicitly
        for entry in history:
            add_chat_message(uid, entry["role"], entry["content"], session_id)  # <- Added uid
        print(f"Saved history to Firebase (session: {session_id}).")
    
    @staticmethod
    def summarize(history: list):
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