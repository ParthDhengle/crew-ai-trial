import os
import sys
import json
import warnings
from datetime import datetime
from crew import AiAgent
import traceback
from pydantic import __version__ as pydantic_version
from common_functions.Find_project_root import find_project_root
from firebase_client import get_user_profile, set_user_profile
from common_functions.User_preference import collect_preferences

PROJECT_ROOT = find_project_root()
if pydantic_version.startswith("2"):
    from pydantic import PydanticDeprecatedSince20
    warnings.filterwarnings("ignore", category=PydanticDeprecatedSince20)

REQUIRED_PROFILE_KEYS = [
    "Name", "Role", "Location", "Productive Time", "Reminder Type",
    "Top Task Type", "Missed Task Handling", "Top Motivation",
    "AI Tone", "Break Reminder", "Mood Check", "Current Focus"
]

def display_welcome():
    print("=" * 60)
    print("🤖 AI ASSISTANT - Firebase-Integrated CrewAI")
    print("=" * 60)
    print("Now using Firestore for profiles, tasks, and memory!")
    print("Use 'help' or 'h' for commands, 'quit' or 'q' to exit.")
    print("=" * 60)

def display_help():
    print("\nAvailable Commands:")
    print("- help, h: Show this help message")
    print("- quit, q: Exit the assistant")
    print("- Any other input: Process as a query (e.g., 'List tasks', 'Create snapshot')")
    print("\nExamples:")
    print("- 'List files in /tmp' → Lists files using file.list operation")
    print("- 'Create task Buy groceries' → Creates task in Firestore")
    print("- 'Start focus session for 25 min' → Starts focus session")

def get_user_input(prompt="💬 What can I help you with? "):
    try:
        return input(prompt).strip()
    except KeyboardInterrupt:
        return "quit"

def load_or_create_profile():
    """Load or create user profile in Firestore."""
    profile = get_user_profile()
    if not profile:
        print("No profile found in Firestore. Setting up...")
        name = input("Your name: ")
        email = input("Your email: ")
        set_user_profile(name, email)
        profile = get_user_profile()
        print("✅ Profile created in Firestore.")
    missing = [k for k in REQUIRED_PROFILE_KEYS if k not in profile or not profile[k]]
    if missing:
        print(f"Missing profile fields: {missing}. Collecting...")
        collect_preferences(None, get_user_input)  # Uses Firestore
        profile = get_user_profile()
    return profile

def validate_environment():
    """Check Firebase connectivity."""
    try:
        _ = get_user_profile()
        print("✅ Firebase connected.")
        return True
    except Exception as e:
        print(f"❌ Firebase error: {e}")
        return False

def run_single_query(user_query=None):
    if not validate_environment():
        return False
    profile = load_or_create_profile()
    if not user_query:
        user_query = get_user_input()
    if user_query.lower() in ["quit", "exit", "q"]:
        return False
    if user_query.lower() in ["help", "h"]:
        display_help()
        return True
    if not user_query:
        return True
    print(f"\n🔍 Processing: '{user_query}' (Profile: {profile.get('Name', 'Unknown')})")
    try:
        crew_instance = AiAgent()
        final_response = crew_instance.run_workflow(user_query)
        print(final_response)
        return True
    except Exception as e:
        print(f"❌ Error: {e}")
        traceback.print_exc()
        return True

def run_interactive():
    display_welcome()
    try:
        while True:
            if not run_single_query():
                break
    except KeyboardInterrupt:
        print("\n👋 Goodbye!")

def run():
    if len(sys.argv) > 1:
        query = " ".join(sys.argv[1:]).strip('"')
        run_single_query(query)
    else:
        run_interactive()

def train():
    # Unchanged
    pass

def replay():
    # Unchanged
    pass

def test():
    # Unchanged
    pass

if __name__ == "__main__":
    run()