import os
import sys
import json
import warnings
from datetime import datetime
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, __version__ as pydantic_version
from crew import AiAgent
import traceback
from uvicorn import Config, Server
import asyncio
from common_functions.Find_project_root import find_project_root
from common_functions.User_preference import collect_preferences
from utils.logger import setup_logger
from firebase_client import create_user, sign_in_with_email, get_user_profile, set_user_profile, verify_id_token
from firebase_admin import auth
from fastapi import Body
from pydantic import BaseModel
from typing import Optional, List

PROJECT_ROOT = find_project_root()
logger = setup_logger()

# Global for current authenticated UID (for CLI session)
current_uid = None
class TaskRequest(BaseModel):
    title: str
    description: Optional[str] = None
    deadline: Optional[str] = None  # ISO string
    priority: str = "Medium"
    tags: Optional[List[str]] = None

class UpdateTaskRequest(BaseModel):
    status: Optional[str] = None
    title: Optional[str] = None
    # Add other fields as needed

class OperationRequest(BaseModel):
    name: str
    parameters: dict


# Suppress Pydantic warnings
if pydantic_version.startswith("2"):
    from pydantic import PydanticDeprecatedSince20
    warnings.filterwarnings("ignore", category=PydanticDeprecatedSince20)

# FastAPI app setup
app = FastAPI(title="AI Assistant API")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:8000", "http://127.0.0.1:8000", "*"],  # Adjust for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Pydantic models
class QueryRequest(BaseModel):
    query: str

class LoginRequest(BaseModel):
    email: str
    password: str

# API endpoint for auth
@app.post("/auth/login")
async def api_login(request: LoginRequest):  # Use Pydantic for validation
    try:
        uid = sign_in_with_email(request.email, request.password)
        # In real API, return custom token for client to exchange for ID token
        custom_token = auth.create_custom_token(uid)
        return {"uid": uid, "token": custom_token.decode()}  # Client exchanges for ID token
    except ValueError as e:
        raise HTTPException(status_code=401, detail=str(e))

# Middleware for protected routes (e.g., /process_query)
from fastapi import Depends
from fastapi.security import HTTPBearer

security = HTTPBearer()

async def get_current_uid(token: str = Depends(security)):
    try:
        uid = verify_id_token(token.credentials)
        return uid
    except ValueError:
        raise HTTPException(status_code=401, detail="Invalid token")

@app.post("/process_query")
async def process_query(request: QueryRequest, uid: str = Depends(get_current_uid)):
    logger.info(f"Received API query: {request.query}")
    if not request.query:
        logger.error("No query provided in API request")
        raise HTTPException(status_code=400, detail="No query provided")
    try:
        crew_instance = AiAgent()
        final_response = crew_instance.run_workflow(request.query)
        logger.debug(f"API response for query '{request.query}': {final_response}")
        return {"result": final_response}
    except Exception as e:
        logger.error(f"Error processing query '{request.query}': {str(e)}")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")

@app.post("/auth/login")
async def api_login(request: LoginRequest):
    try:
        uid = sign_in_with_email(request.email, request.password)
        custom_token = auth.create_custom_token(uid)
        # Client will exchange custom_token for ID token via Firebase SDK
        return {"uid": uid, "custom_token": custom_token.decode()}
    except ValueError as e:
        raise HTTPException(status_code=401, detail=str(e))

# New: Signup endpoint
@app.post("/auth/signup")
async def api_signup(request: LoginRequest):
    try:
        uid = create_user(request.email, request.password, request.email)  # Use email as display_name
        custom_token = auth.create_custom_token(uid)
        return {"uid": uid, "custom_token": custom_token.decode()}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

# Protected: Process query (unchanged, but add session_id)
class QueryRequest(BaseModel):
    query: str
    session_id: Optional[str] = None

@app.post("/process_query")
async def process_query(request: QueryRequest, uid: str = Depends(get_current_uid)):
    # Set global USER_ID for Firebase ops
    global current_uid
    current_uid = uid
    try:
        crew_instance = AiAgent()
        final_response = crew_instance.run_workflow(request.query, session_id=request.session_id)
        # Queue a mock op for demo (in real, crew does this)
        from firebase_client import queue_operation
        queue_operation("process_query", {"query": request.query})
        return {"result": final_response}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# New Endpoints for Tasks (CRUD)
@app.post("/tasks")
async def create_task(request: TaskRequest, uid: str = Depends(get_current_uid)):
    global current_uid; current_uid = uid
    from firebase_client import add_task
    task_id = add_task(
        title=request.title, description=request.description, due_date=request.deadline,
        priority=request.priority, related_files=request.tags  # Reuse tags as files for now
    )
    return {"task_id": task_id}

@app.get("/tasks")
async def get_tasks(status: Optional[str] = None, uid: str = Depends(get_current_uid)):
    global current_uid; current_uid = uid
    from firebase_client import get_tasks_by_user
    return get_tasks_by_user(status)

@app.put("/tasks/{task_id}")
async def update_task(task_id: str, request: UpdateTaskRequest, uid: str = Depends(get_current_uid)):
    global current_uid; current_uid = uid
    from firebase_client import update_task_by_user
    return update_task_by_user(task_id, request.dict(exclude_unset=True))

@app.delete("/tasks/{task_id}")
async def delete_task(task_id: str, uid: str = Depends(get_current_uid)):
    global current_uid; current_uid = uid
    from firebase_client import delete_task_by_user
    return delete_task_by_user(task_id)

# New Endpoints for Operations (Queue/Status)
@app.post("/operations")
async def queue_operation(request: OperationRequest, uid: str = Depends(get_current_uid)):
    global current_uid; current_uid = uid
    from firebase_client import queue_operation
    op_id = queue_operation(request.name, request.parameters)
    return {"op_id": op_id}

@app.get("/operations")
async def get_operations(status: Optional[str] = None, uid: str = Depends(get_current_uid)):
    global current_uid; current_uid = uid
    from firebase_client import get_operations_queue
    return get_operations_queue(status)

@app.put("/operations/{op_id}/status")
async def update_op_status(op_id: str, status: str, result: Optional[str] = None, uid: str = Depends(get_current_uid)):
    global current_uid; current_uid = uid
    from firebase_client import update_operation_status
    return update_operation_status(op_id, status, result)





# CLI-related functions
REQUIRED_PROFILE_KEYS = [
    "Name", "Role", "Location", "Productive Time", "Reminder Type",
    "Top Task Type", "Missed Task Handling", "Top Motivation",
    "AI Tone", "Break Reminder", "Mood Check", "Current Focus"
]

def display_welcome():
    message = "=" * 60 + "\n🤖 AI ASSISTANT - Firebase-Integrated CrewAI\n" + "=" * 60 + \
              "\nNow using Firestore for profiles, tasks, and memory!\n" + \
              "Use 'help' or 'h' for commands, 'quit' or 'q' to exit.\n" + "=" * 60
    print(message)
    logger.info("Displayed welcome message")

def display_help():
    message = "\nAvailable Commands:\n" + \
              "- help, h: Show this help message\n" + \
              "- quit, q: Exit the assistant\n" + \
              "- Any other input: Process as a query (e.g., 'List tasks', 'Create snapshot')\n" + \
              "\nExamples:\n" + \
              "- 'List files in /tmp' → Lists files using file.list operation\n" + \
              "- 'Create task Buy groceries' → Creates task in Firestore\n" + \
              "- 'Start focus session for 25 min' → Starts focus session"
    print(message)
    logger.info("Displayed help message")

def get_user_input(prompt="💬 What can I help you with? "):
    try:
        user_input = input(prompt).strip()
        logger.debug(f"Received CLI input: {user_input}")
        return user_input
    except KeyboardInterrupt:
        logger.info("CLI input interrupted by user")
        return "quit"

def authenticate_user(get_user_input=None):
    """Simple CLI auth flow: signup or login."""
    if get_user_input is None:
        get_user_input = input
    print("\n🔐 Authentication Required")
    choice = get_user_input("Sign up (s) or Login (l)? ").lower()
    email = get_user_input("Email: ")
    if choice == 's':
        password = get_user_input("Password: ")  # In prod, hash/secure this
        display_name = get_user_input("Display Name: ")
        try:
            uid = create_user(email, password, display_name)
            print(f"✅ Signed up! UID: {uid}")
        except ValueError as e:
            print(f"❌ Signup failed: {e}")
            return None
    else:  # login
        password = get_user_input("Password: ")
        try:
            uid = sign_in_with_email(email, password)
            print(f"✅ Logged in! UID: {uid}")
        except ValueError as e:
            print(f"❌ Login failed: {e}")
            return None
    return uid

def load_or_create_profile():
    """Load or create user profile in Firestore."""
    from firebase_client import get_user_profile
    logger.info("Loading or creating user profile")
    profile = get_user_profile()
    if not profile:
        logger.warning("No profile found in Firestore. Setting up...")
        print("No profile found in Firestore. Setting up...")
        name = get_user_input("Your name: ")
        email = get_user_input("Your email: ")
        set_user_profile(current_uid, email, display_name=name)  # Use global current_uid
        profile = get_user_profile()
        logger.info("Profile created in Firestore")
        print("✅ Profile created in Firestore.")
    missing = [k for k in REQUIRED_PROFILE_KEYS if k not in profile or not profile[k]]
    if missing:
        logger.warning(f"Missing profile fields: {missing}. Collecting...")
        print(f"Missing profile fields: {missing}. Collecting...")
        collect_preferences(None, get_user_input)  # Uses Firestore
        profile = get_user_profile()
    logger.debug(f"User profile loaded: {json.dumps(profile, default=str)}")
    return profile

def validate_environment():
    """Check Firebase connectivity."""
    logger.info("Validating Firebase connectivity")
    try:
        _ = get_user_profile()
        logger.info("Firebase connected successfully")
        print("✅ Firebase connected.")
        return True
    except Exception as e:
        logger.error(f"Firebase error: {str(e)}")
        print(f"❌ Firebase error: {str(e)}")
        return False

def run_single_query(user_query=None):
    global current_uid  # Access global UID
    logger.info(f"Processing single query: {user_query}")
    if not validate_environment():
        logger.error("Environment validation failed")
        return False
    # Auth only if not already authenticated
    if current_uid is None:
        uid = authenticate_user(get_user_input)
        if not uid:
            print("❌ Auth failed. Exiting.")
            return False
        current_uid = uid  # Set global for session
    profile = load_or_create_profile()
    if not user_query:
        user_query = get_user_input()
    if user_query.lower() in ["quit", "exit", "q"]:
        logger.info("User requested to quit")
        current_uid = None  # Reset on exit
        return False
    if user_query.lower() in ["help", "h"]:
        display_help()
        return True
    if not user_query:
        logger.debug("Empty query provided")
        return True
    print(f"\n🔍 Processing: '{user_query}' (Profile: {profile.get('Name', 'Unknown')})")
    logger.info(f"Processing query: {user_query} for user {profile.get('Name', 'Unknown')}")
    try:
        crew_instance = AiAgent()
        final_response = crew_instance.run_workflow(user_query)
        print(final_response)
        logger.debug(f"Query response: {final_response}")
        return True
    except Exception as e:
        logger.error(f"Error processing query '{user_query}': {str(e)}")
        print(f"❌ Error: {e}")
        traceback.print_exc()
        return True

async def run_server():
    """Run the FastAPI server."""
    logger.info("Starting FastAPI server on http://127.0.0.1:8000")
    config = Config(app=app, host="127.0.0.1", port=8000, log_level="info")
    server = Server(config)
    await server.serve()

def run_interactive():
    global current_uid  # Ensure global access
    display_welcome()
    try:
        while True:
            if not run_single_query():
                break
    except KeyboardInterrupt:
        logger.info("Interactive mode terminated by user")
        print("\n👋 Goodbye!")
        current_uid = None  # Reset on exit

def run():
    logger.info("Starting AI Assistant")
    if len(sys.argv) > 1 and sys.argv[1] == "--server":
        logger.info("Running in server mode")
        asyncio.run(run_server())
    elif len(sys.argv) > 1:
        query = " ".join(sys.argv[1:]).strip('"')
        logger.info(f"Running single query mode with: {query}")
        run_single_query(query)
    else:
        logger.info("Running in interactive CLI mode")
        run_interactive()

def train():
    logger.info("Train function called (not implemented)")
    pass

def replay():
    logger.info("Replay function called (not implemented)")
    pass

def test():
    logger.info("Test function called (not implemented)")
    pass

if __name__ == "__main__":
    run()