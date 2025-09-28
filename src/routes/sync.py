from fastapi import APIRouter, Depends
from typing import Optional
from firebase_client import get_current_uid
from googleapiclient.discovery import build
import uuid
from firebase_admin import firestore
from firebase_client import db
from routes.auth import get_google_creds
sync_router = APIRouter(prefix="/api/sync")

@sync_router.post("/subscribe")
async def subscribe_sync(calendarId: str = 'primary', uid: str = Depends(get_current_uid)):
    creds = get_google_creds(uid)
    service = build('calendar', 'v3', credentials=creds)
    channel_id = str(uuid.uuid4())
    body = {
        'id': channel_id,
        'type': 'web_hook',
        'address': 'https://your-public-domain/webhook/google'  # Use ngrok for dev
    }
    watch = service.events().watch(calendarId=calendarId, body=body).execute()
    db.collection('users').document(uid).update({
        'integrations.google_calendar.channels': firestore.ArrayUnion([{
            'id': channel_id,
            'resourceId': watch['resourceId'],
            'expiration': watch['expiration']
        }])
    })
    return {"ok": True, "channel_id": channel_id}

@sync_router.post("/unsubscribe")
async def unsubscribe_sync(channel_id: str, resource_id: str, uid: str = Depends(get_current_uid)):
    creds = get_google_creds(uid)
    service = build('calendar', 'v3', credentials=creds)
    body = {
        'id': channel_id,
        'resourceId': resource_id
    }
    service.channels().stop(body=body).execute()
    db.collection('users').document(uid).update({
        'integrations.google_calendar.channels': firestore.ArrayRemove([{
            'id': channel_id,
            'resourceId': resource_id
        }])
    })
    return {"ok": True}