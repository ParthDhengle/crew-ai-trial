def read_event(event_id: str = None) -> tuple[bool, str]: 
    try:
        # Local import to avoid package resolution issues during startup
        from src.firebase_client import query_collection, get_document
        if event_id:
            doc = get_document("calendar_events", event_id)
            return True, str(doc)
        docs = query_collection("calendar_events")
        return True, str(docs)
    except Exception as e:
        return False, str(e)