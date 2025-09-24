# src/tools/operations/tasks/read_task.py (updated)
from firebase_client import get_tasks_by_user
import json
def read_task(status: str = None) -> tuple[bool, str]:
    tasks = get_tasks_by_user(status)
    return True, json.dumps(tasks)