# src/tools/operations/tasks/update_task.py (updated)
from firebase_client import update_task_by_user

def update_task(task_id: str, status: str = None, title: str = None, description: str = None, deadline: str = None, priority: str = None, tags: list = None) -> tuple[bool, str]:
    updates = {}
    if status: updates["status"] = status
    if title: updates["title"] = title
    if description: updates["description"] = description
    if deadline: updates["due_date"] = deadline
    if priority: updates["priority"] = priority
    if tags: updates["related_files"] = tags
    success = update_task_by_user(task_id, updates)
    return success, "Task updated successfully" if success else "Task not found"