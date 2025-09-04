import os
import sys
from datetime import datetime
from crew import AiAgent
import traceback
import warnings
from pydantic import __version__ as pydantic_version

# Correct PROJECT_ROOT: From src/main.py, dirname=src, '..' gets to project root
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))

if pydantic_version.startswith('2'):  # Only apply if Pydantic v2
    from pydantic import PydanticDeprecatedSince20
    warnings.filterwarnings("ignore", category=PydanticDeprecatedSince20)

def display_welcome():
    """Display welcome message and instructions."""
    print("=" * 60)
    print("🤖 AI ASSISTANT - CrewAI Operation Executor")
    print("=" * 60)
    print("I can help you with various tasks including:")
    print("• Communication (email, SMS, calls)")
    print("• File management (create, read, update, delete)")
    print("• Web searches and weather")
    print("• Calendar and task management")
    print("• Calculations and utilities")
    print("• System operations and more!")
    print()
    print("Type 'help' for more info, 'quit' to exit")
    print("=" * 60)
    print()

def display_help():
    """Display help information."""
    print("\n📖 HELP - Example Commands:")
    print("-" * 40)
    print("• 'Send an email to john@example.com about the meeting'")
    print("• 'Create a file called notes.txt with my ideas'")
    print("• 'Calculate 15% tip on $85'")
    print("• 'Get the weather for San Francisco'")
    print("• 'Generate a strong password'")
    print("• 'Take a screenshot'")
    print("• 'Create a task to review the report by Friday'")
    print("• 'Set a reminder for team meeting at 2 PM tomorrow'")
    print("-" * 40)
    print()

def get_user_input(prompt="💬 What can I help you with? "):
    """Get user input with proper handling."""
    try:
        return input(prompt).strip()
    except (EOFError, KeyboardInterrupt):
        print("\n👋 Goodbye!")
        return "quit"

def parse_preferences(prefs_path):
    """Parse user_preference.txt into a dict, ignoring invalid lines."""
    prefs = {}
    if os.path.exists(prefs_path):
        try:
            with open(prefs_path, "r") as f:
                for line in f:
                    if ":" in line:
                        key, value = line.split(":", 1)
                        prefs[key.strip()] = value.strip()
        except Exception as e:
            warnings.warn(f"Error parsing preferences: {e}")
    return prefs

def collect_preferences(prefs_path):
    """Collect missing user preferences interactively, updating the file."""
    print("\n🛠️ Personalizing your experience! Filling in missing preferences.")

    # Define all keys and their choice options (None for free text)
    pref_definitions = {
        "Name": None,  # Free text
        "Role": ["Student", "Professional (Engineer/Developer)", "Creative/Designer", "Manager/Entrepreneur", "Other"],
        "Location": None,
        "Productive Time": ["Morning", "Afternoon", "Evening", "Late Night"],
        "Reminder Type": ["Gentle notification", "Phone call / Voice prompt", "Email / Message"],
        "Top Task Type": ["Learning / Study", "Coding / Development", "Writing / Content Creation", "Management / Planning", "Personal Growth / Health"],
        "Missed Task Handling": ["Auto-reschedule to next free slot", "Ask me before moving", "Skip if missed"],
        "Top Motivation": ["Checking things off a list", "Friendly competition / Leaderboards", "Music + Encouragement", "Supportive reminders (like a friend)"],
        "AI Tone": ["Calm & Professional", "Friendly & Casual", "Motivational & Pushy", "Fun & Humorous"],
        "Break Reminder": ["Every 25 min (Pomodoro style)", "Every 1 hour", "Every 2 hours", "Never remind me"],
        "Mood Check": ["Yes, ask me once a day", "Only if I look unproductive", "No, skip this"],
        "Current Focus": ["Finish studies", "Grow career skills", "Build side projects", "Explore & learn", "Health & balance"]  # Optional
    }

    existing_prefs = parse_preferences(prefs_path)
    updated_prefs = existing_prefs.copy()

    for key, options in pref_definitions.items():
        if key not in existing_prefs or not existing_prefs[key]:
            if options:
                print(f"\n{key}?")
                for i, opt in enumerate(options, 1):
                    print(f"{i}. {opt}")
                while True:
                    try:
                        choice = int(get_user_input("Choose a number: "))
                        if 1 <= choice <= len(options):
                            value = options[choice - 1]
                            if value == "Other":
                                value = get_user_input("Please specify: ").strip()
                            updated_prefs[key] = value
                            break
                        else:
                            print("Invalid choice. Try again.")
                    except ValueError:
                        print("Please enter a number.")
            else:
                value = get_user_input(f"{key}? ").strip()
                if value:
                    updated_prefs[key] = value

    # Optional Current Focus
    if "Current Focus" not in updated_prefs or not updated_prefs["Current Focus"]:
        set_goals = get_user_input("\nWould you like to set a long-term goal? (yes/no): ").strip().lower()
        if set_goals == "yes":
            options = pref_definitions["Current Focus"]
            print("\nWhat’s your current focus?")
            for i, opt in enumerate(options, 1):
                print(f"{i}. {opt}")
            while True:
                try:
                    choice = int(get_user_input("Choose a number: "))
                    if 1 <= choice <= len(options):
                        updated_prefs["Current Focus"] = options[choice - 1]
                        break
                    else:
                        print("Invalid choice. Try again.")
                except ValueError:
                    print("Please enter a number.")

    # Write back only if changes
    if updated_prefs != existing_prefs:
        try:
            os.makedirs(os.path.dirname(prefs_path), exist_ok=True)
            with open(prefs_path, "w") as f:
                for k, v in updated_prefs.items():
                    f.write(f"{k}: {v}\n")
            print("\n✅ Preferences updated! You can change them anytime by telling me new info.")
        except Exception as e:
            warnings.warn(f"Error saving preferences: {e}")
    else:
        print("\n✅ All preferences already set. No changes needed.")

def validate_environment():
    """Check if required files exist and have content."""
    required_files = [
        os.path.join(PROJECT_ROOT, 'knowledge', 'user_preference.txt'),
        os.path.join(PROJECT_ROOT, 'knowledge', 'operations.txt')
    ]

    for file_path in required_files:
        if not os.path.exists(file_path) or os.stat(file_path).st_size == 0:
            if 'user_preference.txt' in file_path:
                collect_preferences(file_path)  # Will create/populate
            else:
                print(f"❌ Missing or empty: {file_path}")
                return False
        elif 'user_preference.txt' in file_path:
            # Even if exists, check for completeness
            collect_preferences(file_path)  # Will fill missing if any

    return True

def run_single_query(user_query=None):
    """Run a single query execution."""
    if not validate_environment():
        return False
    if not user_query:
        user_query = get_user_input()
    if user_query.lower() in ['quit', 'exit', 'q']:
        return False
    if user_query.lower() in ['help', 'h']:
        display_help()
        return True
    if not user_query:
        print("❌ Please provide a valid query.")
        return True
    print(f"\n🔍 Processing: '{user_query}'")
    try:
        crew_instance = AiAgent()
        final_response = crew_instance.run_workflow(user_query)
        print(final_response)
        return True
    except Exception as e:
        print(f"❌ Error during execution: {e}")
        traceback.print_exc()
        print("Please try again or contact support.")
        return True

def run_interactive():
    """Run in interactive mode."""
    display_welcome()
    validate_environment()  # Ensure preferences are set/filled
    try:
        while True:
            if not run_single_query():
                break
    except KeyboardInterrupt:
        print("\n👋 Goodbye!")

def run():
    """Main entry point - supports both interactive and single-query modes."""
    if len(sys.argv) > 1:
        # Single query mode
        query = ' '.join(sys.argv[1:]).strip('"')
        run_single_query(query)
    else:
        # Interactive mode
        run_interactive()

def train():
    print("🎓 Training mode not implemented yet.")
    print("This feature will allow you to train the assistant on your specific use cases.")

def replay():
    print("🔄 Replay mode not implemented yet.")
    print("This feature will allow you to replay previous successful operations.")

def test():
    print("🧪 Running test scenarios...")
    test_queries = [
        "Calculate 10 + 15",
        "Get current time",
        "Generate a password",
        "Check system status"
    ]
    print(f"Running {len(test_queries)} test queries:\n")
    for i, query in enumerate(test_queries, 1):
        print(f"Test {i}: {query}")
        success = run_single_query(query)
        if not success:
            print("❌ Test failed")
            break
        print("-" * 40)
    print("✅ All tests completed!")

if __name__ == "__main__":
    run()