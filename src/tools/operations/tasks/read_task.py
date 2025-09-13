from firebase_client import get_tasks
import json

def read_task(user_id: str, status: str = None, date_range: str = None) -> tuple[bool, str]:  # date_range placeholder (not impl in get_tasks)
    tasks = get_tasks(status)
    tasks_json = json.dumps(tasks, indent=2) if tasks else "[]"
    return True, f"Retrieved {len(tasks)} tasks for user '{user_id}':\n{tasks_json}"