# src/routes/events.py
from fastapi import APIRouter, Depends, HTTPException
from typing import Optional, List, Dict
from firebase_client import get_current_uid
from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from firebase_client import db
from typing import Dict
import os
from dotenv import load_dotenv
import json
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

events_router = APIRouter(prefix="/api/events", tags=["events"])

def get_google_creds(uid: str) -> Credentials:
    user_doc = db.collection('users').document(uid).get()
    if not user_doc.exists:
        raise HTTPException(404, "User not found")
        
    user = user_doc.to_dict()
    tokens = user.get('integrations', {}).get('google_calendar', {}).get('tokens', {})
    if not tokens.get('refresh_token'):
        raise HTTPException(401, "Google Calendar not connected. Please connect your Google Calendar first.")
    
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

@events_router.get("")
async def list_events(
    calendarId: str = 'primary',
    timeMin: Optional[str] = None,
    timeMax: Optional[str] = None,
    singleEvents: bool = True,
    orderBy: str = 'startTime',
    maxResults: int = 100,
    pageToken: Optional[str] = None,
    syncToken: Optional[str] = None,
    showDeleted: bool = False,
    uid: str = Depends(get_current_uid)
):
    try:
        creds = get_google_creds(uid)
        service = build('calendar', 'v3', credentials=creds)
        
        params = {
            'calendarId': calendarId,
            'singleEvents': singleEvents,
            'maxResults': maxResults,
            'showDeleted': showDeleted
        }
        
        # Add optional parameters
        if timeMin:
            params['timeMin'] = timeMin
        if timeMax:
            params['timeMax'] = timeMax
        if orderBy and singleEvents:  # orderBy only works with singleEvents=True
            params['orderBy'] = orderBy
        if pageToken:
            params['pageToken'] = pageToken
        if syncToken:
            params['syncToken'] = syncToken
            
        events_result = service.events().list(**params).execute()
        return events_result.get('items', [])
        
    except Exception as e:
        raise HTTPException(500, f"Failed to fetch events: {str(e)}")

@events_router.get("/{calendarId}/{eventId}")
async def get_event(calendarId: str, eventId: str, uid: str = Depends(get_current_uid)):
    try:
        creds = get_google_creds(uid)
        service = build('calendar', 'v3', credentials=creds)
        event = service.events().get(calendarId=calendarId, eventId=eventId).execute()
        return event
    except Exception as e:
        raise HTTPException(500, f"Failed to get event: {str(e)}")

@events_router.post("")
async def create_event(
    body: Dict, 
    calendarId: str = 'primary',
    sendUpdates: str = 'none', 
    conferenceDataVersion: int = 1, 
    supportsAttachments: bool = True, 
    uid: str = Depends(get_current_uid)
):
    try:
        creds = get_google_creds(uid)
        service = build('calendar', 'v3', credentials=creds)
        
        event = service.events().insert(
            calendarId=calendarId,
            body=body,
            sendUpdates=sendUpdates,
            conferenceDataVersion=conferenceDataVersion,
            supportsAttachments=supportsAttachments
        ).execute()
        
        return event
    except Exception as e:
        raise HTTPException(500, f"Failed to create event: {str(e)}")

@events_router.patch("/{calendarId}/{eventId}")
async def patch_event(
    calendarId: str, 
    eventId: str, 
    body: Dict, 
    sendUpdates: str = 'none', 
    conferenceDataVersion: int = 1, 
    supportsAttachments: bool = True, 
    uid: str = Depends(get_current_uid)
):
    try:
        creds = get_google_creds(uid)
        service = build('calendar', 'v3', credentials=creds)
        
        event = service.events().patch(
            calendarId=calendarId,
            eventId=eventId,
            body=body,
            sendUpdates=sendUpdates,
            conferenceDataVersion=conferenceDataVersion,
            supportsAttachments=supportsAttachments
        ).execute()
        
        return event
    except Exception as e:
        raise HTTPException(500, f"Failed to update event: {str(e)}")

@events_router.put("/{calendarId}/{eventId}")
async def update_event_full(
    calendarId: str, 
    eventId: str, 
    body: Dict, 
    sendUpdates: str = 'none', 
    conferenceDataVersion: int = 1, 
    supportsAttachments: bool = True, 
    uid: str = Depends(get_current_uid)
):
    try:
        creds = get_google_creds(uid)
        service = build('calendar', 'v3', credentials=creds)
        
        event = service.events().update(
            calendarId=calendarId,
            eventId=eventId,
            body=body,
            sendUpdates=sendUpdates,
            conferenceDataVersion=conferenceDataVersion,
            supportsAttachments=supportsAttachments
        ).execute()
        
        return event
    except Exception as e:
        raise HTTPException(500, f"Failed to update event: {str(e)}")

@events_router.delete("/{calendarId}/{eventId}")
async def delete_event_api(
    calendarId: str, 
    eventId: str, 
    sendUpdates: str = 'none', 
    uid: str = Depends(get_current_uid)
):
    try:
        creds = get_google_creds(uid)
        service = build('calendar', 'v3', credentials=creds)
        
        service.events().delete(
            calendarId=calendarId,
            eventId=eventId,
            sendUpdates=sendUpdates
        ).execute()
        
        return {"ok": True, "message": "Event deleted successfully"}
    except Exception as e:
        raise HTTPException(500, f"Failed to delete event: {str(e)}")

@events_router.post("/quick-add")
async def quick_add_event(
    text: str, 
    calendarId: str = 'primary', 
    uid: str = Depends(get_current_uid)
):
    try:
        creds = get_google_creds(uid)
        service = build('calendar', 'v3', credentials=creds)
        
        event = service.events().quickAdd(
            calendarId=calendarId,
            text=text
        ).execute()
        
        return event
    except Exception as e:
        raise HTTPException(500, f"Failed to quick-add event: {str(e)}")

@events_router.post("/bulk")
async def bulk_events(body: List[Dict], uid: str = Depends(get_current_uid)):
    try:
        creds = get_google_creds(uid)
        service = build('calendar', 'v3', credentials=creds)
        
        results = []
        errors = []
        
        for i, event_data in enumerate(body):
            try:
                event = service.events().insert(calendarId='primary', body=event_data).execute()
                results.append(event)
            except Exception as e:
                errors.append({"index": i, "error": str(e)})
        
        return {"created": results, "errors": errors}
    except Exception as e:
        raise HTTPException(500, f"Failed to create bulk events: {str(e)}")