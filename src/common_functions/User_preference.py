import os
import json
import warnings
from firebase_client import get_user_profile, update_user_profile
REQUIRED_PROFILE_KEYS = [
    "Name",
    "Role",
    "Location",
    "Productive Time",
    "Reminder Type",
    "Top Task Type",
    "Missed Task Handling",
    "Top Motivation",
    "AI Tone",
    "Break Reminder",
    "Mood Check",
    "Current Focus"
]
def parse_preferences(prefs_path: str = None) -> dict:
    """Load profile from Firestore (auth-aware)."""
    from firebase_client import get_user_profile  # Ensure import
    return get_user_profile()

def collect_preferences(prefs_path: str = None, get_user_input=None):
    """Collect preferences and save to Firestore."""
    if get_user_input is None:
        get_user_input = input
    print("\n🛠️ Personalizing! (Saving to Firestore)")
    pref_definitions = {
        "Name": None,
        "Role": ["Student", "Professional (Engineer/Developer)", "Creative/Designer", "Manager/Entrepreneur", "Other"],
        "Location": None,
        "Productive Time": ["Morning", "Afternoon", "Evening", "Night"],
        "Reminder Type": ["Email", "Push Notification", "None"],
        "Top Task Type": ["Work", "Study", "Personal", "Health", "Other"],
        "Missed Task Handling": ["Reschedule Automatically", "Mark as Overdue", "Delete"],
        "Top Motivation": ["Career Growth", "Personal Development", "Work-Life Balance", "Creativity", "Health"],
        "AI Tone": ["Friendly", "Professional", "Casual", "Motivational"],
        "Break Reminder": ["Every 25 minutes", "Every 1 hour", "Every 2 hours", "None"],
        "Mood Check": ["Daily", "Weekly", "None"],
        "Current Focus": ["Finish studies", "Grow career skills", "Build side projects", "Explore & learn", "Health & balance"]
    }
    existing_prefs = parse_preferences()
    if all(key in existing_prefs and existing_prefs[key] for key in pref_definitions):  # Check if complete
        print("\n✅ Preferences already complete in Firestore.")
        return
    updated_prefs = existing_prefs.copy()
    for key, options in pref_definitions.items():
        if key not in existing_prefs or not existing_prefs[key]:
            if options:
                print(f"\n{key}:")
                for i, option in enumerate(options, 1):
                    print(f"{i}. {option}")
                choice = get_user_input(f"Select {key} (1-{len(options)}): ")
                try:
                    value = options[int(choice) - 1]
                except (ValueError, IndexError):
                    value = options[0] if options else choice
            else:
                value = get_user_input(f"{key}: ")
            updated_prefs[key] = value
    if updated_prefs != existing_prefs:
        from firebase_client import update_user_profile
        update_user_profile(updated_prefs)
        print("\n✅ Preferences updated in Firestore!")
    else:
        print("\n✅ Preferences up to date.")