# src/tools/operations/tasks/mark_complete.py (updated)
from firebase_client import update_task_by_user

def mark_complete(task_id: str) -> tuple[bool, str]:
    success = update_task_by_user(task_id, {"status": "complete"})
    return success, "Task marked complete" if success else "Task not found"