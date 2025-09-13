from firebase_client import add_task, USER_ID
import json

def create_task(title: str, user_id: str = None, description: str = None, due_date: str = None, estimate_min: int = None, related_files: list = None) -> tuple[bool, str]:
    user_id = user_id or USER_ID
    doc_id = add_task(title, description, due_date, related_files=related_files)  # estimate_min not in add_task; extend if needed
    return True, f"Created task '{title}' (ID: {doc_id}) for user '{user_id}' due {due_date or 'TBD'}."