# calendar_and_time.py
import os
import re
import json
import datetime
import pytz
from typing import Optional, Dict, List, Any

# Google Calendar API imports
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build

# Try import Gemini client (new genai sdk) or legacy SDK.
try:
    from google import genai as genai_sdk  # preferred new SDK (google-genai)
    GENAI_SDK = "google"
except Exception:
    try:
        import google.generativeai as genai_sdk  # legacy SDK
        GENAI_SDK = "legacy"
    except Exception:
        genai_sdk = None
        GENAI_SDK = None

# Optional fallback parser
try:
    import dateparser
except Exception:
    dateparser = None

# Scheduler for local reminders
from apscheduler.schedulers.background import BackgroundScheduler
scheduler = BackgroundScheduler()
scheduler.start()

SCOPES = ["https://www.googleapis.com/auth/calendar"]
TIMEZONE = os.getenv("CALENDAR_TIMEZONE", "Asia/Kolkata")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-1.5")


def get_calendar_service():
    creds = None
    if os.path.exists("token.json"):
        creds = Credentials.from_authorized_user_file("token.json", SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            if not os.path.exists("credentials.json"):
                raise FileNotFoundError("credentials.json not found. Follow setup steps to get Google OAuth credentials.")
            flow = InstalledAppFlow.from_client_secrets_file("credentials.json", SCOPES)
            creds = flow.run_local_server(port=0)
        with open("token.json", "w") as f:
            f.write(creds.to_json())
    return build("calendar", "v3", credentials=creds)


# ---------------- Gemini helper ----------------
def _call_gemini(prompt: str, model: Optional[str] = None) -> str:
    """
    Call Gemini using whichever SDK is installed. Returns raw text.
    """
    model = model or GEMINI_MODEL
    if genai_sdk is None:
        raise RuntimeError("Gemini SDK not installed. Install google-genai or google-generativeai and set GEMINI_API_KEY / ADC.")

    # New SDK (google.genai)
    if GENAI_SDK == "google":
        client = genai_sdk.Client()
        resp = client.models.generate_content(model=model, contents=[prompt])
        raw = getattr(resp, "text", None)
        if raw:
            return raw
        # fallback attempts
        try:
            if hasattr(resp, "output") and resp.output:
                return str(resp.output)
        except Exception:
            pass
        return str(resp)

    # Legacy SDK (google.generativeai)
    elif GENAI_SDK == "legacy":
        genai_sdk.configure(api_key=os.getenv("GEMINI_API_KEY"))
        model_obj = genai_sdk.GenerativeModel(model)
        resp = model_obj.generate_content(prompt)
        raw = getattr(resp, "text", None) or str(resp)
        return raw

    else:
        raise RuntimeError("No supported Gemini SDK found.")


def gemini_extract_fields(user_text: str, fields: List[str]) -> Dict[str, Optional[str]]:
    today = datetime.datetime.now(pytz.timezone(TIMEZONE)).date().isoformat()
    fields_list = ", ".join(fields)
    prompt = f"""
Return ONLY a JSON object. Do not write any text before or after.

Today is {today} (timezone {TIMEZONE}).
Extract the following fields from the user's text: {fields_list}.
Output JSON with exactly these keys.

Rules:
- "date" → YYYY-MM-DD
- "time" → HH:MM (24-hour)
- "title", "location", "message" → plain strings or null
- If user says "tomorrow" or "25 September", resolve it to correct absolute date.
- If something is missing, set it to null.

User text: "{user_text}"
"""

    try:
        raw = _call_gemini(prompt)
    except Exception:
        return _fallback_extract(user_text, fields)

    # Extract JSON more reliably
    m = re.search(r"\{.*\}", raw, re.S)
    if not m:
        return _fallback_extract(user_text, fields)

    try:
        parsed = json.loads(m.group())
    except Exception:
        return _fallback_extract(user_text, fields)

    return {f: parsed.get(f) for f in fields}


def _fallback_extract(user_text: str, fields: List[str]) -> Dict[str, Optional[str]]:
    """
    Simple heuristic fallback: dateparser for dates/times if available,
    and regex heuristics for location/title.
    """
    result = {f: None for f in fields}
    if dateparser:
        dt = dateparser.parse(user_text, settings={'PREFER_DATES_FROM': 'future'})
        if dt:
            if 'date' in fields:
                result['date'] = dt.date().isoformat()
            if 'time' in fields:
                result['time'] = dt.time().strftime('%H:%M')
    # heuristics for location
    m = re.search(r'\b(?:at|in)\s+([A-Za-z0-9 \-_,]+)', user_text, re.I)
    if m and 'location' in fields:
        result['location'] = m.group(1).strip()
    # title heuristic: remove date/time phrases
    if 'title' in fields:
        title_candidate = re.sub(r'\b(on|at|in|tomorrow|today|next)\b.*', '', user_text, flags=re.I).strip()
        if title_candidate:
            result['title'] = title_candidate[:120]
    return result


# ---------------- Interactive ask & fill ----------------
def _ask_user_for_missing(fields: List[str]) -> Dict[str, Optional[str]]:
    """
    Ask the user (via input()) for a natural-language response containing the missing fields.
    Then call Gemini to extract them. Returns dict.
    """
    instruction = "\n".join([
        "I need the following information:",
        f"  - {', '.join(fields)}",
        "Please reply naturally in one sentence (example: 'Team sync on Friday at 5 pm at Office')."
    ])
    user_reply = input(instruction + "\nYour reply: ")
    extracted = gemini_extract_fields(user_reply, fields)
    tries = 0
    while any(extracted[f] is None for f in fields) and tries < 2:
        missing = [f for f in fields if extracted[f] is None]
        print("I couldn't extract:", ", ".join(missing) + ". Please clarify.")
        user_reply = input("Clarify (natural language): ")
        more = gemini_extract_fields(user_reply, missing)
        for k, v in more.items():
            if v:
                extracted[k] = v
        tries += 1
    return extracted


# ---------------- Helpers for datetime ----------------
def _to_kolkata_rfc3339(date_str: str, time_str: Optional[str] = None) -> str:
    tz = pytz.timezone(TIMEZONE)
    if time_str:
        dt = datetime.datetime.fromisoformat(f"{date_str}T{time_str}")
    else:
        dt = datetime.datetime.fromisoformat(f"{date_str}T00:00:00")
    dt = tz.localize(dt) if dt.tzinfo is None else dt.astimezone(tz)
    return dt.isoformat()


def _parse_date_time_or_raise(date_s: str, time_s: str) -> datetime.datetime:
    try:
        return datetime.datetime.fromisoformat(f"{date_s}T{time_s}")
    except Exception:
        if dateparser:
            dt = dateparser.parse(f"{date_s} {time_s}", settings={'PREFER_DATES_FROM': 'future'})
            if dt:
                return dt
        raise ValueError(f"Unable to parse date/time: {date_s} {time_s}")


# ---------------- Calendar operations ----------------
def create_event(title: Optional[str] = None, date: Optional[str] = None,
                 time: Optional[str] = None, location: Optional[str] = None):
    missing = [k for k, v in [('title', title), ('date', date), ('time', time), ('location', location)] if not v]
    if missing:
        extracted = _ask_user_for_missing(missing)
        title = title or extracted.get('title')
        date = date or extracted.get('date')
        time = time or extracted.get('time')
        location = location or extracted.get('location')

    if not all([title, date, time, location]):
        return (False, "Missing event details after extraction.")

    try:
        start_iso = _to_kolkata_rfc3339(date, time)
        dt_obj = _parse_date_time_or_raise(date, time)
        end_dt = dt_obj + datetime.timedelta(hours=1)
        end_iso = pytz.timezone(TIMEZONE).localize(end_dt).isoformat() if end_dt.tzinfo is None else end_dt.astimezone(pytz.timezone(TIMEZONE)).isoformat()

        service = get_calendar_service()
        event = {
            'summary': title,
            'location': location,
            'start': {'dateTime': start_iso, 'timeZone': TIMEZONE},
            'end': {'dateTime': end_iso, 'timeZone': TIMEZONE},
        }
        created = service.events().insert(calendarId='primary', body=event).execute()
        return (True, f"Event created: {created.get('htmlLink')}")
    except Exception as e:
        return (False, str(e))


def list_events(max_results: int = 10, time_min: Optional[str] = None):
    try:
        service = get_calendar_service()
        if time_min is None:
            time_min = datetime.datetime.utcnow().isoformat() + 'Z'
        events_result = service.events().list(calendarId='primary', timeMin=time_min,
                                              maxResults=max_results, singleEvents=True, orderBy='startTime').execute()
        items = events_result.get('items', [])
        if not items:
            return (True, 'No upcoming events found.')
        formatted = '\n'.join([f"{it['start'].get('dateTime', it['start'].get('date'))}: {it.get('summary')} (id={it.get('id')})" for it in items])
        return (True, formatted)
    except Exception as e:
        return (False, str(e))


def _find_events_by_criteria(title: Optional[str] = None, date: Optional[str] = None, time: Optional[str] = None) -> List[Dict[str, Any]]:
    service = get_calendar_service()
    now = datetime.datetime.utcnow().isoformat() + 'Z'
    time_min = now
    time_max = None
    if date:
        start_day = datetime.datetime.fromisoformat(f"{date}T00:00:00")
        end_day = start_day + datetime.timedelta(days=1)
        time_min = pytz.timezone(TIMEZONE).localize(start_day).isoformat()
        time_max = pytz.timezone(TIMEZONE).localize(end_day).isoformat()

    events_result = service.events().list(calendarId='primary', timeMin=time_min,
                                          timeMax=time_max, q=title, singleEvents=True, orderBy='startTime').execute()
    return events_result.get('items', [])


def delete_event(event_id: Optional[str] = None):
    if not event_id:
        extracted = _ask_user_for_missing(['title', 'date', 'time'])
        candidates = _find_events_by_criteria(title=extracted.get('title'), date=extracted.get('date'), time=extracted.get('time'))
        if not candidates:
            return (False, 'No event matching that description found.')
        event_id = candidates[0].get('id')

    try:
        service = get_calendar_service()
        service.events().delete(calendarId='primary', eventId=event_id).execute()
        return (True, f"Deleted event {event_id}")
    except Exception as e:
        return (False, str(e))


def update_event(event_id: Optional[str] = None, updates: Optional[Dict[str, str]] = None):
    if not event_id:
        print('Which event would you like to update? Describe it naturally.')
        extracted = _ask_user_for_missing(['title', 'date', 'time'])
        candidates = _find_events_by_criteria(title=extracted.get('title'), date=extracted.get('date'), time=extracted.get('time'))
        if not candidates:
            return (False, 'No event found to update.')
        event_id = candidates[0].get('id')

    if not updates:
        print('What do you want to update? (You can say: change time to 6 pm, move to Monday, change location to Office)')
        user_text = input('Update: ')
        updates = gemini_extract_fields(user_text, ['title', 'date', 'time', 'location'])

    try:
        service = get_calendar_service()
        event = service.events().get(calendarId='primary', eventId=event_id).execute()
        if updates.get('title'):
            event['summary'] = updates['title']
        if updates.get('location'):
            event['location'] = updates['location']
        if updates.get('date') or updates.get('time'):
            new_date = updates.get('date') or event['start'].get('dateTime', '')[:10]
            new_time = updates.get('time') or event['start'].get('dateTime', '')[11:16]
            start_iso = _to_kolkata_rfc3339(new_date, new_time)
            dt_obj = _parse_date_time_or_raise(new_date, new_time)
            end_dt = dt_obj + datetime.timedelta(hours=1)
            end_iso = pytz.timezone(TIMEZONE).localize(end_dt).isoformat() if end_dt.tzinfo is None else end_dt.astimezone(pytz.timezone(TIMEZONE)).isoformat()
            event['start'] = {'dateTime': start_iso, 'timeZone': TIMEZONE}
            event['end'] = {'dateTime': end_iso, 'timeZone': TIMEZONE}

        updated = service.events().update(calendarId='primary', eventId=event_id, body=event).execute()
        return (True, f"Updated event: {updated.get('htmlLink')}")
    except Exception as e:
        return (False, str(e))


def get_time(location: Optional[str] = None):
    if not location:
        location = input('Enter timezone name (e.g., Asia/Kolkata) or "local": ').strip() or 'local'
    try:
        if location.lower() == 'local':
            current_time = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        else:
            tz = pytz.timezone(location)
            current_time = datetime.datetime.now(tz).strftime('%Y-%m-%d %H:%M:%S')
        return (True, f"Current time ({location}): {current_time}")
    except Exception as e:
        return (False, str(e))


def set_reminder(message: Optional[str] = None, remind_time: Optional[str] = None):
    missing = [k for k, v in [('message', message), ('remind_time', remind_time)] if not v]
    if missing:
        extracted = _ask_user_for_missing(missing)
        message = message or extracted.get('message') or extracted.get('title') or 'Reminder'
        if extracted.get('date') and extracted.get('time'):
            remind_time = f"{extracted.get('date')} {extracted.get('time')}:00"
        else:
            remind_time = remind_time or (extracted.get('date') or extracted.get('time'))

    if not message or not remind_time:
        return (False, 'Missing reminder details.')

    try:
        dt = datetime.datetime.fromisoformat(remind_time) if 'T' in remind_time else datetime.datetime.strptime(remind_time, '%Y-%m-%d %H:%M:%S')
    except Exception:
        if dateparser:
            dt = dateparser.parse(remind_time, settings={'PREFER_DATES_FROM': 'future'})
        else:
            return (False, 'Could not parse reminder time.')
    if not dt:
        return (False, 'Could not parse reminder time.')

    def _job():
        print(f"🔔 Reminder: {message}")

    scheduler.add_job(_job, 'date', run_date=dt)
    return (True, f"Reminder set for '{message}' at {dt}")


# ---------------- Demo ---------------
if __name__ == '__main__':
    create_event(title='New Meeting')
