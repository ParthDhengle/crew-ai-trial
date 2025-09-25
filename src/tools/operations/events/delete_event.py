from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials
from firebase_client import get_user_profile
import google.auth.transport.requests
def delete_event(event_id: str, calendar_id: str = 'primary') -> tuple[bool, str]:
    """
    Delete a Google Calendar event by ID.
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
        service.events().delete(calendarId=calendar_id, eventId=event_id).execute()

        # Optional: Delete from local Firestore cache
        from firebase_client import delete_document
        delete_document("calendar_events", event_id)

        return True, f"✅ Deleted Google Calendar event (ID: {event_id}) from '{calendar_id}'."
    except Exception as e:
        return False, f"❌ Failed to delete event: {str(e)}."