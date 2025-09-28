from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from src.firebase_client import db
from typing import Optional, List, Dict, Tuple
import json
import os
from dotenv import load_dotenv

load_dotenv()

def get_google_creds(uid: str) -> Credentials:
    """Retrieve and refresh Google Calendar credentials for the given user ID."""
    try:
        user_doc = db.collection('users').document(uid).get()
        if not user_doc.exists:
            raise ValueError("User not found")

        user = user_doc.to_dict()
        google_cal = user.get('integrations', {}).get('google_calendar', {})
        client_id = google_cal.get('client_id')
        client_secret = google_cal.get('client_secret')
        tokens = google_cal.get('tokens', {})

        if not client_id or not client_secret:
            raise ValueError("Google credentials not set. Please add client ID and secret manually in Firestore.")

        if not tokens.get('refresh_token'):
            raise ValueError("Google Calendar not connected. Please add refresh token manually in Firestore.")

        creds = Credentials(
            token=tokens.get('access_token'),
            refresh_token=tokens.get('refresh_token'),
            token_uri='https://oauth2.googleapis.com/token',
            client_id=client_id,
            client_secret=client_secret
        )

        if creds.expired and creds.refresh_token:
            try:
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
                print(f"Token refresh failed for user {uid}: {str(refresh_err)}")
                raise ValueError(f"Failed to refresh Google token: {str(refresh_err)}")

        return creds

    except Exception as e:
        raise ValueError(str(e))

def create_task(
    title: str,
    description: Optional[str] = None,
    deadline: Optional[str] = None,
    priority: str = "Medium",
    tags: Optional[List[str]] = None,
    uid: str = None
) -> Tuple[bool, str]:
    """Create a new task as a Google Calendar event."""
    try:
        creds = get_google_creds(uid)
        service = build('calendar', 'v3', credentials=creds)

        event_body = {
            'summary': title,
            'description': description or '',
            'extendedProperties': {
                'private': {
                    'type': 'task',
                    'status': 'needsAction',
                    'priority': priority,
                    'tags': json.dumps(tags or [])
                }
            }
        }

        if deadline:
            event_body['start'] = {'date': deadline}
            event_body['end'] = {'date': deadline}

        event = service.events().insert(
            calendarId='primary',
            body=event_body
        ).execute()

        return True, f"Task created: {event['id']}"

    except ValueError as ve:
        return False, str(ve)
    except Exception as e:
        return False, f"Failed to create task: {str(e)}"

def read_task(
    status: Optional[str] = None,
    uid: str = None
) -> Tuple[bool, str]:
    """Retrieve tasks from Google Calendar, optionally filtered by status."""
    try:
        creds = get_google_creds(uid)
        service = build('calendar', 'v3', credentials=creds)

        params = {
            'calendarId': 'primary',
            'maxResults': 100,
            'singleEvents': True,
            'orderBy': 'startTime'
        }

        events_result = service.events().list(**params).execute()
        items = events_result.get('items', [])
        tasks = []

        for event in items:
            ext = event.get('extendedProperties', {}).get('private', {})
            if ext.get('type') == 'task':
                if status is None or ext.get('status') == status:
                    task = {
                        'id': event['id'],
                        'title': event['summary'],
                        'description': event.get('description'),
                        'due': event.get('start', {}).get('date') or event.get('start', {}).get('dateTime'),
                        'status': ext.get('status'),
                        'priority': ext.get('priority'),
                        'tags': json.loads(ext.get('tags', '[]'))
                    }
                    tasks.append(task)

        return True, json.dumps(tasks)

    except ValueError as ve:
        return False, str(ve)
    except Exception as e:
        return False, f"Failed to fetch tasks: {str(e)}"

def update_task(
    task_id: str,
    status: Optional[str] = None,
    title: Optional[str] = None,
    description: Optional[str] = None,
    deadline: Optional[str] = None,
    priority: Optional[str] = None,
    tags: Optional[List[str]] = None,
    uid: str = None
) -> Tuple[bool, str]:
    """Update an existing task in Google Calendar."""
    try:
        creds = get_google_creds(uid)
        service = build('calendar', 'v3', credentials=creds)

        body = {}
        if title:
            body['summary'] = title
        if description is not None:
            body['description'] = description
        if deadline:
            body['start'] = {'date': deadline}
            body['end'] = {'date': deadline}

        ext_update = {}
        if status:
            ext_update['status'] = status
        if priority:
            ext_update['priority'] = priority
        if tags is not None:
            ext_update['tags'] = json.dumps(tags)

        if ext_update:
            current_event = service.events().get(calendarId='primary', eventId=task_id).execute()
            current_ext = current_event.get('extendedProperties', {}).get('private', {})
            new_ext = {**current_ext, **ext_update}
            body['extendedProperties'] = {'private': new_ext}

        if not body:
            return False, "No updates provided"

        event = service.events().patch(
            calendarId='primary',
            eventId=task_id,
            body=body
        ).execute()

        return True, f"Task {task_id} updated"

    except ValueError as ve:
        return False, str(ve)
    except Exception as e:
        return False, f"Failed to update task: {str(e)}"

def mark_complete(
    task_id: str,
    uid: str = None
) -> Tuple[bool, str]:
    """Mark a task as complete by updating its status in Google Calendar."""
    return update_task(task_id, status='completed', uid=uid)

def delete_task(
    task_id: str,
    uid: str = None
) -> Tuple[bool, str]:
    """Delete a task from Google Calendar."""
    try:
        creds = get_google_creds(uid)
        service = build('calendar', 'v3', credentials=creds)

        service.events().delete(
            calendarId='primary',
            eventId=task_id
        ).execute()

        return True, f"Task {task_id} deleted"

    except ValueError as ve:
        return False, str(ve)
    except Exception as e:
        return False, f"Failed to delete task: {str(e)}"
    


if __name__ == "__main__":
    # Example usage
    uid = "user123"  # Replace with actual user ID
    success, message = create_task("Test Task", "This is a test task", "2024-12-31", "High", ["test", "demo"], uid)
    print(success, message)