from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from firebase_client import get_user_profile
from typing import Optional, List, Tuple
from datetime import datetime
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


def create_event(summary: str, start_time: str, end_time: str, description: Optional[str] = None, 
                 location: Optional[str] = None, attendees: Optional[List[str]] = None) -> Tuple[bool, str]:
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
        
        event_body = {
            'summary': summary,
            'description': description,
            'location': location,
            'start': {'dateTime': start_time},
            'end': {'dateTime': end_time}
        }
        
        if attendees:
            event_body['attendees'] = [{'email': email} for email in attendees]
        
        event = service.events().insert(calendarId='primary', body=event_body).execute()
        return True, f"Event created: {event.get('htmlLink')}"
    
    except Exception as e:
        return False, str(e)