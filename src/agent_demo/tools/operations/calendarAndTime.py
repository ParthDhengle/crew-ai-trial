import datetime
import os.path
from zoneinfo import ZoneInfo
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

SCOPES = ['https://www.googleapis.com/auth/calendar']
DEFAULT_TIMEZONE = 'UTC'

def get_service():
    """
    Authenticates and returns the Google Calendar service.
    """
    creds = None
    if os.path.exists('token.json'):
        creds = Credentials.from_authorized_user_file('token.json', SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file('client_secret.json', SCOPES)
            creds = flow.run_local_server(port=0)
        with open('token.json', 'w') as token:
            token.write(creds.to_json())
    return build('calendar', 'v3', credentials=creds)

service = get_service()

def create_event(title, date, time, location):
    """
    Creates a calendar event.
    :param title: str - The title of the event.
    :param date: str - The date in 'YYYY-MM-DD' format.
    :param time: str - The time in 'HH:MM' format.
    :param location: str - The location of the event.
    :return: str - Confirmation message with event ID.
    """
    try:
        start_dt = datetime.datetime.fromisoformat(f"{date}T{time}:00")
        end_dt = start_dt + datetime.timedelta(hours=1)  # Assume 1-hour duration
        event = {
            'summary': title,
            'location': location,
            'start': {
                'dateTime': start_dt.isoformat(),
                'timeZone': DEFAULT_TIMEZONE,
            },
            'end': {
                'dateTime': end_dt.isoformat(),
                'timeZone': DEFAULT_TIMEZONE,
            },
        }
        created_event = service.events().insert(calendarId='primary', body=event).execute()
        return f"Event created with ID {created_event['id']}"
    except HttpError as e:
        return f"Error creating event: {e}"
    except ValueError:
        return "Invalid date or time format."
def find_event_id(title, date):
    """
    Finds the event ID for a given title and date.
    :param title: str - Event title to search for (case-insensitive).
    :param date: str - Event date in 'YYYY-MM-DD' format.
    :return: str or None - Event ID if found, else None.
    """
    try:
        start_dt = datetime.datetime.fromisoformat(date + 'T00:00:00')
        end_dt = datetime.datetime.fromisoformat(date + 'T23:59:59')
        time_min = start_dt.isoformat() + 'Z'
        time_max = end_dt.isoformat() + 'Z'

        events_result = service.events().list(
            calendarId='primary',
            timeMin=time_min,
            timeMax=time_max,
            singleEvents=True,
            orderBy='startTime'
        ).execute()

        events = events_result.get('items', [])
        for e in events:
            if title.lower() in e.get('summary', '').lower():
                return e['id']  # Return the first match
        return None
    except HttpError as e:
        return f"Error searching event: {e}"

def list_events(date_range):
    """
    Lists events in the given date range.
    :param date_range: str - The date range in 'YYYY-MM-DD to YYYY-MM-DD' format.
    :return: list - List of matching event dictionaries.
    """
    try:
        start_str, end_str = date_range.split(' to ')
        start_dt = datetime.datetime.fromisoformat(start_str.strip() + 'T00:00:00')
        end_dt = datetime.datetime.fromisoformat(end_str.strip() + 'T23:59:59')
        time_min = start_dt.isoformat() + 'Z'
        time_max = end_dt.isoformat() + 'Z'
        events_result = service.events().list(
            calendarId='primary',
            timeMin=time_min,
            timeMax=time_max,
            singleEvents=True,
            orderBy='startTime'
        ).execute()
        events = events_result.get('items', [])
        return [{
            'id': e['id'],
            'title': e.get('summary', ''),
            'date': e['start'].get('dateTime', e['start'].get('date', '')).split('T')[0],
            'time': e['start'].get('dateTime', '').split('T')[1][:5] if 'T' in e['start'].get('dateTime', '') else '',
            'location': e.get('location', '')
        } for e in events]
    except HttpError as e:
        return f"Error listing events: {e}"
    except ValueError:
        return "Invalid date range format. Use 'YYYY-MM-DD to YYYY-MM-DD'."

def delete_event(title, date):
    event_id=find_event_id(title, date)
    if not event_id:
        return "Event not found."
    """
    Deletes a specific calendar event.
    :param event_id: str - The ID of the event to delete.
    :return: str - Confirmation message.
    """
    try:
        service.events().delete(calendarId='primary', eventId=event_id).execute()
        return "Event deleted successfully."
    except HttpError as e:
        if e.status_code == 410 or e.status_code == 404:  # 410 for gone, 404 not found
            return "Event not found."
        return f"Error deleting event: {e}"

def get_time(location):
    """
    Returns current time for a location.
    :param location: str - The timezone string (e.g., 'America/New_York').
    :return: str - Current time in the specified timezone.
    """
    try:
        tz = ZoneInfo(location)
        now = datetime.datetime.now(tz)
        return now.strftime('%Y-%m-%d %H:%M:%S %Z')
    except Exception as e:
        return f"Error getting time for location '{location}': {str(e)}"

def set_reminder(message, datetime_str):
    """
    Sets a reminder by creating a short event with a popup reminder.
    :param message: str - The reminder message.
    :param datetime_str: str - The datetime in 'YYYY-MM-DDTHH:MM:SS' format.
    :return: str - Confirmation message.
    """
    try:
        dt = datetime.datetime.fromisoformat(datetime_str)
        end_dt = dt + datetime.timedelta(minutes=1)  # Short duration for reminder event
        event = {
            'summary': f"Reminder: {message}",
            'start': {
                'dateTime': dt.isoformat(),
                'timeZone': DEFAULT_TIMEZONE,
            },
            'end': {
                'dateTime': end_dt.isoformat(),
                'timeZone': DEFAULT_TIMEZONE,
            },
            'reminders': {
                'useDefault': False,
                'overrides': [
                    {'method': 'popup', 'minutes': 0},
                ],
            },
        }
        service.events().insert(calendarId='primary', body=event).execute()
        return "Reminder set successfully."
    except HttpError as e:
        return f"Error setting reminder: {e}"
    except ValueError:
        return "Invalid datetime format. Use 'YYYY-MM-DDTHH:MM:SS'."

def update_event(title, date, updates):
    event_id=find_event_id(title, date)
    if not event_id:    
        return "Event not found."
    """
    Updates an existing calendar event.
    :param event_id: str - The ID of the event to update.
    :param updates: dict - Dictionary of fields to update (e.g., {'title': 'New Title', 'location': 'New Location', 'date': 'YYYY-MM-DD', 'time': 'HH:MM'}).
    :return: str - Confirmation message.
    """
    try:
        event = service.events().get(calendarId='primary', eventId=event_id).execute()
        if 'title' in updates:
            event['summary'] = updates['title']
        if 'location' in updates:
            event['location'] = updates['location']
        if 'date' in updates or 'time' in updates:
            start_str = event['start'].get('dateTime', event['start'].get('date'))
            end_str = event['end'].get('dateTime', event['end'].get('date'))
            start_dt = datetime.datetime.fromisoformat(start_str.rstrip('Z'))
            end_dt = datetime.datetime.fromisoformat(end_str.rstrip('Z'))
            duration = end_dt - start_dt
            if 'date' in updates:
                new_date = datetime.date.fromisoformat(updates['date'])
                start_dt = start_dt.replace(year=new_date.year, month=new_date.month, day=new_date.day)
            if 'time' in updates:
                new_time = datetime.time.fromisoformat(updates['time'])
                start_dt = start_dt.replace(hour=new_time.hour, minute=new_time.minute)
            end_dt = start_dt + duration
            event['start']['dateTime'] = start_dt.isoformat()
            event['end']['dateTime'] = end_dt.isoformat()
        service.events().update(calendarId='primary', eventId=event_id, body=event).execute()
        return "Event updated successfully."
    except HttpError as e:
        if e.status_code == 404:
            return "Event not found."
        return f"Error updating event: {e}"
    except ValueError:
        return "Invalid update format."
print(list_events("2025-08-26 to 2025-09-30"))