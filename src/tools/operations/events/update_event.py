def update_event(event_id: str = None, **fields) -> tuple[bool, str]: 
    if not event_id:
        return False, "event_id required"
    # Local import to avoid package resolution issues during startup
    from src.firebase_client import update_document
    ok = update_document("calendar_events", event_id, fields)
    return (ok, f"Updated event {event_id}" if ok else f"Failed to update event {event_id}")