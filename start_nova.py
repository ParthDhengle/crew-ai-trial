#!/usr/bin/env python3
"""
Nova AI Assistant - Startup Script
Starts both backend and frontend services
"""

import subprocess
import sys
import os
import time
import signal
import threading
from pathlib import Path

def run_backend():
    """Start the FastAPI backend"""
    print("🚀 Starting Nova Backend...")
    backend_dir = Path("src")
    if not backend_dir.exists():
        print("❌ Backend directory 'src' not found")
        return None
    
    try:
        process = subprocess.Popen(
            [sys.executable, "app.py"],
            cwd=backend_dir,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            universal_newlines=True,
            bufsize=1
        )
        
        # Monitor backend output
        def monitor_backend():
            for line in iter(process.stdout.readline, ''):
                if line:
                    print(f"[BACKEND] {line.strip()}")
        
        thread = threading.Thread(target=monitor_backend, daemon=True)
        thread.start()
        
        # Wait a moment for backend to start
        time.sleep(3)
        
        if process.poll() is None:
            print("✅ Backend started successfully")
            return process
        else:
            print("❌ Backend failed to start")
            return None
            
    except Exception as e:
        print(f"❌ Error starting backend: {e}")
        return None

def run_frontend():
    """Start the React frontend"""
    print("🎨 Starting Nova Frontend...")
    frontend_dir = Path("frontend")
    if not frontend_dir.exists():
        print("❌ Frontend directory 'frontend' not found")
        return None
    
    try:
        process = subprocess.Popen(
            ["npm", "run", "dev"],
            cwd=frontend_dir,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            universal_newlines=True,
            bufsize=1
        )
        
        # Monitor frontend output
        def monitor_frontend():
            for line in iter(process.stdout.readline, ''):
                if line:
                    print(f"[FRONTEND] {line.strip()}")
        
        thread = threading.Thread(target=monitor_frontend, daemon=True)
        thread.start()
        
        # Wait a moment for frontend to start
        time.sleep(5)
        
        if process.poll() is None:
            print("✅ Frontend started successfully")
            return process
        else:
            print("❌ Frontend failed to start")
            return None
            
    except Exception as e:
        print(f"❌ Error starting frontend: {e}")
        return None

def check_dependencies():
    """Check if required dependencies are installed"""
    print("🔍 Checking dependencies...")
    
    # Check Python dependencies
    try:
        import fastapi
        import uvicorn
        print("✅ Python dependencies found")
    except ImportError as e:
        print(f"❌ Missing Python dependency: {e}")
        print("   Install with: pip install -r requirements.txt")
        return False
    
    # Check Node.js dependencies
    frontend_dir = Path("frontend")
    if frontend_dir.exists():
        node_modules = frontend_dir / "node_modules"
        if not node_modules.exists():
            print("❌ Node.js dependencies not found")
            print("   Install with: cd frontend && npm install")
            return False
        else:
            print("✅ Node.js dependencies found")
    
    return True

def cleanup_processes(processes):
    """Clean up running processes"""
    print("\n🛑 Shutting down services...")
    for name, process in processes.items():
        if process and process.poll() is None:
            print(f"   Stopping {name}...")
            process.terminate()
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
    print("✅ All services stopped")

def main():
    print("🌟 Nova AI Assistant - Startup Script")
    print("=" * 50)
    
    # Check dependencies
    if not check_dependencies():
        sys.exit(1)
    
    processes = {}
    
    try:
        # Start backend
        backend_process = run_backend()
        if not backend_process:
            print("❌ Failed to start backend. Exiting.")
            sys.exit(1)
        processes['backend'] = backend_process
        
        # Start frontend
        frontend_process = run_frontend()
        if not frontend_process:
            print("❌ Failed to start frontend. Exiting.")
            cleanup_processes(processes)
            sys.exit(1)
        processes['frontend'] = frontend_process
        
        print("\n" + "=" * 50)
        print("🎉 Nova AI Assistant is running!")
        print("\n📱 Frontend: http://localhost:5173")
        print("🔧 Backend API: http://127.0.0.1:8000")
        print("📚 API Docs: http://127.0.0.1:8000/docs")
        print("\nPress Ctrl+C to stop all services")
        print("=" * 50)
        
        # Wait for interrupt
        try:
            while True:
                time.sleep(1)
                # Check if processes are still running
                for name, process in processes.items():
                    if process.poll() is not None:
                        print(f"❌ {name} process stopped unexpectedly")
                        cleanup_processes(processes)
                        sys.exit(1)
        except KeyboardInterrupt:
            pass
            
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
    finally:
        cleanup_processes(processes)

if __name__ == "__main__":
    main()
