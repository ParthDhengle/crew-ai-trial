from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from firebase_client import get_user_profile
from typing import Tuple
import os
from dotenv import load_dotenv
load_dotenv()
import json
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


def delete_event(event_id: str, calendar_id: str = 'primary') -> Tuple[bool, str]:
    try:
        profile = get_user_profile()
        tokens = profile.get('integrations', {}).get('google_calendar', {}).get('tokens', {})
        if not tokens:
            return False, "Google Calendar not connected"
        
        creds = Credentials(
            token=tokens.get('access_token'),
            refresh_token=tokens.get('refresh_token'),
            token_uri='https://oauth2.googleapis.com/token',
            client_id=GOOGLE_CLIENT_ID,
            client_secret=GOOGLE_CLIENT_SECRET
        )
        
        if creds.expired and creds.refresh_token:
            creds.refresh(Request())
        
        service = build('calendar', 'v3', credentials=creds)
        
        service.events().delete(calendarId=calendar_id, eventId=event_id).execute()
        return True, f"Event {event_id} deleted"
    
    except Exception as e:
        return False, str(e)