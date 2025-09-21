import os
import sys
import json
import warnings
from datetime import datetime
from collections import defaultdict
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
    queue_operation, get_operations_queue, update_operation_status
)
from firebase_admin import auth
from fastapi.security import HTTPBearer
from typing import Optional

PROJECT_ROOT = find_project_root()
logger = setup_logger()

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

# Protected Routes
@app.post("/process_query")
async def process_query(request: QueryRequest, uid: str = Depends(get_current_uid)):
    global current_uid
    current_uid = uid
    try:
        from firebase_client import save_chat_message
        timestamp = datetime.now().isoformat()

        # Save user query
        save_chat_message(request.session_id, uid, "user", request.query, timestamp)

        # Run AI agent
        crew_instance = AiAgent()
        final_response = crew_instance.run_workflow(request.query, session_id=request.session_id)

        # Save assistant response
        save_chat_message(request.session_id, uid, "assistant", final_response, datetime.now().isoformat())

        # Queue op
        queue_operation("process_query", {"query": request.query})
        return {"result": final_response["display_response"]}
    except Exception as e:
        logger.error(f"Error processing query: {str(e)}")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")

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

@app.get("/chat_sessions")
async def get_chat_sessions(uid: str = Depends(get_current_uid)):
    history = get_chat_history()  # All messages for user
    sessions = defaultdict(lambda: {
        'id': None,
        'title': None,
        'summary': '',
        'messages': [],
        'createdAt': float('inf'),
        'updatedAt': float('-inf')
    })
    
    for msg in history:
        sid = msg.get('session_id') or 'default'
        session = sessions[sid]
        session['id'] = sid
        session['title'] = f"Chat {sid}"  # Can improve with AI title generation later
        session['messages'].append(msg)
        ts = datetime.fromisoformat(msg['timestamp']).timestamp() * 1000  # ms for JS
        session['createdAt'] = min(session['createdAt'], ts)
        session['updatedAt'] = max(session['updatedAt'], ts)
    
    # Compute summaries (first message content truncated)
    for sid, data in sessions.items():
        if data['messages']:
            first_msg = sorted(data['messages'], key=lambda m: m['timestamp'])[0]
            data['summary'] = first_msg['content'][:100] + '...'
            # Include full messages or just metadata? For list, omit messages to save bandwidth
            del data['messages']  # Don't send full history in list
    
    return list(sessions.values())

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
@app.get("/chat_history")
async def get_chat_history(session_id: str = None, uid: str = Depends(get_current_uid)):
    global current_uid; current_uid = uid
    from firebase_client import get_chat_history
    history = get_chat_history(session_id)
    return history  # List of message dicts
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


# Run server
async def run_server():
    logger.info("Starting FastAPI server on http://127.0.0.1:8001")
    config = Config(app=app, host="127.0.0.1", port=8001, log_level="info")
    server = Server(config)
    await server.serve()

if __name__ == "__main__":
    asyncio.run(run_server())