from firebase_client import mark_task_complete

def mark_complete(task_id: str, completed_at: str = None) -> tuple[bool, str]:
    success = mark_task_complete(task_id)
    if success:
        return True, f"Marked task '{task_id}' as complete{(f' at {completed_at}' if completed_at else '')}."
    return False, f"Failed to mark task '{task_id}' complete."