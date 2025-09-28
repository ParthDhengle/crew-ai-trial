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


events_router = APIRouter(prefix="/api/events", tags=["events"])

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
        try:  # NEW: Catch refresh errors
            creds.refresh(Request())
            new_tokens = {
                'access_token': creds.token,
                'expiry': creds.expiry.isoformat() if creds.expiry else None
            }
            db.collection('users').document(uid).update({
                'integrations.google_calendar.tokens.access_token': new_tokens['access_token'],
                'integrations.google_calendar.tokens.expiry': new_tokens['expiry']
            })
        except Exception as refresh_err:
            print(f"Token refresh failed for user {uid}: {str(refresh_err)}")  # NEW: Log error
            raise HTTPException(500, f"Failed to refresh Google token: {str(refresh_err)}")
        
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