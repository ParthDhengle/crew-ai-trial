import os
import sys
import traceback
import threading
import subprocess
import time
from datetime import datetime
from agent_demo.crew import AiAgent
from agent_demo.server import app
import uvicorn
import signal

def run_single_query(user_query):
    """Run a single query execution (kept for CLI args, but can be removed if pure UI)."""
    if not user_query:
        print("❌ Please provide a valid query.")
        return False

    print(f"\n🔍 Processing: '{user_query}'")
    print("⏳ Analyzing your request...\n")
    
    inputs = {
        'user_query': user_query,
        'current_year': str(datetime.now().year),
        'user_preferences_path': 'knowledge/user_preference.txt',
        'operations_file_path': 'knowledge/operations.txt'
    }

    try:
        crew_instance = AiAgent()
        result = crew_instance.crew().kickoff(inputs=inputs)
        
        print("\n" + "="*50)
        print("📋 ANALYSIS COMPLETE")
        print("="*50)
        
        crew_instance.perform_operations("execution_plan.json")
        
        print("="*50)
        print()
        
        return True
        
    except Exception as e:
        print("❌ Error during execution — full traceback below:")
        traceback.print_exc()
        print("Please try again or contact support.")

def run_ui():
    """Launch everything: Server in background, Electron UI, and text selection listener."""
    def start_server():
        print("Starting backend server...")
        uvicorn.run(app, host="127.0.0.1", port=8000, log_level="info")

    # Start server in thread
    server_thread = threading.Thread(target=start_server, daemon=True)
    server_thread.start()
    
    time.sleep(3)  # Wait for server to start

    # Launch Electron UI
    electron_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), 'electron_app'))
    print("Launching Electron UI...")
    electron_proc = subprocess.Popen(['npm', 'start'], cwd=electron_dir, shell=True)

    # Launch text selection listener (MVP popup)
    listener_path = os.path.abspath(os.path.join(os.path.dirname(__file__), 'desktop_app.py'))
    print("Launching text selection listener...")
    listener_proc = subprocess.Popen([sys.executable, listener_path], shell=True)

    # Graceful shutdown handling
    def shutdown(sig, frame):
        print("Shutting down...")
        electron_proc.terminate()
        listener_proc.terminate()
        sys.exit(0)

    signal.signal(signal.SIGINT, shutdown)
    signal.signal(signal.SIGTERM, shutdown)

    # Keep main process alive
    try:
        electron_proc.wait()  # Wait for Electron to exit
    except KeyboardInterrupt:
        shutdown(None, None)

def run():
    """Main entry point - defaults to UI (with listener), or single-query if args provided."""
    if len(sys.argv) > 1:
        query = ' '.join(sys.argv[1:])
        if query.startswith('"') and query.endswith('"'):
            query = query[1:-1]
        run_single_query(query)
    else:
        run_ui()

def train():
    print("🎓 Training mode not implemented yet.")

def replay():
    print("🔄 Replay mode not implemented yet.")

def test():
    print("🧪 Running test scenarios...")
    
    test_queries = [
        "Calculate 10 + 15",
        "Get current time",
        "Generate a password",
        "Check system status"
    ]
    
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