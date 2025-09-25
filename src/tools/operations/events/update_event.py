from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials
from firebase_client import get_user_profile
from datetime import datetime
import google.auth.transport.requests
def update_event(event_id: str, title: str = None, start: str = None, end: str = None, attendees: list = None, location: str = None, calendar_id: str = 'primary') -> tuple[bool, str]:
    """
    Update a Google Calendar event.
    """
    try:
        profile = get_user_profile()
        tokens = profile.get('integrations', {}).get('google_calendar', {}).get('tokens', {})
        if not tokens or 'access_token' not in tokens:
            return False, "Google Calendar integration not set up."

        creds = Credentials(
            token=tokens.get('access_token'),
            refresh_token=tokens.get('refresh_token'),
            token_uri=tokens.get('token_uri', 'https://oauth2.googleapis.com/token'),
            client_id=tokens.get('client_id'),
            client_secret=tokens.get('client_secret'),
            scopes=['https://www.googleapis.com/auth/calendar.events']
        )
        if creds.expired and creds.refresh_token:
            creds.refresh(google.auth.transport.requests.Request())

        service = build('calendar', 'v3', credentials=creds)

        # Get current event
        current_event = service.events().get(calendarId=calendar_id, eventId=event_id).execute()

        # Update fields
        if title:
            current_event['summary'] = title
        if start:
            current_event['start']['dateTime'] = start
        if end:
            current_event['end']['dateTime'] = end
        if location:
            current_event['location'] = location
        if attendees:
            current_event['attendees'] = [{'email': email} for email in attendees]

        updated_event = service.events().update(calendarId=calendar_id, eventId=event_id, body=current_event).execute()

        # Optional: Update local Firestore cache
        from firebase_client import update_document
        local_data = {
            'title': updated_event['summary'],
            'start': updated_event['start']['dateTime'],
            'end': updated_event['end']['dateTime'],
            'updated_at': datetime.now().isoformat()
        }
        update_document("calendar_events", event_id, local_data)

        return True, f"✅ Updated Google Calendar event '{updated_event['summary']}' (ID: {event_id})."
    except Exception as e:
        return False, f"❌ Failed to update event: {str(e)}."