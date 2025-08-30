import os
import sys
from datetime import datetime
from agent_demo.crew import AiAgent
import traceback
import multiprocessing
import subprocess

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

def validate_environment():
    """Check if required files exist."""
    required_files = [
        'knowledge/user_preference.txt',
        'knowledge/operations.txt'
    ]
    
    missing_files = []
    for file_path in required_files:
        if not os.path.exists(file_path):
            missing_files.append(file_path)
    
    if missing_files:
        print("❌ Missing required files:")
        for file_path in missing_files:
            print(f"   • {file_path}")
        print("\nPlease ensure all knowledge files are present.")
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
    
    try:
        while True:
            if not run_single_query():
                break
    except KeyboardInterrupt:
        print("\n👋 Goodbye!")

def run_backend():
    subprocess.run(["uv", "run", "uvicorn", "src.agent_demo.server:app", "--host", "127.0.0.1", "--port", "8000"])

def run():
    """Main entry point - supports both interactive, single-query, and UI modes."""
    # Check if we're running with command line arguments
    if len(sys.argv) > 1:
        if sys.argv[1] == "--with-ui":
            p = multiprocessing.Process(target=run_backend)
            p.start()
            from . import desktop_app  # Use relative import
            desktop_app.main()
            p.terminate()
        else:
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