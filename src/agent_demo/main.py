# Modified: src/agent_demo/main.py
# Changes: 
# - Modified validate_environment to check if user_preference.txt exists and has content (size > 0)
# - Added collect_preferences() function to ask the questions and store in key:value format
# - Call collect_preferences if empty in run_interactive and run_single_query

import os
import sys
from datetime import datetime
from agent_demo.crew import AiAgent
import traceback

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


def get_user_input():
    """Get user input with proper handling."""
    try:
        user_query = input("💬 What can I help you with? ").strip()
        return user_query
    except (EOFError, KeyboardInterrupt):
        print("\n👋 Goodbye!")
        return "quit"


def collect_preferences():
    """Collect user preferences if the file is empty."""
    print("\n🛠️ It looks like your preferences aren't set up yet. Let's personalize your experience!")
    print("Answer the following questions to help the agent understand you better.\n")

    # 1. Basic Identity
    name = input("1. What’s your name or nickname? ").strip()

    roles = ["Student", "Professional (Engineer/Developer)", "Creative/Designer", "Manager/Entrepreneur", "Other"]
    print("\nWhat’s your role?")
    for i, role in enumerate(roles, 1):
        print(f"{i}. {role}")
    role_choice = int(input("Choose a number: ")) - 1
    role = roles[role_choice]
    if role == "Other":
        role = input("Please specify your role: ").strip()

    # Timezone/Location (ask, as detection requires external tools)
    location = input("\nWhat’s your timezone/location? (e.g., San Francisco, UTC-8): ").strip() or "San Francisco"

    # 2. Daily Rhythm & Energy
    productive_times = ["Morning", "Afternoon", "Evening", "Late Night"]
    print("\nWhen do you usually feel most productive?")
    for i, time in enumerate(productive_times, 1):
        print(f"{i}. {time}")
    productive_choice = int(input("Choose a number: ")) - 1
    productive_time = productive_times[productive_choice]

    reminder_types = ["Gentle notification", "Phone call / Voice prompt", "Email / Message"]
    print("\nHow do you want the agent to remind you?")
    for i, reminder in enumerate(reminder_types, 1):
        print(f"{i}. {reminder}")
    reminder_choice = int(input("Choose a number: ")) - 1
    reminder_type = reminder_types[reminder_choice]

    # 3. Work & Task Preferences
    task_types = ["Learning / Study", "Coding / Development", "Writing / Content Creation", "Management / Planning", "Personal Growth / Health"]
    print("\nWhat’s your top priority type of task?")
    for i, task in enumerate(task_types, 1):
        print(f"{i}. {task}")
    task_choice = int(input("Choose a number: ")) - 1
    top_task = task_types[task_choice]

    missed_task_handlings = ["Auto-reschedule to next free slot", "Ask me before moving", "Skip if missed"]
    print("\nHow do you want missed tasks handled?")
    for i, handling in enumerate(missed_task_handlings, 1):
        print(f"{i}. {handling}")
    missed_choice = int(input("Choose a number: ")) - 1
    missed_task = missed_task_handlings[missed_choice]

    # 4. Motivation & Support
    motivations = ["Checking things off a list", "Friendly competition / Leaderboards", "Music + Encouragement", "Supportive reminders (like a friend)"]
    print("\nWhat motivates you most?")
    for i, motivation in enumerate(motivations, 1):
        print(f"{i}. {motivation}")
    motivation_choice = int(input("Choose a number: ")) - 1
    top_motivation = motivations[motivation_choice]

    tones = ["Calm & Professional", "Friendly & Casual", "Motivational & Pushy", "Fun & Humorous"]
    print("\nHow do you prefer the AI tone?")
    for i, tone in enumerate(tones, 1):
        print(f"{i}. {tone}")
    tone_choice = int(input("Choose a number: ")) - 1
    ai_tone = tones[tone_choice]

    # 5. Well-being & Breaks
    break_reminders = ["Every 25 min (Pomodoro style)", "Every 1 hour", "Every 2 hours", "Never remind me"]
    print("\nHow often should I remind you to take breaks?")
    for i, break_opt in enumerate(break_reminders, 1):
        print(f"{i}. {break_opt}")
    break_choice = int(input("Choose a number: ")) - 1
    break_reminder = break_reminders[break_choice]

    mood_checks = ["Yes, ask me once a day", "Only if I look unproductive", "No, skip this"]
    print("\nDo you want me to check on your mood/energy daily?")
    for i, mood in enumerate(mood_checks, 1):
        print(f"{i}. {mood}")
    mood_choice = int(input("Choose a number: ")) - 1
    mood_check = mood_checks[mood_choice]

    # 6. Long-Term Goals (Optional)
    set_goals = input("\nWould you like to set a long-term goal? (yes/no): ").strip().lower()
    current_focus = ""
    if set_goals == "yes":
        focuses = ["Finish studies", "Grow career skills", "Build side projects", "Explore & learn", "Health & balance"]
        print("\nWhat’s your current focus?")
        for i, focus in enumerate(focuses, 1):
            print(f"{i}. {focus}")
        focus_choice = int(input("Choose a number: ")) - 1
        current_focus = focuses[focus_choice]

    # Store in file
    prefs_path = "knowledge/user_preference.txt"
    with open(prefs_path, "w") as f:
        f.write(f"Name: {name}\n")
        f.write(f"Role: {role}\n")
        f.write(f"Location: {location}\n")
        f.write(f"Productive Time: {productive_time}\n")
        f.write(f"Reminder Type: {reminder_type}\n")
        f.write(f"Top Task Type: {top_task}\n")
        f.write(f"Missed Task Handling: {missed_task}\n")
        f.write(f"Top Motivation: {top_motivation}\n")
        f.write(f"AI Tone: {ai_tone}\n")
        f.write(f"Break Reminder: {break_reminder}\n")
        f.write(f"Mood Check: {mood_check}\n")
        if current_focus:
            f.write(f"Current Focus: {current_focus}\n")

    print("\n✅ Preferences saved! You can update them anytime by telling me new info (e.g., 'My location is New York').")


def validate_environment():
    """Check if required files exist and have content."""
    required_files = [
        'knowledge/user_preference.txt',
        'knowledge/operations.txt'
    ]
    
    missing_or_empty = []
    for file_path in required_files:
        if not os.path.exists(file_path) or os.stat(file_path).st_size == 0:
            missing_or_empty.append(file_path)
        elif file_path == 'knowledge/operations.txt' and os.stat(file_path).st_size == 0:
            missing_or_empty.append(file_path)
    
    if 'knowledge/user_preference.txt' in missing_or_empty:
        collect_preferences()
        missing_or_empty.remove('knowledge/user_preference.txt')
    
    if missing_or_empty:
        print("❌ Missing or empty required files:")
        for file_path in missing_or_empty:
            print(f"   • {file_path}")
        print("\nPlease ensure all knowledge files are present and not empty.")
        return False
    
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
    print("⏳ Analyzing your request...\n")
    
    # Prepare inputs for the crew
    inputs = {
        'user_query': user_query,
        'current_year': str(datetime.now().year),
        'user_preferences_path': 'knowledge/user_preference.txt',
        'operations_file_path': 'knowledge/operations.txt'
    }

    try:
        # Create and run the crew
        crew_instance = AiAgent()
        result = crew_instance.crew().kickoff(inputs=inputs)
        
        print("\n" + "="*50)
        print("📋 ANALYSIS COMPLETE")
        print("="*50)
        
        # Execute the operations
        crew_instance.perform_operations("execution_plan.json")
        
        print("="*50)
        print()
        
        return True
        
    except Exception as e:
        print("❌ Error during execution — full traceback below:")
        traceback.print_exc()
        print("Please try again or contact support.")


def run_interactive():
    """Run in interactive mode."""
    display_welcome()
    validate_environment()  # Ensure preferences are collected at start
    
    try:
        while True:
            if not run_single_query():
                break
    except KeyboardInterrupt:
        print("\n👋 Goodbye!")


def run():
    """Main entry point - supports both interactive and single-query modes."""
    # Check if we're running with command line arguments
    if len(sys.argv) > 1:
        # Single query mode
        query = ' '.join(sys.argv[1:])
        if query.startswith('"') and query.endswith('"'):
            query = query[1:-1]  # Remove quotes if present
        run_single_query(query)
    else:
        # Interactive mode
        run_interactive()


def train():
    """Training function - placeholder for future ML training capabilities."""
    print("🎓 Training mode not implemented yet.")
    print("This feature will allow you to train the assistant on your specific use cases.")


def replay():
    """Replay function - replay previous execution plans."""
    print("🔄 Replay mode not implemented yet.")
    print("This feature will allow you to replay previous successful operations.")


def test():
    """Test function - run predefined test scenarios."""
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