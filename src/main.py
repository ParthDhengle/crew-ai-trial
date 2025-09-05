import os
import sys
from datetime import datetime
from crew import AiAgent
import traceback
import warnings
from pydantic import __version__ as pydantic_version
from common_functions.Find_project_root import find_project_root
from common_functions.User_preference import collect_preferences,parse_preferences
# Correct PROJECT_ROOT: From src/main.py, dirname=src, '..' gets to project root
PROJECT_ROOT = find_project_root()

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


def validate_environment():
    """Check if required files exist and have content."""
    required_files = [
        os.path.join(PROJECT_ROOT, 'knowledge', 'user_preference.txt'),
        os.path.join(PROJECT_ROOT, 'knowledge', 'operations.txt')
    ]

    for file_path in required_files:
        if not os.path.exists(file_path) or os.stat(file_path).st_size == 0:
            if 'user_preference.txt' in file_path:
                collect_preferences(file_path,get_user_input)  # Will create/populate
            else:
                print(f"❌ Missing or empty: {file_path}")
                return False
        elif 'user_preference.txt' in file_path:
            # Even if exists, check for completeness
            collect_preferences(file_path,get_user_input)  # Will fill missing if any

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