import os
import sys
import json
import warnings
from datetime import datetime
from fastapi import FastAPI, HTTPException
from fastapi import Body
from typing import Optional, List, Dict, Any
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, __version__ as pydantic_version
from .crew import AiAgent
import traceback
from uvicorn import Config, Server
import asyncio
from dotenv import load_dotenv # Import load_dotenv
from .common_functions.Find_project_root import find_project_root
from .firebase_client import get_user_profile, set_user_profile
from .common_functions.User_preference import collect_preferences
from .utils.logger import setup_logger
from fastapi import UploadFile, File, Form
import tempfile
import shutil

PROJECT_ROOT = find_project_root()
load_dotenv(os.path.join(PROJECT_ROOT, '.env')) # Load .env file
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
    allow_origins=[
        "http://localhost:8000",
        "http://127.0.0.1:8000",
        "http://localhost:8001",
        "http://127.0.0.1:8001",
        "*",
    ],  # Adjust for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Pydantic model for query input
class QueryRequest(BaseModel):
    query: str


# ===== Additional API Schemas =====
class Profile(BaseModel):
    name: str
    email: str
    timezone: Optional[str] = "UTC"
    focus_hours: Optional[List[Any]] = None
    permissions: Optional[Dict[str, Any]] = None
    integrations: Optional[Dict[str, Any]] = None


class TaskCreate(BaseModel):
    title: str
    description: Optional[str] = None
    due_date: Optional[str] = None
    priority: Optional[str] = "medium"


class TaskUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    due_date: Optional[str] = None
    priority: Optional[str] = None
    status: Optional[str] = None


class ChatMessage(BaseModel):
    role: str
    content: str
    session_id: Optional[str] = None


class EventCreate(BaseModel):
    calendar_id: str
    title: str
    start: str
    end: str
    attendees: Optional[List[str]] = None
    location: Optional[str] = None

# API endpoint for processing queries
@app.post("/process_query")
async def process_query(request: QueryRequest):
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


# =================== PROFILE ===================
@app.get("/profile")
async def get_profile():
    try:
        profile = get_user_profile()
        if not profile:
            return {}
        return profile
    except Exception as e:
        logger.error(f"Error fetching profile: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/profile")
async def upsert_profile(p: Profile):
    try:
        set_user_profile(
            name=p.name,
            email=p.email,
            timezone=p.timezone or "UTC",
            focus_hours=p.focus_hours or [],
            permissions=p.permissions or {},
            integrations=p.integrations or {},
        )
        return {"ok": True}
    except Exception as e:
        logger.error(f"Error updating profile: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# =================== TASKS ===================
from .firebase_client import (
    add_task, get_tasks, update_task, mark_task_complete,
    add_chat_message, get_chat_history
)


@app.get("/tasks")
async def list_tasks(status: Optional[str] = None):
    try:
        return get_tasks(status=status)
    except Exception as e:
        logger.error(f"Error listing tasks: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/tasks")
async def create_task(task: TaskCreate):
    try:
        task_id = add_task(
            title=task.title,
            description=task.description,
            due_date=task.due_date,
            priority=task.priority or "medium",
        )
        return {"id": task_id}
    except Exception as e:
        logger.error(f"Error creating task: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.patch("/tasks/{task_id}")
async def update_task_api(task_id: str, updates: TaskUpdate):
    try:
        ok = update_task(task_id, {k: v for k, v in updates.dict().items() if v is not None})
        if not ok:
            raise HTTPException(status_code=404, detail="Task not found or update failed")
        return {"ok": True}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating task: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/tasks/{task_id}/complete")
async def complete_task(task_id: str):
    try:
        ok = mark_task_complete(task_id)
        if not ok:
            raise HTTPException(status_code=404, detail="Task not found or complete failed")
        return {"ok": True}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error completing task: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# =================== CHAT HISTORY ===================
@app.get("/chat_history")
async def list_chat(session_id: Optional[str] = None):
    try:
        return get_chat_history(session_id=session_id)
    except Exception as e:
        logger.error(f"Error fetching chat history: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/chat_message")
async def create_chat_message(msg: ChatMessage):
    try:
        message_id = add_chat_message(role=msg.role, content=msg.content, session_id=msg.session_id)
        return {"id": message_id}
    except Exception as e:
        logger.error(f"Error adding chat message: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# =================== EVENTS ===================
from .tools.operations.events.create_event import create_event as create_calendar_event
from .tools.operations.powerbi_dashboard import powerbi_generate_dashboard


@app.post("/events")
async def create_event_api(event: EventCreate):
    try:
        ok, msg = create_calendar_event(
            calendar_id=event.calendar_id,
            title=event.title,
            start=event.start,
            end=event.end,
            attendees=event.attendees or [],
            location=event.location or "",
        )
        if not ok:
            raise HTTPException(status_code=400, detail=msg)
        return {"ok": True, "message": msg}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating event: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# =================== POWER BI ===================
class SuggestRequest(BaseModel):
    query: str
    columns: List[str]


@app.post("/powerbi/upload")
async def powerbi_upload(file: UploadFile = File(...)):
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(file.filename)[1]) as tmp:
            shutil.copyfileobj(file.file, tmp)
            saved_path = tmp.name
        return {"temp_path": saved_path}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/powerbi/generate")
async def powerbi_generate(temp_path: str = Form(...), query: str = Form(""), auto_open: bool = Form(False)):
    try:
        if auto_open:
            os.environ["PBI_AUTO_OPEN"] = "1"
        else:
            os.environ["PBI_AUTO_OPEN"] = "0"
        ok, msg = powerbi_generate_dashboard(temp_path, query or "Create suitable visuals.")
        return {"ok": ok, "message": msg}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

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

def load_or_create_profile():
    """Load or create user profile in Firestore."""
    logger.info("Loading or creating user profile")
    profile = get_user_profile()
    if not profile:
        logger.warning("No profile found in Firestore. Setting up...")
        print("No profile found in Firestore. Setting up...")
        name = get_user_input("Your name: ")
        email = get_user_input("Your email: ")
        set_user_profile(name, email)
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
    logger.info(f"Processing single query: {user_query}")
    if not validate_environment():
        logger.error("Environment validation failed")
        return False
    profile = load_or_create_profile()
    if not user_query:
        user_query = get_user_input()
    if user_query.lower() in ["quit", "exit", "q"]:
        logger.info("User requested to quit")
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
    host = os.getenv("HOST", "127.0.0.1")
    port = int(os.getenv("PORT", "8001"))
    logger.info(f"Starting FastAPI server on http://{host}:{port}")
    config = Config(app=app, host=host, port=port, log_level="info")
    server = Server(config)
    await server.serve()

def run_interactive():
    display_welcome()
    try:
        while True:
            if not run_single_query():
                break
    except KeyboardInterrupt:
        logger.info("Interactive mode terminated by user")
        print("\n👋 Goodbye!")

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
