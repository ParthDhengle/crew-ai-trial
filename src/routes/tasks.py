from fastapi import APIRouter, Depends, HTTPException
from typing import Optional, List, Dict
from firebase_client import get_current_uid
from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from firebase_client import db
from typing import Dict
import json
import os
from dotenv import load_dotenv
load_dotenv()
client_secret_path = os.getenv("GOOGLE_CLIENT_SECRET_PATH")

GOOGLE_CLIENT_ID = None
GOOGLE_CLIENT_SECRET = None

if client_secret_path and os.path.exists(client_secret_path):
    with open(client_secret_path, "r") as f:
        data = json.load(f)
        # Some Google JSONs have "installed" key, some have "web"
        creds = data.get("installed") or data.get("web")
        GOOGLE_CLIENT_ID = creds.get("client_id")
        GOOGLE_CLIENT_SECRET = creds.get("client_secret")

tasks_router = APIRouter(prefix="/api/tasks")

def get_google_creds(uid: str) -> Credentials:
    user_doc = db.collection('users').document(uid).get()
    if not user_doc.exists:
        raise HTTPException(404, "User not found")  # Or 401 if preferred; add logging if needed
    user = user_doc.to_dict()
    tokens = user.get('integrations', {}).get('google_calendar', {}).get('tokens', {})
    if not tokens.get('refresh_token'):
        raise HTTPException(401, "Google integration not connected")
    
    creds = Credentials(
        token=tokens['access_token'],
        refresh_token=tokens['refresh_token'],
        token_uri='https://oauth2.googleapis.com/token',
        client_id=GOOGLE_CLIENT_ID,
        client_secret=GOOGLE_CLIENT_SECRET
    )
    
    if creds.expired and creds.refresh_token:
        creds.refresh(Request())
        new_tokens = {
            'access_token': creds.token,
            'expiry': creds.expiry.isoformat() if creds.expiry else None
        }
        db.collection('users').document(uid).update({
            'integrations.google_calendar.tokens.access_token': new_tokens['access_token'],
            'integrations.google_calendar.tokens.expiry': new_tokens['expiry']
        })
    
    return creds

@tasks_router.get("")
async def list_tasks(tasklist: str = '@default', showCompleted: bool = False, maxResults: int = 100, pageToken: Optional[str] = None, uid: str = Depends(get_current_uid)):
    creds = get_google_creds(uid)
    service = build('tasks', 'v1', credentials=creds)
    tasks_result = service.tasks().list(
        tasklist=tasklist,
        showCompleted=showCompleted,
        maxResults=maxResults,
        pageToken=pageToken
    ).execute()
    return tasks_result.get('items', [])

@tasks_router.get("/{tasklist}/{taskId}")
async def get_task(tasklist: str, taskId: str, uid: str = Depends(get_current_uid)):
    creds = get_google_creds(uid)
    service = build('tasks', 'v1', credentials=creds)
    task = service.tasks().get(tasklist=tasklist, task=taskId).execute()
    return task

@tasks_router.post("")
async def create_task_api(body: Dict, tasklist: str = '@default', uid: str = Depends(get_current_uid)):
    creds = get_google_creds(uid)
    service = build('tasks', 'v1', credentials=creds)
    task = service.tasks().insert(tasklist=tasklist, body=body).execute()
    return task

@tasks_router.patch("/{tasklist}/{taskId}")
async def patch_task(tasklist: str, taskId: str, body: Dict, uid: str = Depends(get_current_uid)):
    creds = get_google_creds(uid)
    service = build('tasks', 'v1', credentials=creds)
    task = service.tasks().patch(tasklist=tasklist, task=taskId, body=body).execute()
    return task

@tasks_router.delete("/{tasklist}/{taskId}")
async def delete_task_api(tasklist: str, taskId: str, uid: str = Depends(get_current_uid)):
    creds = get_google_creds(uid)
    service = build('tasks', 'v1', credentials=creds)
    service.tasks().delete(tasklist=tasklist, task=taskId).execute()
    return {"ok": True}

@tasks_router.post("/{tasklist}/{taskId}/move")
async def move_task(tasklist: str, taskId: str, body: Dict, uid: str = Depends(get_current_uid)):
    creds = get_google_creds(uid)
    service = build('tasks', 'v1', credentials=creds)
    task = service.tasks().move(tasklist=tasklist, task=taskId, body=body).execute()
    return task

@tasks_router.post("/bulk")
async def bulk_tasks(body: List[Dict], uid: str = Depends(get_current_uid)):
    creds = get_google_creds(uid)
    service = build('tasks', 'v1', credentials=creds)
    results = []
    for task_data in body:
        tasklist = task_data.pop('tasklist', '@default')
        task = service.tasks().insert(tasklist=tasklist, body=task_data).execute()
        results.append(task)
    return results