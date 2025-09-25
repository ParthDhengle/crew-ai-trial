from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials
from firebase_client import get_user_profile
from datetime import datetime
from datetime import timedelta
import google.auth.transport.requests
def read_event(event_id: str = None, calendar_id: str = 'primary', time_min: str = None, time_max: str = None) -> tuple[bool, str]:
    """
    Read a Google Calendar event or list events.
    - If event_id: Get single event.
    - Else: List events between time_min/time_max (ISO strings).
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
            scopes=['https://www.googleapis.com/auth/calendar.events.readonly']
        )
        if creds.expired and creds.refresh_token:
            creds.refresh(google.auth.transport.requests.Request())

        service = build('calendar', 'v3', credentials=creds)

        if event_id:
            event = service.events().get(calendarId=calendar_id, eventId=event_id).execute()
            return True, f"✅ Event '{event['summary']}' (ID: {event_id}) from {event['start']['dateTime']} to {event['end']['dateTime']}."
        else:
            # List events
            time_min = time_min or datetime.now().isoformat() + 'Z'  # UTC now
            time_max = time_max or (datetime.now() + timedelta(days=30)).isoformat() + 'Z'
            events_result = service.events().list(
                calendarId=calendar_id, timeMin=time_min, timeMax=time_max, singleEvents=True, orderBy='startTime'
            ).execute()
            events = events_result.get('items', [])
            if not events:
                return True, "No events found in the specified time range."
            event_list = "\n".join([f"- '{e['summary']}': {e['start']['dateTime']} to {e['end']['dateTime']}" for e in events])
            return True, f"✅ Upcoming events in '{calendar_id}':\n{event_list}"
    except Exception as e:
        return False, f"❌ Failed to read events: {str(e)}."