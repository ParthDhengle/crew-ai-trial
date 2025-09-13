from firebase_client import update_task

def update_task(task_id: str, fields: dict) -> tuple[bool, str]:
    success = update_task(task_id, fields)
    if success:
        return True, f"Updated task '{task_id}' with fields: {fields}"
    return False, f"Failed to update task '{task_id}'"