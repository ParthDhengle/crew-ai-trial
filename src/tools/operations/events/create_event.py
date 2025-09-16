from ....firebase_client import add_document  # For future; placeholder now

def create_event(calendar_id: str, title: str, start: str, end: str, attendees: list = None, location: str = None) -> tuple[bool, str]:
    # Placeholder: In prod, integrate Google Calendar API via integrations in profile
    data = {  # Mock for Firestore if needed
        "calendar_id": calendar_id, "title": title, "start": start, "end": end,
        "attendees": attendees or [], "location": location or ""
    }
    doc_id = add_document("calendar_events", data)  # Store in Firestore
    return True, f"Created calendar event '{title}' (ID: {doc_id}) from {start} to {end} in calendar '{calendar_id}'."