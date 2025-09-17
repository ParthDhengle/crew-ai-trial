import os
import sys
import json
from datetime import datetime
from crew import AiAgent
import traceback
from common_functions.Find_project_root import find_project_root
from utils.logger import setup_logger
from firebase_client import create_user, sign_in_with_email, get_user_profile, set_user_profile, verify_id_token
from firebase_admin import auth
from common_functions.User_preference import collect_preferences, parse_preferences, REQUIRED_PROFILE_KEYS


PROJECT_ROOT = find_project_root()
logger = setup_logger()

# Global for current authenticated UID (for CLI session)
current_uid = None

def display_welcome():
    message = "=" * 60 + "\n🤖 AI ASSISTANT - Firebase-Integrated CrewAI (CLI Mode)\n" + "=" * 60 + \
              "\nNow using Firestore for profiles, tasks, and memory!\n" + \
              "Use 'help' or 'h' for commands, 'quit' or 'q' to exit.\n" + "=" * 60
    print(message)
    logger.info("Displayed welcome message")

def display_help():
    message = "\nAvailable Commands:\n" + \
              "- help, h: Show this help message\n" + \
              "- quit, q: Exit the assistant\n" + \
              "- Any other input: Process as a query (e.g., 'List tasks', 'Create snapshot')\n" + \
              "\nExamples:\n" + \
              "- 'List files in /tmp' → Lists files using file.list operation\n" + \
              "- 'Create task Buy groceries' → Creates task in Firestore\n" + \
              "- 'Start focus session for 25 min' → Starts focus session"
    print(message)
    logger.info("Displayed help message")

def get_user_input(prompt="💬 What can I help you with? "):
    try:
        user_input = input(prompt).strip()
        logger.debug(f"Received CLI input: {user_input}")
        return user_input
    except KeyboardInterrupt:
        logger.info("CLI input interrupted by user")
        return "quit"

def authenticate_user(get_user_input=None):
    """Simple CLI auth flow: signup or login."""
    if get_user_input is None:
        get_user_input = input
    print("\n🔐 Authentication Required")
    choice = get_user_input("Sign up (s) or Login (l)? ").lower()
    email = get_user_input("Email: ")
    if choice == 's':
        password = get_user_input("Password: ")  # In prod, hash/secure this
        display_name = get_user_input("Display Name: ")
        try:
            uid = create_user(email, password, display_name)
            print(f"✅ Signed up! UID: {uid}")
        except ValueError as e:
            print(f"❌ Signup failed: {e}")
            return None
    else:  # login
        password = get_user_input("Password: ")
        try:
            uid = sign_in_with_email(email, password)
            print(f"✅ Logged in! UID: {uid}")
        except ValueError as e:
            print(f"❌ Login failed: {e}")
            return None
    return uid

def load_or_create_profile():
    """Load or create user profile in Firestore."""
    logger.info("Loading or creating user profile")
    profile = get_user_profile()
    if not profile:
        logger.warning("No profile found in Firestore. Setting up...")
        print("No profile found in Firestore. Setting up...")
        name = get_user_input("Your name: ")
        email = get_user_input("Your email: ")
        set_user_profile(current_uid, email, display_name=name)  # Use global current_uid
        profile = get_user_profile()
        logger.info("Profile created in Firestore")
        print("✅ Profile created in Firestore.")
    # ... (rest as before, collect_preferences)

    missing = [k for k in REQUIRED_PROFILE_KEYS if k not in profile or not profile[k]]
    if missing:
        logger.warning(f"Missing profile fields: {missing}. Collecting...")
        print(f"Missing profile fields: {missing}. Collecting...")
        collect_preferences(None, get_user_input)  # Uses Firestore
        profile = get_user_profile()
    logger.debug(f"User profile loaded: {json.dumps(profile, default=str)}")
    return profile

def validate_environment():
    """Check Firebase connectivity."""
    logger.info("Validating Firebase connectivity")
    try:
        _ = get_user_profile()
        logger.info("Firebase connected successfully")
        print("✅ Firebase connected.")
        return True
    except Exception as e:
        logger.error(f"Firebase error: {str(e)}")
        print(f"❌ Firebase error: {str(e)}")
        return False

def run_single_query(user_query=None):
    global current_uid  # Access global UID
    logger.info(f"Processing single query: {user_query}")
    if not validate_environment():
        logger.error("Environment validation failed")
        return False
    # Auth only if not already authenticated
    if current_uid is None:
        uid = authenticate_user(get_user_input)
        if not uid:
            print("❌ Auth failed. Exiting.")
            return False
        current_uid = uid  # Set global for session
    profile = load_or_create_profile()
    if not user_query:
        user_query = get_user_input()
    if user_query.lower() in ["quit", "exit", "q"]:
        logger.info("User requested to quit")
        current_uid = None  # Reset on exit
        return False
    if user_query.lower() in ["help", "h"]:
        display_help()
        return True
    if not user_query:
        logger.debug("Empty query provided")
        return True
    print(f"\n🔍 Processing: '{user_query}' (Profile: {profile.get('Name', 'Unknown')})")
    logger.info(f"Processing query: {user_query} for user {profile.get('Name', 'Unknown')}")
    try:
        crew_instance = AiAgent()
        final_response = crew_instance.run_workflow(user_query)
        print(final_response)
        logger.debug(f"Query response: {final_response}")
        return True
    except Exception as e:
        logger.error(f"Error processing query '{user_query}': {str(e)}")
        print(f"❌ Error: {e}")
        traceback.print_exc()
        return True

def run_interactive():
    global current_uid  # Ensure global access
    display_welcome()
    try:
        while True:
            if not run_single_query():
                break
    except KeyboardInterrupt:
        logger.info("Interactive mode terminated by user")
        print("\n👋 Goodbye!")
        current_uid = None  # Reset on exit

def run():
    logger.info("Starting AI Assistant (CLI)")
    if len(sys.argv) > 1:
        query = " ".join(sys.argv[1:]).strip('"')
        logger.info(f"Running single query mode with: {query}")
        run_single_query(query)
    else:
        logger.info("Running in interactive CLI mode")
        run_interactive()

if __name__ == "__main__":
    run()