# src/firebase_client.py
import os
import shutil
from dotenv import load_dotenv
import firebase_admin
from firebase_admin import credentials, firestore
from datetime import datetime, timedelta
import json
from .utils.logger import setup_logger  # Added logger

# Resolve project root and load .env from project root, overriding any system/user env vars
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ENV_PATH = os.path.join(PROJECT_ROOT, ".env")
if os.path.exists(ENV_PATH):
    load_dotenv(ENV_PATH, override=True)
else:
    load_dotenv(override=True)

logger = setup_logger()  # Initialize logger

# Initialize Firebase
if not firebase_admin._apps:
    cred_path = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
    # Fallback: use local credentials file in project root if env var missing/invalid
    if not cred_path or not os.path.exists(cred_path):
        fallback_cred = os.path.join(PROJECT_ROOT, "NOVA_firebase_credentials.json")
        if os.path.exists(fallback_cred):
            os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = fallback_cred
            cred_path = fallback_cred

    if not cred_path or not os.path.exists(cred_path):
        logger.error(
            f"GOOGLE_APPLICATION_CREDENTIALS not set or invalid: {cred_path}. "
            f"Consider setting it in {ENV_PATH} or placing NOVA_firebase_credentials.json in the project root."
        )
        raise ValueError("Firebase credentials not found.")

    cred = credentials.Certificate(cred_path)
    firebase_admin.initialize_app(cred)
    logger.info("Firebase initialized successfully.")  # Log init

db = firestore.client()
USER_ID = os.getenv("USER_ID", "parth")
STORAGE_BASE = os.path.join(PROJECT_ROOT, "knowledge", "storage")

def get_user_ref():
    """Get users doc ref for current user."""
    return db.collection("users").document(USER_ID)

# Generic CRUD (added logging)
def add_document(collection: str, data: dict, doc_id: str = None, subcollection: bool = True) -> str:
    """Add doc to users/{user_id}/{collection}/{doc_id} or top-level collection."""
    if subcollection:
        if doc_id:
            ref = get_user_ref().collection(collection).document(doc_id)
        else:
            ref = get_user_ref().collection(collection).document()
    else:
        ref = db.collection(collection).document(doc_id or data.get("id"))
    ref.set(data)
    logger.info(f"Added document to {collection} (ID: {ref.id})")  # Log add
    return ref.id

def get_document(collection: str, doc_id: str, subcollection: bool = True) -> dict:
    """Get doc."""
    if subcollection:
        doc = get_user_ref().collection(collection).document(doc_id).get()
    else:
        doc = db.collection(collection).document(doc_id).get()
    if doc.exists:
        logger.debug(f"Retrieved document from {collection} (ID: {doc_id})")  # Log get
    else:
        logger.warning(f"Document not found in {collection} (ID: {doc_id})")  # Log missing
    return doc.to_dict() if doc.exists else {}

# ... (rest of the file remains similar, with logger added to all functions like update_document, query_collection, etc.)

# New: For monitoring logs
def log_monitoring(data: dict) -> str:
    """Log PC monitoring data (e.g., open apps)."""
    data["timestamp"] = datetime.now().isoformat()
    return add_document("monitoring_logs", data)