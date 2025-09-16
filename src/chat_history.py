# Updated src/chat_history.py
# Now uses Firebase for storage, with session-based history (default to global session if none specified).
# Limits to last 20 turns for token efficiency.
# Summarization remains local via Gemini for speed.
# Added: Logger integration for debug/info.

import os
import json
from datetime import datetime
import google.generativeai as genai
from .common_functions.Find_project_root import find_project_root
import uuid
from .firebase_client import add_chat_message, get_chat_history  # Updated imports
from .utils.logger import setup_logger  # Added logger

project_root = find_project_root()
genai.configure(api_key=os.getenv('GEMINI_API_KEY1'))

logger = setup_logger()  # Initialize logger

class ChatHistory:
    @staticmethod
    def get_session_id():
        # Use a default session ID based on today + short UUID for persistence across runs.
        today = datetime.now().strftime('%Y-%m-%d')
        session_id = f"session_{today}_{uuid.uuid4().hex[:8]}"
        logger.debug(f"Generated session ID: {session_id}")  # Log session ID
        return session_id

    @staticmethod
    def load_history(session_id: str = None):
        if session_id is None:
            session_id = ChatHistory.get_session_id()
        # Fetch recent history (last 50 docs, filter to session if provided)
        history_docs = get_chat_history(session_id)
        # Sort by timestamp and limit to last 20 turns (user/assistant pairs)
        history_docs.sort(key=lambda x: x.get('timestamp', ''))
        history = []
        for doc in history_docs[-40:]:  # Up to 40 to get ~20 pairs
            history.append({
                "role": doc["role"],
                "content": doc["content"]
            })
        # Ensure even number (trim if odd)
        if len(history) % 2 == 1:
            history = history[:-1]
        logger.info(f"Loaded {len(history)//2} turns from Firebase (session: {session_id}).")  # Log load
        return history

    @staticmethod
    def save_history(history: list, session_id: str = None):
        if session_id is None:
            session_id = ChatHistory.get_session_id()
        for entry in history:
            add_chat_message(
                role=entry["role"],
                content=entry["content"],
                session_id=session_id
            )
        logger.info(f"Saved history to Firebase (session: {session_id}).")  # Log save
        return True  # Added return for success check

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
            logger.debug(f"History summarized: {summary[:100]}...")  # Log summary snippet
            return summary
        except Exception as e:
            logger.error(f"Error summarizing history: {e}. Returning default summary.")  # Log error
            return "History summary unavailable."