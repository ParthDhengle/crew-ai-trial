# src/tools/operations/tasks/create_task.py (updated)
from firebase_client import add_task

def create_task(title: str, description: str = None, deadline: str = None, priority: str = "Medium", tags: list = None) -> tuple[bool, str]:
    try:
        task_id = add_task(title=title, description=description, due_date=deadline, priority=priority, related_files=tags or [])
        return True, f"Task created with ID: {task_id}"
    except Exception as e:
        return False, f"Error creating task: {str(e)}"