import os
import sys
import json
import warnings
from datetime import datetime
from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, __version__ as pydantic_version
from crew import AiAgent
import traceback
from uvicorn import Config, Server
import asyncio
from common_functions.Find_project_root import find_project_root
from common_functions.User_preference import collect_preferences
from utils.logger import setup_logger
from firebase_client import (
    create_user, sign_in_with_email, get_user_profile, set_user_profile, verify_id_token,
    add_task, get_tasks_by_user, update_task_by_user, delete_task_by_user,
    queue_operation, get_operations_queue, update_operation_status,
    save_chat_message, get_chat_history, add_chat_message, get_user_ref
)
from firebase_admin import auth
from firebase_admin import firestore as _firestore
from fastapi.security import HTTPBearer
from typing import Optional,List
from collections import defaultdict

PROJECT_ROOT = find_project_root()
logger = setup_logger()

db = _firestore.client()

# Suppress Pydantic warnings
if pydantic_version.startswith("2"):
    from pydantic import PydanticDeprecatedSince20
    warnings.filterwarnings("ignore", category=PydanticDeprecatedSince20)

# FastAPI app setup
app = FastAPI(title="AI Assistant API")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173", "*"],  # Vite dev + Electron
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Security
security = HTTPBearer()

async def get_current_uid(token: str = Depends(security)):
    try:
        print(f"DEBUG: Received token: {token.credentials[:50]}...")
        
        # First try to verify as ID token
        try:
            uid = verify_id_token(token.credentials)
            print(f"DEBUG: ID token verification successful, UID: {uid}")
            return uid
        except ValueError as e:
            print(f"DEBUG: ID token verification failed: {e}")
            
            # For development/testing, decode custom tokens
            # In production, this should be removed
            if token.credentials.startswith('eyJ'):  # JWT tokens start with eyJ
                print("DEBUG: Attempting custom token decode...")
                try:
                    import base64
                    import json
                    
                    # Decode JWT token (simplified - no signature verification for dev)
                    parts = token.credentials.split('.')
                    print(f"DEBUG: Token has {len(parts)} parts")
                    if len(parts) == 3:
                        # Decode the payload (middle part)
                        payload = parts[1]
                        # Add padding if needed
                        payload += '=' * (4 - len(payload) % 4)
                        decoded = json.loads(base64.b64decode(payload))
                        print(f"DEBUG: Decoded payload: {decoded}")
                        uid = decoded.get('uid')
                        if uid:
                            print(f"DEBUG: Custom token decode successful, UID: {uid}")
                            return uid
                    
                    # Fallback for testing
                    print("DEBUG: Using fallback UID")
                    return "test-user-uid"
                except Exception as e:
                    print(f"DEBUG: Token decode error: {e}")
                    return "test-user-uid"  # Fallback for testing
            else:
                print("DEBUG: Token doesn't start with eyJ")
                raise ValueError("Invalid token format")
    except ValueError as e:
        print(f"DEBUG: Final error: {e}")
        raise HTTPException(status_code=401, detail="Invalid token")

# Pydantic models
class LoginRequest(BaseModel):
    email: str
    password: str

class QueryRequest(BaseModel):
    query: str
    session_id: Optional[str] = None

class TaskRequest(BaseModel):
    title: str
    description: str = None
    deadline: str = None  # ISO string
    priority: str = "Medium"
    tags: list[str] = None

class UpdateTaskRequest(BaseModel):
    status: str = None
    title: str = None
    description: str = None
    deadline: str = None
    priority: str = None
    tags: list[str] = None

class OperationRequest(BaseModel):
    name: str
    parameters: dict

# Auth Routes (public)
@app.post("/auth/login")
async def api_login(request: LoginRequest):
    try:
        uid = sign_in_with_email(request.email, request.password)
        custom_token = auth.create_custom_token(uid)
        return {"uid": uid, "custom_token": custom_token.decode()}
    except ValueError as e:
        raise HTTPException(status_code=401, detail=str(e))

@app.post("/auth/signup")
async def api_signup(request: LoginRequest):
    try:
        user_data = create_user(request.email, request.password, request.email)  # Use email as display_name
        uid = user_data['uid']  # Extract UID from user data
        custom_token = auth.create_custom_token(uid)
        return {"uid": uid, "custom_token": custom_token.decode()}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


# Tasks CRUD
@app.post("/tasks")
async def create_task(request: TaskRequest, uid: str = Depends(get_current_uid)):
    global current_uid; current_uid = uid
    task_id = add_task(
        title=request.title, description=request.description, due_date=request.deadline,
        priority=request.priority, related_files=request.tags or []
    )
    return {"task_id": task_id}

@app.get("/tasks")
async def get_tasks(status: str = None, uid: str = Depends(get_current_uid)):
    global current_uid; current_uid = uid
    return get_tasks_by_user(status)

@app.put("/tasks/{task_id}")
async def update_task(task_id: str, request: UpdateTaskRequest, uid: str = Depends(get_current_uid)):
    global current_uid; current_uid = uid
    updates = request.dict(exclude_unset=True)
    updates["updated_at"] = datetime.now().isoformat()
    success = update_task_by_user(task_id, updates)
    if not success:
        raise HTTPException(status_code=404, detail="Task not found")
    return {"success": True}

@app.delete("/tasks/{task_id}")
async def delete_task(task_id: str, uid: str = Depends(get_current_uid)):
    global current_uid; current_uid = uid
    success = delete_task_by_user(task_id)
    if not success:
        raise HTTPException(status_code=404, detail="Task not found")
    return {"success": True}

# Operations
@app.post("/operations")
async def queue_operation(request: OperationRequest, uid: str = Depends(get_current_uid)):
    global current_uid; current_uid = uid
    op_id = queue_operation(request.name, request.parameters)
    return {"op_id": op_id}

@app.get("/operations")
async def get_operations(status: str = None, uid: str = Depends(get_current_uid)):
    global current_uid; current_uid = uid
    return get_operations_queue(status)

@app.put("/operations/{op_id}/status")
async def update_op_status(op_id: str, status: str, result: str = None, uid: str = Depends(get_current_uid)):
    global current_uid; current_uid = uid
    success = update_operation_status(op_id, status, result)
    if not success:
        raise HTTPException(status_code=404, detail="Operation not found")
    return {"success": True}

# Profile (protected)
@app.get("/profile")
async def get_profile(uid: str = Depends(get_current_uid)):
    global current_uid; current_uid = uid
    from firebase_client import get_user_profile
    return get_user_profile()

@app.put("/profile")
async def update_profile(updates: dict, uid: str = Depends(get_current_uid)):
    global current_uid; current_uid = uid
    from firebase_client import update_user_profile
    success = update_user_profile(updates)
    if not success:
        raise HTTPException(status_code=500, detail="Update failed")
    return {"success": True}

@app.post("/chat_message")
async def add_chat_message(role: str, content: str, session_id: str = None, uid: str = Depends(get_current_uid)):
    global current_uid; current_uid = uid
    from firebase_client import add_chat_message
    msg_id = add_chat_message(role, content, session_id)
    return {"msg_id": msg_id}
# Chats (protected)

@app.get("/chats/{session_id}")
async def get_chats(session_id: str, uid: str = Depends(get_current_uid)):
    from firebase_client import get_chats_by_session
    return get_chats_by_session(session_id)

@app.post("/process_query")
async def process_query(request: QueryRequest, uid: str = Depends(get_current_uid)):
    """
    Saves user message, runs AI agent with the session_id (new if None), saves assistant reply,
    and returns assistant result + session_id.
    """
    try:
        timestamp = datetime.now().isoformat()

        # Save user query and get session_id (create new session if None)
        session_id = save_chat_message(request.session_id, uid, "user", request.query, timestamp)
        if not session_id:
            raise RuntimeError("Failed to create or retrieve session_id")

        # Run AI agent (synchronous call kept as you had it)
        crew_instance = AiAgent()
        final_response = crew_instance.run_workflow(request.query, session_id=session_id)

        # Save assistant response
        save_chat_message(session_id, uid, "assistant", final_response, datetime.now().isoformat())

        return {"result": final_response, "session_id": session_id}
    except Exception as e:
        logger.error(f"Error in process_query: {e}")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

# ---- get_chat_history (updated) ----
@app.get("/chat_history")
async def get_chat_history_api(session_id: str = None, uid: str = Depends(get_current_uid)):
    """
    Returns chat history for a given session_id (or all user messages if session_id is None).
    Converts ISO timestamps to integer ms for the frontend.
    """
    try:
        history: List[dict] = get_chat_history(session_id, uid)
        if not isinstance(history, list):
            history = []

        # Convert timestamps to ms since epoch (int)
        for msg in history:
            iso_ts = msg.get("timestamp")
            if iso_ts:
                try:
                    msg["timestamp"] = int(datetime.fromisoformat(iso_ts).timestamp() * 1000)
                except Exception:
                    # If it is already numeric, keep it
                    try:
                        msg["timestamp"] = int(msg["timestamp"])
                    except Exception:
                        msg["timestamp"] = None
        return history
    except Exception as e:
        logger.error(f"Error fetching chat history: {e}")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

# ---- get_chat_sessions (updated) ----
@app.get("/chat_sessions")
async def get_chat_sessions(uid: str = Depends(get_current_uid)):
    """
    Reads session documents under users/{uid}/chat_sessions and returns list of sessions
    with title, summary and createdAt/updatedAt in ms. Messages are not included here.
    """
    try:
        user_ref = db.collection("users").document(uid)
        sessions_ref = user_ref.collection("chat_sessions").stream()
        session_list = []
        for session_doc in sessions_ref:
            sid = session_doc.id
            data = session_doc.to_dict() or {}

            # Ensure createdAt/updatedAt exist and are ISO strings (or datetimes)
            created_at = data.get("createdAt")
            updated_at = data.get("updatedAt")

            def to_ms(v):
                if v is None:
                    return None
                if isinstance(v, str):
                    return int(datetime.fromisoformat(v).timestamp() * 1000)
                if hasattr(v, "timestamp"):  # e.g., python datetime
                    return int(v.timestamp() * 1000)
                # try numeric
                try:
                    return int(v)
                except Exception:
                    return None

            created_ms = to_ms(created_at)
            updated_ms = to_ms(updated_at)

            # Build summary from messages (counts)
            messages = get_chat_history(sid, uid)
            summary = f"{len(messages)} messages" if isinstance(messages, list) else "0 messages"

            session_list.append({
                "id": sid,
                "title": data.get("title", "Untitled"),
                "summary": summary,
                "messages": [],  # don't return messages here; fetch with /chat_history
                "createdAt": created_ms,
                "updatedAt": updated_ms
            })

        # sort by updatedAt desc (None values go last)
        session_list.sort(key=lambda s: (s["updatedAt"] is not None, s["updatedAt"] or 0), reverse=True)
        return session_list
    except Exception as e:
        logger.error(f"Error listing chat sessions: {e}")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

# ---- delete_chat_session (updated with chunked batch deletion) ----
@app.delete("/chat_sessions/{session_id}")
async def delete_chat_session(session_id: str, uid: str = Depends(get_current_uid)):
    """
    Deletes a session doc and all messages under users/{uid}/chat_sessions/{session_id}/messages
    Uses chunked batch deletes to respect Firestore limits.
    """
    try:
        user_ref = db.collection("users").document(uid)
        session_ref = user_ref.collection("chat_sessions").document(session_id)

        # Delete messages in batches (Firestore write limit per batch = 500)
        messages_ref = session_ref.collection("messages")
        while True:
            docs = list(messages_ref.limit(500).stream())
            if not docs:
                break
            batch = db.batch()
            for d in docs:
                batch.delete(d.reference)
            batch.commit()

        # Delete session document itself
        session_ref.delete()
        return {"success": True}
    except Exception as e:
        logger.error(f"Error deleting chat session {session_id} for user {uid}: {e}")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


# Run server
async def run_server():
    logger.info("Starting FastAPI server on http://127.0.0.1:8001")
    config = Config(app=app, host="127.0.0.1", port=8001, log_level="info")
    server = Server(config)
    await server.serve()

if __name__ == "__main__":
    asyncio.run(run_server())