from fastapi import APIRouter, Depends, HTTPException
from typing import Optional, List, Dict
from firebase_client import get_current_uid
from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from firebase_client import db
from typing import Dict
import os

tasks_router = APIRouter(prefix="/api/tasks")


def get_google_creds(uid: str) -> Credentials:
    user_doc = db.collection('users').document(uid).get()
    if not user_doc.exists:
        raise HTTPException(404, "User not found")
        
    user = user_doc.to_dict()
    google_cal = user.get('integrations', {}).get('google_calendar', {})
    client_id = google_cal.get('client_id')
    client_secret = google_cal.get('client_secret')
    tokens = google_cal.get('tokens', {})
    
    if not client_id or not client_secret:
        raise HTTPException(401, "Google credentials not set. Please add client ID and secret manually in Firestore.")
    
    if not tokens.get('refresh_token'):
        raise HTTPException(401, "Google Calendar not connected. Please add refresh token manually in Firestore.")
    
    creds = Credentials(
        token=tokens.get('access_token'),
        refresh_token=tokens.get('refresh_token'),
        token_uri='https://oauth2.googleapis.com/token',
        client_id=client_id,
        client_secret=client_secret
    )
    
    if creds.expired and creds.refresh_token:
        creds.refresh(Request())
        new_tokens = {
            'access_token': creds.token,
            'expiry': creds.expiry.isoformat() if creds.expiry else None
        }
        db.collection('users').document(uid).update({
            'integrations.google_calendar.tokens': new_tokens
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