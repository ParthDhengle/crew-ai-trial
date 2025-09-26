import os
import shutil
from dotenv import load_dotenv
import firebase_admin
from firebase_admin import credentials, firestore , auth
from datetime import datetime, timedelta
import json
import uuid
from fastapi import Depends, HTTPException
from fastapi.security import HTTPBearer
from firebase_admin import auth
from google.cloud.firestore_v1.field_path import FieldPath
load_dotenv()

def initialize_firebase():
    """Initialize Firebase with proper error handling"""
    try:
        # Check if already initialized
        if firebase_admin._apps:
            print("Firebase already initialized")
            return firestore.client()
        
        # Get credentials path
        cred_path = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
        if not cred_path:
            raise ValueError("GOOGLE_APPLICATION_CREDENTIALS environment variable not set")
        
        if not os.path.exists(cred_path):
            raise ValueError(f"Firebase credentials file not found: {cred_path}")
        
        # Initialize Firebase
        cred = credentials.Certificate(cred_path)
        firebase_admin.initialize_app(cred)
        
        print("Firebase initialized successfully")
        return firestore.client()
        
    except Exception as e:
        print(f"Error initializing Firebase: {e}")
        raise

# Initialize Firebase and get Firestore client
db = initialize_firebase()

security = HTTPBearer()

async def get_current_uid(token: str = Depends(security)):
    try:
        decoded_token = auth.verify_id_token(token.credentials)
        uid = decoded_token.get('uid')
        return uid
    except Exception as e:
        print(f"Token verification error: {str(e)}")  # NEW: Log exact error
        raise HTTPException(status_code=401, detail=f"Invalid token: {str(e)}")
    
    
def verify_id_token(id_token: str) -> str:
    """Verify ID token and return UID"""
    try:
        decoded_token = auth.verify_id_token(id_token)
        return decoded_token.get('uid')
    except Exception as e:
        print(f"ID token verification failed: {e}")
        raise ValueError(f"Token verification failed: {e}")

def verify_custom_token_locally(custom_token: str) -> bool:
    """
    Note: Firebase Admin SDK doesn't directly verify custom tokens.
    Custom tokens are meant to be exchanged for ID tokens.
    This is a helper to check token format.
    """
    try:
        # Custom tokens are JWTs, we can decode header to check format
        import jwt
        header = jwt.get_unverified_header(custom_token)
        return header.get('alg') == 'RS256' and 'kid' in header
    except:
        return False
    

USER_ID = os.getenv("USER_ID", "parth")
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STORAGE_BASE = os.path.join(PROJECT_ROOT, "knowledge", "storage")

def set_user_id(uid: str):
    """Set the current USER_ID from auth UID."""
    global USER_ID
    USER_ID = uid

def get_user_ref():
    """Get users doc ref for current user (uses dynamic USER_ID)."""
    return db.collection("users").document(USER_ID)

# === Auth Functions ===
def create_user(email: str, password: str = None, display_name: str = None) -> dict:
    if not isinstance(email, str) or not isinstance(password, (str, type(None))) or not isinstance(display_name, (str, type(None))):
        raise ValueError("Invalid input types for email, password, or display_name")
    if password and len(password) < 6:
        raise ValueError("Password must be at least 6 characters")
    try:
        user = auth.create_user(email=email, password=password, display_name=display_name)
        set_user_profile(user.uid, email, display_name=display_name)
        print(f"✅ User created: UID {user.uid}")
        return {"uid": user.uid}
    except Exception as e:
        raise ValueError(f"Failed to create user: {str(e)}")
    
def sign_in_with_email(email: str, password: str) -> str:
    """Sign in user and return ID token (for verification). For CLI, store in session/memory."""
    try:
        # Note: For CLI, this is server-side sim; in prod, client sends token.
        # Here, we verify by getting user and generating custom token (simple flow).
        user = auth.get_user_by_email(email)
        custom_token = auth.create_custom_token(user.uid)
        # In real CLI, send custom_token to client for id_token exchange; for now, return uid.
        set_user_id(user.uid)
        return user.uid
    except auth.UserNotFoundError:
        raise ValueError("User not found. Sign up first.")
    except Exception as e:
        raise ValueError(f"Sign-in failed: {e}")

def verify_id_token(id_token: str) -> str:
    """Verify ID token (for FastAPI endpoints). Returns UID."""
    try:
        decoded = auth.verify_id_token(id_token)
        uid = decoded['uid']
        set_user_id(uid)
        return uid
    except Exception as e:
        raise ValueError(f"Token verification failed: {e}")

def get_user_by_uid(uid: str) -> dict:
    """Get user by UID."""
    try:
        user = auth.get_user(uid)
        return user._data
    except Exception as e:
        raise ValueError(f"User fetch failed: {e}")

# === Profile Functions (Updated to use auth UID) ===
def get_user_profile(uid: str) -> dict:
    doc = db.collection("users").document(uid).get()
    profile = doc.to_dict() if doc.exists else {}
    if 'current_chat_session' not in profile:
        import uuid
        profile['current_chat_session'] = str(uuid.uuid4())
        db.collection("users").document(uid).set(profile, merge=True)
    return profile

def set_user_profile(uid: str, email: str, display_name: str = None, timezone: str = "UTC",

                      focus_hours: list = None, permissions: dict = None, integrations: dict = None) -> str:
    """Create/update profile using UID as doc ID."""
    set_user_id(uid) # Ensure global USER_ID is set
    data = {
        "uid": uid, "email": email, "Name": display_name, "display_name": display_name,
        "timezone": timezone, "focus_hours": focus_hours or [],
        "permissions": permissions or {}, "integrations": integrations or {},
        "updated_at": datetime.now().isoformat()
    }
    return add_document("users", data, uid, subcollection=False)

def update_user_profile(uid:str, data: dict) -> bool:
    """Update profile (uses current USER_ID)."""
    return update_document("users", uid, data, subcollection=False)

# Generic CRUD
def add_document(uid: str, collection: str, data: dict, doc_id: str = None, subcollection: bool = True) -> str:
    """Add doc to users/{uid}/{collection}/{doc_id} or top-level."""
    if subcollection:
        user_ref = db.collection("users").document(uid)
        ref = user_ref.collection(collection).document(doc_id) if doc_id else user_ref.collection(collection).document()
    else:
        ref = db.collection(collection).document(doc_id) if doc_id else db.collection(collection).document()
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
            query = query.where(filter=firestore.FieldFilter(field, op, value))
    if limit:
        query = query.limit(limit)
    return [doc.to_dict() for doc in query.stream()]
def get_operations() -> list:
    """Get operations from Firestore (or fallback to json)."""
    ops = query_collection("operations", subcollection=False) # Assumes top-level collection
    if ops:
        return ops # List of dicts like operations.json
    # Fallback to json
    ops_path = os.path.join(PROJECT_ROOT, "knowledge", "operations.json")
    if os.path.exists(ops_path):
        with open(ops_path, "r") as f:
            return json.load(f).get("operations", [])
    return []

def get_chat_history(session_id: str = None, uid: str = None) -> list:
    user_ref = db.collection('users').document(uid)
    if session_id:
        messages_ref = user_ref.collection('chat_sessions').document(session_id).collection('messages')
        docs = messages_ref.stream()
        history = [doc.to_dict() for doc in docs]
        history.sort(key=lambda x: x.get('timestamp', ''))
        return history
    else:
        # Aggregate all messages across sessions (with session_id in each)
        all_history = []
        sessions = user_ref.collection('chat_sessions').stream()
        for session in sessions:
            msgs = session.reference.collection('messages').stream()
            for msg in msgs:
                data = msg.to_dict()
                data['session_id'] = session.id
                all_history.append(data)
        all_history.sort(key=lambda x: x.get('timestamp', ''))
        return all_history
   
def add_chat_message(uid: str, role: str, content: str, session_id: str = None) -> str:
    """Add a message to chat_history collection."""
    data = {
        "role": role,
        "content": content,
        "timestamp": datetime.now().isoformat()
    }
    if session_id:
        data["session_id"] = session_id
    return add_document(uid, "chat_history", data)
def delete_document(collection: str, doc_id: str, subcollection: bool = True) -> bool:
    """Delete doc."""
    try:
        (get_user_ref().collection(collection).document(doc_id) if subcollection else
         db.collection(collection).document(doc_id)).delete()
        return True
    except Exception:
        return False
# Local Storage Helpers
def upload_file(uid:str, file_path: str, storage_path: str) -> str:
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
def create_snapshot(uid: str, paths: list, retention_days: int = 30) -> str:
    """Create snapshot: Copy files to knowledge/storage/snapshots/{USER_ID}/{snap_id}/."""
    snap_id = add_document("snapshots", {
        "paths": paths, "created_at": datetime.now().isoformat(),
        "retention_days": retention_days, "object_store_uri": f"snapshots/{USER_ID}/{snap_id}"
    })
    for i, p in enumerate(paths):
        upload_file(uid, p, f"snapshots/{snap_id}/{i}_{os.path.basename(p)}")
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
async def save_chat_message(session_id: str, uid: str, role: str, content: str, timestamp: str, actions=None) -> str:
    user_ref = db.collection("users").document(uid)
   
    if session_id is None or not user_ref.collection('chat_sessions').document(session_id).get().exists:
        session_id = session_id or str(uuid.uuid4())
        # Create session doc with metadata
        session_ref = user_ref.collection('chat_sessions').document(session_id)
        session_ref.set({
            'title': 'New Chat',
            'summary': '',
            'createdAt': timestamp,
            'updatedAt': timestamp
        })
   
    # Add message
    session_ref = user_ref.collection('chat_sessions').document(session_id)
    msg_ref = session_ref.collection('messages').document()
    message = {
        "role": role,
        "content": content,
        "timestamp": timestamp,
        "actions": actions or []
    }
    msg_ref.set(message)
   
    # Update session updatedAt (and title if first user message)
    session_ref.update({'updatedAt': timestamp})
    if role == 'user':
        messages = session_ref.collection('messages').where('role', '==', 'user').stream()
        user_msgs = [m.to_dict()['content'] for m in messages]
        if len(user_msgs) == 1: # First user message
            title = user_msgs[0][:50] + ('...' if len(user_msgs[0]) > 50 else '')
            session_ref.update({'title': title})

   
    return session_id # Return session_id (new or existing)

def set_initial_profile(uid: str, email: str, display_name: str = None) -> str:
    """Create initial profile with minimal data - will be completed via profile setup."""
    set_user_id(uid)
    data = {
        "uid": uid, 
        "email": email, 
        "Name": display_name, 
        "display_name": display_name,
        "timezone": "UTC", 
        "focus_hours": [],
        "permissions": {}, 
        "integrations": {},
        "profile_completed": False,  # Track if profile setup is complete
        "created_at": datetime.now().isoformat(),
        "updated_at": datetime.now().isoformat()
    }
    return add_document("users", data, uid, subcollection=False)

def complete_user_profile(uid: str, profile_data: dict) -> bool:
    """Complete user profile with personalization data."""
    try:
        profile_data['profile_completed'] = True
        profile_data['updated_at'] = datetime.now().isoformat()
        success = update_document("users", uid, profile_data, subcollection=False)
        if success:
            print(f"Profile completed for user {uid}")
        return success
    except Exception as e:
        print(f"Error completing profile: {e}")
        return False

def is_profile_complete(uid: str) -> bool:
    """Check if user has completed their profile setup."""
    profile = get_user_profile(uid)
    return profile.get('profile_completed', False)


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
def add_summary(uid: str, date: str, summary_text: str, metrics: dict = None) -> str:
    """Add narrative summary with proper error handling."""
    try:
        if not uid or not date or not summary_text:
            raise ValueError("uid, date_, and summary_text are required")
            
        from datetime import datetime
        
        data = {
            "date": date,
            "summary_text": summary_text,
            "metrics": metrics or {},
            "created_at": datetime.now().isoformat(),
            "uid": uid  # Include uid in the document for better querying
        }
        
        # Add to user's summaries subcollection
        doc_ref = db.collection('users').document(uid).collection('summaries').document()
        doc_ref.set(data)
        
        print(f"Summary added successfully for user {uid}")
        return doc_ref.id
        
    except Exception as e:
        print(f"Error adding summary: {e}")
        raise

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

def queue_operation(uid: str, operation_data: dict) -> str:
    """Queue operation under user. Fixed parameter structure."""
    # Extract operation details from the operation_data dict
    op_name = operation_data.get('name', 'unknown')
    params = operation_data.get('parameters', {})
    
    data = {

        "user_id": uid,
        "op_name": op_name,
        "params": params,
        "status": "pending",
        "created_at": datetime.now().isoformat(),
        "start_time": None,
        "end_time": None,
        "result": None
    }
    return add_document(uid, "operations_queue", data)


def get_operations_queue(status: str = None) -> list:
    filters = [("status", "==", status)] if status else None
    return query_collection("operations_queue", filters=filters)

def update_operation_status(uid: str, op_id: str, status: str, result: str = None) -> bool:
    """Update op status."""
    data = {"status": status, "updated_at": datetime.now().isoformat()}
    if status == 'running':
        data["start_time"] = datetime.now().isoformat()
    if status in ['success', 'failed']:
        data["end_time"] = datetime.now().isoformat()
    if result:
        data["result"] = result
    return update_document(uid, "operations_queue", op_id, data)

# Add to end of file
def get_tasks_by_user(status: str = None) -> list:
    """Get user's tasks (filtered by status)."""
    filters = [("owner_id", "==", USER_ID)] + ([("status", "==", status)] if status else [])
    return query_collection("tasks", filters=filters)

def update_task_by_user(task_id: str, data: dict) -> bool:
    """Update user's task."""
    data["updated_at"] = datetime.now().isoformat()
    return update_document("tasks", task_id, data)

def delete_task_by_user(task_id: str) -> bool:
    """Delete user's task."""
    return delete_document("tasks", task_id)