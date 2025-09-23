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
import inspect
from firebase_client import (
    create_user, sign_in_with_email, get_user_profile, update_user_profile, verify_id_token,
    add_task, get_tasks_by_user, update_task_by_user, delete_task_by_user,
    save_chat_message, get_chat_history, add_chat_message, get_user_ref
)
from firebase_admin import auth
from firebase_admin import firestore as _firestore
from fastapi.security import HTTPBearer
from typing import Optional,List
from collections import defaultdict
from fastapi import BackgroundTasks
from fastapi.responses import StreamingResponse
from operations_store import queue_operation_local, register_sse_queue, unregister_sse_queue, publish_event, get_operation_local, OP_STORE, update_operation_local, OP_LOCK

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
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"], # Vite dev + Electron
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
    # Use local queue (session_id not required here; attach in process_query)
    op_id = await queue_operation_local(request.name, request.parameters, session_id="")  # session_id optional
    return {"op_id": op_id}

@app.get("/operations")
async def get_operations(status: str = None, uid: str = Depends(get_current_uid)):
     # Return all ops (or filter by status; no uid filter for simplicity)
    ops = [op for op in OP_STORE.values() if not status or op["status"] == status]
    return ops

@app.put("/operations/{op_id}/status")
async def update_op_status(op_id: str, status: str, uid: str = Depends(get_current_uid)):
    """
    Update operation status (supports cancel_requested).
    """
    try:
        # use operations_store.update_operation_local to set status
        from operations_store import update_operation_local
        await update_operation_local(op_id, status=status, extra_fields={"updatedBy": uid, "updatedAt": datetime.now().isoformat()})
        return {"success": True}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

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
async def process_query(request: QueryRequest, background_tasks: BackgroundTasks, uid: str = Depends(get_current_uid)):
    """
    Processes the query using the updated AiAgent workflow.
    For 'direct' mode: Returns response immediately.
    For 'agentic' mode: Queues ops, returns mode/ops/session_id, executes in background.
    """
    try:
        timestamp = datetime.now().isoformat()
        
        # Save user query and get session_id
        session_id = await save_chat_message(request.session_id, uid, "user", request.query, timestamp)
        
        if not session_id:
            raise RuntimeError("Failed to create or retrieve session_id")
        
        # Ensure session_id is a string (not a coroutine)
        if inspect.iscoroutine(session_id):
            session_id = await session_id
        
        logger.info(f"Session ID type: {type(session_id)}, value: {session_id}")
         # Clear old ops for this session before processing new query
        async with OP_LOCK:
            to_delete = [oid for oid, op in list(OP_STORE.items()) if op.get('session_id') == session_id]
            for oid in to_delete:
                del OP_STORE[oid]
        # Publish an event to notify clients (optional, but helps frontend reset)

        await publish_event(session_id, {"type": "ops_cleared"})

        # Run the full workflow synchronously (includes classification)
        crew_instance = AiAgent()
        result = await crew_instance.run_workflow(
            request.query, 
            file_path=getattr(request, 'file_path', None),
            session_id=session_id,
            uid=uid
        )
        
        # Ensure result is a dict (not a coroutine)
        if inspect.iscoroutine(result):
            result = await result
        
        mode = result.get('mode', 'direct')
        
        if mode == 'direct':
            final_response = result.get('display_response', 'No response')
            
            # Save assistant response
            save_result = save_chat_message(session_id, uid, "assistant", final_response, datetime.now().isoformat())
            if inspect.iscoroutine(save_result):
                await save_result
            
            # Return serializable data
            return {
                "result": {
                    "display_response": final_response, 
                    "mode": mode
                }, 
                "session_id": str(session_id)
            }
        else:  # agentic
            operations = result.get('operations', [])  # Assuming run_workflow returns this in agentic mode
            
            # Validate operations structure
            if not isinstance(operations, list):
                operations = []
            
            # Queue operations and collect IDs
            op_ids = []
            for op in operations:
                if isinstance(op, dict) and 'name' in op:
                    try:
                        op_id = await queue_operation_local(op['name'], op.get('parameters', {}), session_id)
                        op_ids.append(str(op_id))
                        op['op_id'] = op_id
                    except Exception as e:
                        logger.error(f"Failed to queue local operation {op['name']}: {e}")
                        op_ids.append(f"error_{len(op_ids)}")
            
            # Prepare serializable response operations
            response_ops = []
            for i, (op_id, op) in enumerate(zip(op_ids, operations)):
                response_ops.append({
                    "id": str(op_id),
                    "name": str(op.get('name', 'unknown')),
                    "parameters": op.get('parameters', {})
                })
            
            user_summarized_requirements = result.get('user_summarized_requirements', 'User intent unclear.')
            for i, op in enumerate(operations):
                if i < len(op_ids):
                    op['op_id'] = op_ids[i]
            # Add background task for execution
            background_tasks.add_task(
                crew_instance.execute_agentic_background, 
                operations, 
                user_summarized_requirements, 
                session_id, 
                uid
            )
            
            # Return serializable data
            return {
                "result": {
                    "mode": "agentic", 
                    "operations": response_ops
                }, 
                "session_id": str(session_id)
            }
            
    except Exception as e:
        logger.error(f"Error in process_query: {e}")
        traceback.print_exc()
        
        # Return a proper error response
        error_response = {
            "result": {
                "mode": "error",
                "display_response": f"Processing failed: {str(e)}"
            },
            "session_id": request.session_id or "error"
        }
        
        raise HTTPException(status_code=500, detail=error_response)

# SSE endpoint to stream operation events for a session
@app.get("/operations/stream")
async def operations_stream(session_id: str):
    """
    Server-Sent Events endpoint that streams operation events for a given session_id.
    Clients should connect with EventSource('/operations/stream?session_id=...')
    """
    async def event_generator():
        q = asyncio.Queue()
        await register_sse_queue(session_id, q)
        try:
            # When a client connects, send current snapshot of operations for this session
            # (send as a single 'initial' message)
            current_ops = [op for op in OP_STORE.values() if op.get("session_id") == session_id]
            await q.put({"type": "initial_state", "operations": current_ops})
            while True:
                payload = await q.get()
                # SSE format: "data: <json>\n\n"
                yield f"data: {json.dumps(payload)}\n\n"
        except asyncio.CancelledError:
            # cnnection closed by client

            pass
        finally:
            await unregister_sse_queue(session_id, q)
    return StreamingResponse(event_generator(), media_type="text/event-stream")

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