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

events_router = APIRouter(prefix="/api/events")

def get_google_creds(uid: str) -> Credentials:
    user = db.collection('users').document(uid).get().to_dict()
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
    creds = get_google_creds(uid)
    service = build('calendar', 'v3', credentials=creds)
    events_result = service.events().list(
        calendarId=calendarId,
        timeMin=timeMin,
        timeMax=timeMax,
        singleEvents=singleEvents,
        orderBy=orderBy,
        maxResults=maxResults,
        pageToken=pageToken,
        syncToken=syncToken,
        showDeleted=showDeleted
    ).execute()
    return events_result.get('items', [])

@events_router.get("/{calendarId}/{eventId}")
async def get_event(calendarId: str, eventId: str, uid: str = Depends(get_current_uid)):
    creds = get_google_creds(uid)
    service = build('calendar', 'v3', credentials=creds)
    event = service.events().get(calendarId=calendarId, eventId=eventId).execute()
    return event

@events_router.post("")
async def create_event(body: Dict, sendUpdates: str = 'none', conferenceDataVersion: int = 1, supportsAttachments: bool = True, uid: str = Depends(get_current_uid)):
    creds = get_google_creds(uid)
    service = build('calendar', 'v3', credentials=creds)
    event = service.events().insert(
        calendarId='primary',
        body=body,
        sendUpdates=sendUpdates,
        conferenceDataVersion=conferenceDataVersion,
        supportsAttachments=supportsAttachments
    ).execute()
    return event

@events_router.patch("/{calendarId}/{eventId}")
async def patch_event(calendarId: str, eventId: str, body: Dict, sendUpdates: str = 'none', conferenceDataVersion: int = 1, supportsAttachments: bool = True, uid: str = Depends(get_current_uid)):
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

@events_router.put("/{calendarId}/{eventId}")
async def update_event_full(calendarId: str, eventId: str, body: Dict, sendUpdates: str = 'none', conferenceDataVersion: int = 1, supportsAttachments: bool = True, uid: str = Depends(get_current_uid)):
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

@events_router.delete("/{calendarId}/{eventId}")
async def delete_event_api(calendarId: str, eventId: str, sendUpdates: str = 'none', uid: str = Depends(get_current_uid)):
    creds = get_google_creds(uid)
    service = build('calendar', 'v3', credentials=creds)
    service.events().delete(
        calendarId=calendarId,
        eventId=eventId,
        sendUpdates=sendUpdates
    ).execute()
    return {"ok": True}

@events_router.get("/{calendarId}/{eventId}/instances")
async def list_instances(calendarId: str, eventId: str, timeMin: Optional[str] = None, timeMax: Optional[str] = None, uid: str = Depends(get_current_uid)):
    creds = get_google_creds(uid)
    service = build('calendar', 'v3', credentials=creds)
    instances = service.events().instances(
        calendarId=calendarId,
        eventId=eventId,
        timeMin=timeMin,
        timeMax=timeMax
    ).execute()
    return instances.get('items', [])

@events_router.post("/quick-add")
async def quick_add_event(text: str, calendarId: str = 'primary', uid: str = Depends(get_current_uid)):
    creds = get_google_creds(uid)
    service = build('calendar', 'v3', credentials=creds)
    event = service.events().quickAdd(
        calendarId=calendarId,
        text=text
    ).execute()
    return event

@events_router.post("/bulk")
async def bulk_events(body: List[Dict], uid: str = Depends(get_current_uid)):
    creds = get_google_creds(uid)
    service = build('calendar', 'v3', credentials=creds)
    results = []
    for event_data in body:
        event = service.events().insert(calendarId='primary', body=event_data).execute()
        results.append(event)
    return results