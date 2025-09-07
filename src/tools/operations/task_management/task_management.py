# operations/task_manager.py

"""
A mock task management module.

This file contains placeholder functions for a to-do list or task manager.
Each function simulates a successful operation and returns a tuple
containing a boolean (True for success) and a descriptive string.
"""

def create_task(description: str):
    """
    Simulates creating a new task.

    Args:
        description (str): The content of the task to be created.

    Returns:
        tuple: A tuple indicating success and a confirmation message.
    """
    return (True, f"Placeholder: Would create a task with description '{description}'.")

def update_task(task_id: int, new_description: str):
    """
    Simulates updating an existing task.

    Args:
        task_id (int): The identifier of the task to update.
        new_description (str): The new description for the task.

    Returns:
        tuple: A tuple indicating success and a confirmation message.
    """
    return (True, f"Placeholder: Would update task ID {task_id} with new description '{new_description}'.")

def delete_task(task_id: int):
    """
    Simulates deleting a task.

    Args:
        task_id (int): The identifier of the task to delete.

    Returns:
        tuple: A tuple indicating success and a confirmation message.
    """
    return (True, f"Placeholder: Would delete task with ID {task_id}.")

def list_tasks():
    """
    Simulates listing all tasks.

    Returns:
        tuple: A tuple indicating success and a message with mock data.
    """
    mock_tasks = [
        "1. Buy groceries",
        "2. Finish project report",
        "3. Call the electrician"
    ]
    return (True, f"Placeholder: Would list all tasks.\n" + "\n".join(mock_tasks))

def mark_task_complete(task_id: int):
    """
    Simulates marking a task as complete.

    Args:
        task_id (int): The identifier of the task to mark as complete.

    Returns:
        tuple: A tuple indicating success and a confirmation message.
    """
    return (True, f"Placeholder: Would mark task with ID {task_id} as complete.")

# --- Example System Functions (for context) ---

def shutdown_system():
    """Simulates shutting down the system."""
    return (True, "Placeholder: Would shut down the system.")

def restart_system():
    """Simulates restarting the system."""
    return (True, "Placeholder: Would restart the system.")