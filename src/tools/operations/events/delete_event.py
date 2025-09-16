def delete_event(event_id: str) -> tuple[bool, str]:
    try:
        # Local import to avoid package resolution issues during startup
        from src.firebase_client import delete_document
        ok = delete_document("calendar_events", event_id)
        return (ok, f"Deleted event {event_id}" if ok else f"Failed to delete event {event_id}")
    except Exception as e:
        return False, str(e)