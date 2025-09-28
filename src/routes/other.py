from fastapi import APIRouter, Depends
from firebase_client import get_current_uid
from googleapiclient.discovery import build
from routes.auth import get_google_creds

other_router = APIRouter(prefix="/api")

@other_router.get("/calendars")
async def list_calendars(uid: str = Depends(get_current_uid)):
    creds = get_google_creds(uid)
    service = build('calendar', 'v3', credentials=creds)
    calendars = service.calendarList().list().execute()
    return calendars.get('items', [])

@other_router.get("/people/suggest")
async def suggest_people(query: str, uid: str = Depends(get_current_uid)):
    creds = get_google_creds(uid)
    service = build('people', 'v1', credentials=creds)
    results = service.people().searchContacts(query=query, readMask='names,emailAddresses').execute()
    return results.get('results', [])

@other_router.get("/timezones")
async def get_timezones(uid: str = Depends(get_current_uid)):
    creds = get_google_creds(uid)
    service = build('calendar', 'v3', credentials=creds)
    timezones = service.settings().get(setting='timeZone').execute()
    return timezones