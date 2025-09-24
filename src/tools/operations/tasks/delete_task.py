# src/tools/operations/tasks/delete_task.py (updated)
from firebase_client import delete_task_by_user

def delete_task(task_id: str) -> tuple[bool, str]:
    success = delete_task_by_user(task_id)
    return success, "Task deleted successfully" if success else "Task not found"