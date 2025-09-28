from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from firebase_client import db
from typing import Optional, List, Dict, Tuple
import json
import os
from dotenv import load_dotenv
from datetime import datetime

load_dotenv()

def get_google_creds(uid: str) -> Credentials:
    """Retrieve and refresh Google Calendar credentials for the given user ID."""
    if uid is None:
        raise ValueError("User ID (uid) is required to access Google credentials.")
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
    date: Optional[str] = None,
    start_time: Optional[str] = None,
    end_time: Optional[str] = None,
    priority: str = "Medium",
    reminder_minutes: Optional[int] = None,
    location: Optional[str] = None,
    attendees: Optional[List[str]] = None,
    tags: Optional[List[str]] = None,
    uid: str = None
) -> Tuple[bool, str]:
    """Create a new task as a Google Calendar event with enhanced parameters."""
    if uid is None:
        return False, "User ID (uid) is required to create a task."
    if not title or not date:
        return False, "Title and date are required for creating a task."
    try:
        creds = get_google_creds(uid)
        service = build('calendar', 'v3', credentials=creds)
        
        # Determine if all-day or timed event
        is_all_day = not (start_time and end_time)
        if is_all_day:
            start = {'date': date}
            end = {'date': date}
        else:
            start = {
                'dateTime': f"{date}T{start_time}:00",
                'timeZone': 'Asia/Kolkata'  # Or fetch from user profile/env
            }
            end = {
                'dateTime': f"{date}T{end_time}:00",
                'timeZone': 'Asia/Kolkata'
            }
        # Map priority to colorId (High: red=11, Medium: orange=6, Low: green=10)
        color_map = {"High": "11", "Medium": "6", "Low": "10"}
        color_id = color_map.get(priority, "6")  # Default to Medium
        
        event_body = {
            'summary': title,
            'description': description or '',
            'start': start,
            'end': end,
            'colorId': color_id,
            'extendedProperties': {
                'private': {
                    'type': 'task',
                    'status': 'needsAction',
                    'priority': priority,
                    'tags': json.dumps(tags or [])
                }
            }
        }
        
        if location:
            event_body['location'] = location
            
        if attendees:
            event_body['attendees'] = [{'email': email} for email in attendees]
            
        if reminder_minutes is not None:
            event_body['reminders'] = {
                'useDefault': False,
                'overrides': [{'method': 'popup', 'minutes': reminder_minutes}]
            }
        
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
    """Retrieve tasks from Google Calendar, optionally filtered by status, with enhanced fields."""
    if uid is None:
        return False, "User ID (uid) is required to read tasks."
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
        color_to_priority = {"11": "High", "6": "Medium", "10": "Low"}
        for event in items:
            ext = event.get('extendedProperties', {}).get('private', {})
            if ext.get('type') == 'task':
                if status is None or ext.get('status') == status:
                    start = event.get('start', {})
                    end = event.get('end', {})
                    date = start.get('date') or start.get('dateTime', '').split('T')[0]
                    start_time = start.get('dateTime', '').split('T')[1][:5] if 'dateTime' in start else None
                    end_time = end.get('dateTime', '').split('T')[1][:5] if 'dateTime' in end else None
                    reminder = event.get('reminders', {}).get('overrides', [{}])[0].get('minutes')
                    attendees = [a.get('email') for a in event.get('attendees', [])]
                    priority = ext.get('priority') or color_to_priority.get(event.get('colorId', '6'), "Medium")
                    task = {
                        'id': event['id'],
                        'title': event['summary'],
                        'description': event.get('description'),
                        'date': date,
                        'start_time': start_time,
                        'end_time': end_time,
                        'status': ext.get('status'),
                        'priority': priority,
                        'reminder_minutes': reminder,
                        'location': event.get('location'),
                        'attendees': attendees,
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
    date: Optional[str] = None,
    start_time: Optional[str] = None,
    end_time: Optional[str] = None,
    priority: Optional[str] = None,
    reminder_minutes: Optional[int] = None,
    location: Optional[str] = None,
    attendees: Optional[List[str]] = None,
    tags: Optional[List[str]] = None,
    uid: str = None
) -> Tuple[bool, str]:
    """Update an existing task in Google Calendar with enhanced parameters."""
    if uid is None:
        return False, "User ID (uid) is required to update a task."
    try:
        creds = get_google_creds(uid)
        service = build('calendar', 'v3', credentials=creds)
        current_event = service.events().get(calendarId='primary', eventId=task_id).execute()
        body = {}
        if title:
            body['summary'] = title
        if description is not None:
            body['description'] = description
        if location is not None:
            body['location'] = location
        if attendees is not None:
            body['attendees'] = [{'email': email} for email in attendees]
        if reminder_minutes is not None:
            body['reminders'] = {
                'useDefault': False,
                'overrides': [{'method': 'popup', 'minutes': reminder_minutes}]
            }
        # Handle date/time updates
        if date or start_time or end_time:
            current_start = current_event.get('start', {})
            current_end = current_event.get('end', {})
            new_date = date or current_start.get('date') or current_start.get('dateTime', '').split('T')[0]
            is_all_day = not (start_time and end_time)
            body['start'] = {'date': new_date} if is_all_day else {'dateTime': f"{new_date}T{start_time or '00:00'}:00"}
            body['end'] = {'date': new_date} if is_all_day else {'dateTime': f"{new_date}T{end_time or '23:59'}:00"}
        # Extended properties
        ext_update = {}
        if status:
            ext_update['status'] = status
        if priority:
            ext_update['priority'] = priority
            color_map = {"High": "11", "Medium": "6", "Low": "10"}
            body['colorId'] = color_map.get(priority, "6")
        if tags is not None:
            ext_update['tags'] = json.dumps(tags)
        if ext_update:
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
    if uid is None:
        return False, "User ID (uid) is required to mark a task as complete."
    return update_task(task_id, status='completed', uid=uid)

def delete_task(
    task_id: str,
    uid: str = None
) -> Tuple[bool, str]:
    """Delete a task from Google Calendar."""
    if uid is None:
        return False, "User ID (uid) is required to delete a task."
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
    # Example usage for testing
    uid = "tM0z46gheOTdll6nyyWamQBYrpL2"  # Replace with a test user ID (can be any string for testing, since db is skipped)
    
    # Test create_task - this will attempt to create a real task if creds are valid
    success, message = create_task(
        title="Test Task",
        description="This is a test task for standalone script",
        date="2025-12-27",  # Use YYYY-MM-DD format
        start_time="10:00",
        end_time="11:00",
        priority="High",
        tags=["test", "demo"],
        uid=uid
    )

    print("Create Task:", success, message)