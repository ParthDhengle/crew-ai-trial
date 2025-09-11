import os
import shutil
from dotenv import load_dotenv
import firebase_admin
from firebase_admin import credentials, firestore
from datetime import datetime, timedelta
import json

# Load environment variables
load_dotenv()

# Initialize Firebase
if not firebase_admin._apps:
    cred_path = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
    if not cred_path or not os.path.exists(cred_path):
        raise ValueError(f"GOOGLE_APPLICATION_CREDENTIALS not set or invalid: {cred_path}")
    cred = credentials.Certificate(cred_path)
    firebase_admin.initialize_app(cred)

db = firestore.client()
USER_ID = os.getenv("USER_ID", "parth")
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STORAGE_BASE = os.path.join(PROJECT_ROOT, "knowledge", "storage")

def get_user_ref():
    """Get users doc ref for current user."""
    return db.collection("users").document(USER_ID)

# Generic CRUD
def add_document(collection: str, data: dict, doc_id: str = None, subcollection: bool = True) -> str:
    """Add doc to users/{user_id}/{collection}/{doc_id} or top-level collection."""
    ref = (get_user_ref().collection(collection).document(doc_id) if doc_id else
           get_user_ref().collection(collection).document()) if subcollection else (
           db.collection(collection).document(doc_id or data.get("id")))
    ref.set(data)
    return ref.id

def get_document(collection: str, doc_id: str, subcollection: bool = True) -> dict:
    """Get doc."""
    doc = (get_user_ref().collection(collection).document(doc_id) if subcollection else
           db.collection(collection).document(doc_id)).get()
    return doc.to_dict() if doc.exists else {}

def update_document(collection: str, doc_id: str, data: dict, subcollection: bool = True) -> bool:
    """Update doc."""
    try:
        (get_user_ref().collection(collection).document(doc_id) if subcollection else
         db.collection(collection).document(doc_id)).update(data)
        return True
    except Exception:
        return False

def query_collection(collection: str, filters: list = None, limit: int = None, subcollection: bool = True) -> list:
    """Query collection."""
    query = get_user_ref().collection(collection) if subcollection else db.collection(collection)
    if filters:
        for field, op, value in filters:
            query = query.where(field, op, value)
    if limit:
        query = query.limit(limit)
    return [doc.to_dict() for doc in query.stream()]

def delete_document(collection: str, doc_id: str, subcollection: bool = True) -> bool:
    """Delete doc."""
    try:
        (get_user_ref().collection(collection).document(doc_id) if subcollection else
         db.collection(collection).document(doc_id)).delete()
        return True
    except Exception:
        return False

# Local Storage Helpers
def upload_file(file_path: str, storage_path: str) -> str:
    """Copy file to knowledge/storage/users/{USER_ID}/{storage_path}."""
    dest_path = os.path.join(STORAGE_BASE, "users", USER_ID, storage_path)
    os.makedirs(os.path.dirname(dest_path), exist_ok=True)
    shutil.copy2(file_path, dest_path)
    return dest_path

def download_file(storage_path: str, local_path: str) -> bool:
    """Copy file from knowledge/storage/users/{USER_ID}/{storage_path} to local_path."""
    try:
        src_path = os.path.join(STORAGE_BASE, "users", USER_ID, storage_path)
        os.makedirs(os.path.dirname(local_path), exist_ok=True)
        shutil.copy2(src_path, local_path)
        return True
    except Exception:
        return False

def delete_storage_path(storage_path: str) -> bool:
    """Delete files in knowledge/storage/users/{USER_ID}/{storage_path}."""
    try:
        path = os.path.join(STORAGE_BASE, "users", USER_ID, storage_path)
        if os.path.isdir(path):
            shutil.rmtree(path)
        elif os.path.isfile(path):
            os.remove(path)
        return True
    except Exception:
        return False

# Users (profile)
def get_user_profile() -> dict:
    """Get user profile."""
    return get_document("users", USER_ID, subcollection=False)

def update_user_profile(data: dict) -> bool:
    """Update profile."""
    return update_document("users", USER_ID, data, subcollection=False)

def set_user_profile(name: str, email: str, timezone: str = "UTC", focus_hours: list = None,
                    permissions: dict = None, integrations: dict = None) -> str:
    """Create/update profile."""
    data = {
        "name": name, "email": email, "timezone": timezone,
        "focus_hours": focus_hours or [], "permissions": permissions or {},
        "integrations": integrations or {}, "updated_at": datetime.now().isoformat()
    }
    return add_document("users", data, USER_ID, subcollection=False)

# Tasks
def add_task(title: str, description: str = None, due_date: str = None, priority: str = "medium",
             related_files: list = None) -> str:
    """Create task."""
    data = {
        "title": title, "description": description, "due_date": due_date,
        "status": "pending", "priority": priority, "related_files": related_files or [],
        "rescheduled_from": None, "created_at": datetime.now().isoformat()
    }
    return add_document("tasks", data)

def get_tasks(status: str = None) -> list:
    """List tasks."""
    filters = [("status", "==", status)] if status else None
    return query_collection("tasks", filters)

def update_task(task_id: str, data: dict) -> bool:
    """Update task."""
    return update_document("tasks", task_id, data)

def mark_task_complete(task_id: str) -> bool:
    """Mark task complete."""
    return update_task(task_id, {"status": "complete", "completed_at": datetime.now().isoformat()})

# Projects
def add_project(name: str, description: str = None, members: list = None) -> str:
    """Create project."""
    data = {
        "name": name, "description": description, "owner_id": USER_ID,
        "members": members or [], "created_at": datetime.now().isoformat()
    }
    return add_document("projects", data)

def get_projects() -> list:
    """List projects."""
    return query_collection("projects")

# Focus Sessions
def start_focus_session(duration_min: int, blocked_apps: list = None) -> str:
    """Start focus session."""
    data = {
        "user_id": USER_ID, "start_time": datetime.now().isoformat(),
        "end_time": (datetime.now() + timedelta(minutes=duration_min)).isoformat(),
        "blocked_apps": blocked_apps or [], "status": "active", "distractions_logged": []
    }
    return add_document("focus_sessions", data)

def end_focus_session(session_id: str) -> bool:
    """End focus session."""
    return update_document("focus_sessions", session_id, {"status": "completed", "end_time": datetime.now().isoformat()})

def log_distraction(session_id: str, app: str, url: str = None) -> bool:
    """Log distraction in focus session."""
    session = get_document("focus_sessions", session_id)
    distractions = session.get("distractions_logged", [])
    distractions.append({"app": app, "url": url, "timestamp": datetime.now().isoformat()})
    return update_document("focus_sessions", session_id, {"distractions_logged": distractions})

# Audit Logs
def log_audit(op_id: str, op_name: str, params: dict, result: str, reversible: bool = True, undo_info: dict = None) -> str:
    """Log operation."""
    data = {
        "user_id": USER_ID, "op_id": op_id, "op_name": op_name, "params": params,
        "result": result, "timestamp": datetime.now().isoformat(), "reversible": reversible,
        "undo_info": undo_info or {}
    }
    return add_document("audit_logs", data)

# Snapshots
def create_snapshot(paths: list, retention_days: int = 30) -> str:
    """Create snapshot: Copy files to knowledge/storage/snapshots/{USER_ID}/{snap_id}/."""
    snap_id = add_document("snapshots", {
        "paths": paths, "created_at": datetime.now().isoformat(),
        "retention_days": retention_days, "object_store_uri": f"snapshots/{USER_ID}/{snap_id}"
    })
    for i, p in enumerate(paths):
        upload_file(p, f"snapshots/{snap_id}/{i}_{os.path.basename(p)}")
    return snap_id

def list_snapshots() -> list:
    """List snapshots."""
    return query_collection("snapshots")

def restore_snapshot(snap_id: str, target_path: str) -> bool:
    """Restore snapshot from local storage."""
    os.makedirs(target_path, exist_ok=True)
    src_dir = os.path.join(STORAGE_BASE, "snapshots", USER_ID, snap_id)
    if not os.path.exists(src_dir):
        return False
    for file_name in os.listdir(src_dir):
        src_path = os.path.join(src_dir, file_name)
        dest_path = os.path.join(target_path, file_name)
        shutil.copy2(src_path, dest_path)
    return True

def delete_snapshot(snap_id: str) -> bool:
    """Delete snapshot doc and local files."""
    delete_document("snapshots", snap_id)
    return delete_storage_path(f"snapshots/{snap_id}")

# Emails
def add_email(email_id: str, from_email: str, to: str, subject: str, body_summary: str, attachments: list = None) -> str:
    """Add email."""
    data = {
        "email_id": email_id, "from": from_email, "to": to, "subject": subject,
        "body_summary": body_summary, "attachments": attachments or [], "status": "unread",
        "parsed_at": datetime.now().isoformat()
    }
    return add_document("emails", data)

def get_emails(status: str = None) -> list:
    """List emails."""
    filters = [("status", "==", status)] if status else None
    return query_collection("emails", filters)

# Notifications
def add_notification(type_: str, message: str) -> str:
    """Add notification."""
    data = {
        "type": type_, "message": message, "status": "pending",
        "created_at": datetime.now().isoformat()
    }
    return add_document("notifications", data)

# Expenses
def add_expense(file_ref: str, amount: float, currency: str, category: str, date: str, vendor: str) -> str:
    """Add expense."""
    data = {
        "file_ref": file_ref, "amount": amount, "currency": currency,
        "category": category, "date": date, "vendor": vendor
    }
    return add_document("expenses", data)

def get_expenses() -> list:
    """List expenses."""
    return query_collection("expenses")

# Knowledge Base
def add_kb_entry(title: str, content_md: str, tags: list = None, references: list = None) -> str:
    """Add KB entry (facts/notes)."""
    data = {
        "title": title, "content_md": content_md, "tags": tags or [],
        "references": references or [], "created_at": datetime.now().isoformat()
    }
    return add_document("knowledge_base", data)

def search_kb(query: str, top_k: int = 5) -> list:
    """Simple text search on KB (semantic via memory_manager)."""
    kb = query_collection("knowledge_base", limit=top_k * 2)
    return [entry for entry in kb if query.lower() in entry.get("content_md", "").lower()][:top_k]

# Summaries
def add_summary(date_: str, summary_text: str, metrics: dict = None) -> str:
    """Add narrative summary."""
    data = {
        "date": date_, "summary_text": summary_text, "metrics": metrics or {},
        "created_at": datetime.now().isoformat()
    }
    return add_document("summaries", data)

def get_summaries(days: int = 7) -> list:
    """Get recent summaries."""
    cutoff = (datetime.now() - timedelta(days=days)).isoformat()
    filters = [("created_at", ">=", cutoff)]
    return query_collection("summaries", filters)

# Rules
def add_rule(trigger_type: str, conditions: dict, actions: list, enabled: bool = True) -> str:
    """Add automation rule."""
    data = {
        "trigger_type": trigger_type, "conditions": conditions, "actions": actions,
        "enabled": enabled, "created_at": datetime.now().isoformat()
    }
    return add_document("rules", data)

def get_rules(enabled_only: bool = True) -> list:
    """List rules."""
    filters = [("enabled", "==", True)] if enabled_only else None
    return query_collection("rules", filters)

# Operations Queue
def queue_operation(op_name: str, params: dict) -> str:
    """Queue operation (optional async)."""
    data = {
        "op_name": op_name, "params": params, "status": "pending",
        "created_at": datetime.now().isoformat()
    }
    return add_document("operations_queue", data)