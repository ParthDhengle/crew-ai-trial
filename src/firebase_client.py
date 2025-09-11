import os
import firebase_admin
from firebase_admin import credentials, firestore, storage
from datetime import datetime
import json

# Initialize Firebase if not already done
if not firebase_admin._apps:
    cred_path = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
    if not cred_path or not os.path.exists(cred_path):
        raise ValueError("GOOGLE_APPLICATION_CREDENTIALS not set or invalid.")
    cred = credentials.Certificate(cred_path)
    firebase_admin.initialize_app(cred)

db = firestore.client()
bucket = storage.bucket(os.getenv("FIREBASE_STORAGE_BUCKET", "your-default-bucket"))  # Set env var for bucket

def add_document(collection: str, data: dict, doc_id: str = None, user_id: str = "default_user") -> str:
    """Add a document to a collection, optionally under a user subcollection."""
    ref = db.collection("users").document(user_id).collection(collection).document(doc_id) if doc_id else db.collection("users").document(user_id).collection(collection).document()
    ref.set(data)
    return ref.id

def get_document(collection: str, doc_id: str, user_id: str = "default_user") -> dict:
    """Get a document from a collection."""
    doc = db.collection("users").document(user_id).collection(collection).document(doc_id).get()
    return doc.to_dict() if doc.exists else {}

def update_document(collection: str, doc_id: str, data: dict, user_id: str = "default_user") -> bool:
    """Update a document in a collection."""
    try:
        db.collection("users").document(user_id).collection(collection).document(doc_id).update(data)
        return True
    except Exception:
        return False

def query_collection(collection: str, filters: list = None, user_id: str = "default_user", limit: int = None) -> list:
    """Query a collection with optional filters."""
    query = db.collection("users").document(user_id).collection(collection)
    if filters:
        for field, op, value in filters:
            query = query.where(field, op, value)
    if limit:
        query = query.limit(limit)
    return [doc.to_dict() for doc in query.stream()]

def delete_document(collection: str, doc_id: str, user_id: str = "default_user") -> bool:
    """Delete a document."""
    try:
        db.collection("users").document(user_id).collection(collection).document(doc_id).delete()
        return True
    except Exception:
        return False

def upload_file(file_path: str, storage_path: str, user_id: str = "default_user") -> str:
    """Upload a file to Firebase Storage under user prefix."""
    blob = bucket.blob(f"users/{user_id}/{storage_path}")
    blob.upload_from_filename(file_path)
    blob.make_public()  # Optional: Make public if needed
    return blob.public_url

def download_file(storage_path: str, local_path: str, user_id: str = "default_user") -> bool:
    """Download a file from Firebase Storage."""
    try:
        blob = bucket.blob(f"users/{user_id}/{storage_path}")
        blob.download_to_filename(local_path)
        return True
    except Exception:
        return False

# Specific methods for project features
def add_task(title: str, user_id: str, description: str = None, due_date: str = None, estimate_min: int = None, related_files: list = None) -> str:
    """Create a task in Firestore."""
    data = {
        "title": title,
        "description": description,
        "due": due_date,
        "estimate": estimate_min,
        "files": related_files or [],
        "status": "pending",
        "created_at": datetime.now().isoformat()
    }
    return add_document("tasks", data, user_id=user_id)

def get_tasks(user_id: str, status: str = None) -> list:
    """List tasks, optionally filtered by status."""
    filters = [("status", "==", status)] if status else None
    return query_collection("tasks", filters, user_id=user_id)

def update_task(task_id: str, fields: dict, user_id: str) -> bool:
    """Update a task."""
    return update_document("tasks", task_id, fields, user_id=user_id)

def mark_task_complete(task_id: str, user_id: str) -> bool:
    """Mark task as complete."""
    return update_task(task_id, {"status": "complete", "completed_at": datetime.now().isoformat()}, user_id)

def create_snapshot(paths: list, user_id: str, name: str = None) -> str:
    """Create a snapshot: Upload files to Storage and log in Firestore."""
    if not name:
        name = datetime.now().isoformat()
    snap_id = add_document("snapshots", {"name": name, "paths": paths, "created_at": datetime.now().isoformat()}, user_id=user_id)
    # Upload files to Storage
    for i, p in enumerate(paths):
        upload_file(p, f"snapshots/{snap_id}/{i}_{os.path.basename(p)}", user_id=user_id)
    return snap_id

def list_snapshots(user_id: str) -> list:
    """List snapshots."""
    return query_collection("snapshots", user_id=user_id)

def restore_snapshot(snap_id: str, target_path: str, user_id: str) -> bool:
    """Restore snapshot: Download files from Storage."""
    snap = get_document("snapshots", snap_id, user_id)
    if not snap:
        return False
    os.makedirs(target_path, exist_ok=True)
    # Download files (assume blob paths known; in prod, store blob paths in doc)
    blobs = bucket.list_blobs(prefix=f"users/{user_id}/snapshots/{snap_id}/")
    for blob in blobs:
        local_file = os.path.join(target_path, os.path.basename(blob.name))
        blob.download_to_filename(local_file)
    return True

def delete_snapshot(snap_id: str, user_id: str) -> bool:
    """Delete snapshot doc and Storage files."""
    delete_document("snapshots", snap_id, user_id)
    bucket.delete_blobs(bucket.list_blobs(prefix=f"users/{user_id}/snapshots/{snap_id}/"))
    return True

# For memory/facts: Store extracted facts in Firestore
def add_fact(fact: str, source: str, user_id: str) -> str:
    """Add a fact to long-term memory."""
    data = {"fact": fact, "source": source, "added_at": datetime.now().isoformat()}
    return add_document("facts", data, user_id=user_id)

def search_facts(query: str, user_id: str, top_k: int = 5) -> list:
    """Simple text search on facts (for hybrid; integrate with FAISS for semantic)."""
    facts = query_collection("facts", user_id=user_id, limit=top_k * 2)
    return [f for f in facts if query.lower() in f["fact"].lower()][:top_k]

# For mood logs and summaries
def log_mood(mood: str, user_id: str) -> str:
    """Log user mood."""
    data = {"mood": mood, "date": datetime.now().isoformat()}
    return add_document("mood_logs", data, user_id=user_id)

def get_recent_moods(user_id: str, days: int = 7) -> list:
    """Get recent moods."""
    from datetime import timedelta
    cutoff = (datetime.now() - timedelta(days=days)).isoformat()
    filters = [("date", ">=", cutoff)]
    return query_collection("mood_logs", filters, user_id=user_id)