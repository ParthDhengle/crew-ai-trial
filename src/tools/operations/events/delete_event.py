from ....firebase_client import delete_document

def delete_event(event_id: str) -> tuple[bool, str]:
    try:
        ok = delete_document("calendar_events", event_id)
        return (ok, f"Deleted event {event_id}" if ok else f"Failed to delete event {event_id}")
    except Exception as e:
        return False, str(e)
def delete_event(event_id: str = None) -> tuple[bool, str]: 
    return True, f"Placeholder: Delete event(s): [mock]."