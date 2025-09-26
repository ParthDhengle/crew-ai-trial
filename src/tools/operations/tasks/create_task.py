from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from firebase_client import get_user_profile
from typing import Optional, List, Tuple
from datetime import datetime
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


def create_task(title: str, description: Optional[str] = None, deadline: Optional[str] = None, 
                priority: str = "Medium", tags: Optional[List[str]] = None) -> Tuple[bool, str]:
    try:
        profile = get_user_profile()
        tokens = profile.get('integrations', {}).get('google_calendar', {}).get('tokens', {})
        if not tokens:
            return False, "Google Tasks not connected"
        
        creds = Credentials(
            token=tokens.get('access_token'),
            refresh_token=tokens.get('refresh_token'),
            token_uri='https://oauth2.googleapis.com/token',
            client_id=GOOGLE_CLIENT_ID,
            client_secret=GOOGLE_CLIENT_SECRET
        )
        
        if creds.expired and creds.refresh_token:
            creds.refresh(Request())
        
        service = build('tasks', 'v1', credentials=creds)
        
        task_body = {
            'title': title,
            'notes': description
        }
        
        if deadline:
            task_body['due'] = deadline + 'T00:00:00Z'
        
        notes = task_body.get('notes', '')
        notes += f"\nPriority: {priority}"
        if tags:
            notes += f"\nTags: {', '.join(tags)}"
        task_body['notes'] = notes
        
        task = service.tasks().insert(tasklist='@default', body=task_body).execute()
        return True, f"Task created: {task['id']}"
    
    except Exception as e:
        return False, str(e)