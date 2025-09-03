# src/agent_demo/tools/operations_tool.py
import os
import traceback
import subprocess
import webbrowser
import requests
import json
import csv
import datetime
import shutil
from typing import List, Dict, Any

class OperationsTool:
    """Central dispatcher: accepts a list of operation dicts and executes them using simple Python functions."""
    
    def __init__(self):
        self.prefs_path = "knowledge/user_preference.txt"
    
    # ============ PREFERENCES ============
    def update_user_preference(self, key: str, value: str):
        """Update or add a key-value pair in user_preference.txt."""
        prefs = {}
        if os.path.exists(self.prefs_path):
            with open(self.prefs_path, "r") as f:
                for line in f:
                    if ":" in line:
                        k, v = line.split(":", 1)
                        prefs[k.strip()] = v.strip()
        
        prefs[key] = value
        
        with open(self.prefs_path, "w") as f:
            for k, v in prefs.items():
                f.write(f"{k}: {v}\n")
        
        return (True, f"Updated {key} to {value}")
    
    # ============ WINDOWS DIRECTORY ============
    def open_application(self, app_name: str):
        """Opens an application on the desktop"""
        try:
            subprocess.run(["start", app_name], shell=True, check=True)
            return (True, f"Opened {app_name}")
        except Exception as e:
            return (False, f"Failed to open {app_name}: {e}")
    
    def create_folder(self, path: str):
        """Creates a new directory at the specified path"""
        try:
            os.makedirs(path, exist_ok=True)
            return (True, f"Created folder: {path}")
        except Exception as e:
            return (False, f"Failed to create folder: {e}")
    
    def delete_folder(self, path: str):
        """Deletes a directory (and its contents if non-empty)"""
        try:
            shutil.rmtree(path)
            return (True, f"Deleted folder: {path}")
        except Exception as e:
            return (False, f"Failed to delete folder: {e}")
    
    # ============ COMMUNICATION ============
    def send_email(self, to: str, subject: str, info: str = None, **kwargs):
        """Mock email sending - handles both 'info' and 'body' parameters for flexibility"""
        try:
            # Handle both 'info' (correct) and 'body' (LLM mistake) parameters
            content = info or kwargs.get('body') or kwargs.get('message') or 'Generated email content'
            
            email_content = f"To: {to}\nSubject: {subject}\n\n{content}"
            with open("email_log.txt", "a") as f:
                f.write(f"\n--- EMAIL SENT at {datetime.datetime.now()} ---\n")
                f.write(email_content)
                f.write("\n--- END EMAIL ---\n\n")
            return (True, f"Email sent to {to} with subject: {subject}")
        except Exception as e:
            return (False, f"Failed to send email: {e}")
    
    def send_sms(self, to: str, message: str):
        """Mock SMS sending"""
        try:
            with open("sms_log.txt", "a") as f:
                f.write(f"{datetime.datetime.now()}: SMS to {to}: {message}\n")
            return (True, f"SMS sent to {to}")
        except Exception as e:
            return (False, f"Failed to send SMS: {e}")
    
    # ============ FILE MANAGEMENT ============
    def create_file(self, filename: str, content: str):
        """Creates a file with given content"""
        try:
            with open(filename, 'w', encoding='utf-8') as f:
                f.write(content)
            return (True, f"Created file: {filename}")
        except Exception as e:
            return (False, f"Failed to create file: {e}")
    
    def read_file(self, filename: str):
        """Reads and returns content of a file"""
        try:
            with open(filename, 'r', encoding='utf-8') as f:
                content = f.read()
            return (True, f"File content:\n{content}")
        except Exception as e:
            return (False, f"Failed to read file: {e}")
    
    def update_file(self, filename: str, new_content: str):
        """Updates content of a file"""
        try:
            with open(filename, 'w', encoding='utf-8') as f:
                f.write(new_content)
            return (True, f"Updated file: {filename}")
        except Exception as e:
            return (False, f"Failed to update file: {e}")
    
    def delete_file(self, filename: str):
        """Deletes a specified file"""
        try:
            os.remove(filename)
            return (True, f"Deleted file: {filename}")
        except Exception as e:
            return (False, f"Failed to delete file: {e}")
    
    def list_files(self, directory: str):
        """Lists all files in a directory"""
        try:
            files = os.listdir(directory)
            return (True, f"Files in {directory}:\n" + "\n".join(files))
        except Exception as e:
            return (False, f"Failed to list files: {e}")
    
    # ============ WEB & SEARCH ============
    def search_web(self, query: str):
        """Mock web search - returns a simple response"""
        try:
            # In production, integrate with a search API
            return (True, f"Search results for '{query}': [Mock results - integrate with actual search API]")
        except Exception as e:
            return (False, f"Failed to search web: {e}")
    
    def open_website(self, url: str):
        """Opens a website in the system browser"""
        try:
            webbrowser.open(url)
            return (True, f"Opened website: {url}")
        except Exception as e:
            return (False, f"Failed to open website: {e}")
    
    def get_weather(self, location: str):
        """Mock weather API - in production, use a real weather service"""
        try:
            # Mock response - integrate with actual weather API
            return (True, f"Weather in {location}: 22°C, Partly cloudy [Mock data - integrate with weather API]")
        except Exception as e:
            return (False, f"Failed to get weather: {e}")
    
    # ============ UTILITIES ============
    def calculate(self, expression: str):
        """Evaluates a mathematical expression"""
        try:
            # Safe evaluation - only allow basic math
            allowed_chars = set('0123456789+-*/.() ')
            if all(c in allowed_chars for c in expression):
                result = eval(expression)
                return (True, f"Result: {result}")
            else:
                return (False, "Expression contains invalid characters")
        except Exception as e:
            return (False, f"Failed to calculate: {e}")
    
    def generate_password(self, length: int = 12):
        """Generates a secure password"""
        try:
            import random
            import string
            chars = string.ascii_letters + string.digits + "!@#$%^&*"
            password = ''.join(random.choice(chars) for _ in range(length))
            return (True, f"Generated password: {password}")
        except Exception as e:
            return (False, f"Failed to generate password: {e}")
    
    def get_time(self, location: str = "local"):
        """Returns current time for a location"""
        try:
            current_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            return (True, f"Current time ({location}): {current_time}")
        except Exception as e:
            return (False, f"Failed to get time: {e}")
    
    # ============ SYSTEM ============
    def check_system_status(self):
        """Returns system health status"""
        try:
            import psutil
            cpu = psutil.cpu_percent()
            memory = psutil.virtual_memory().percent
            disk = psutil.disk_usage('/').percent
            return (True, f"System Status:\nCPU: {cpu}%\nMemory: {memory}%\nDisk: {disk}%")
        except Exception as e:
            return (False, f"Failed to check system status: {e}")
    
    def take_screenshot(self, save_path: str):
        """Takes a screenshot"""
        try:
            import pyautogui
            screenshot = pyautogui.screenshot()
            screenshot.save(save_path)
            return (True, f"Screenshot saved to: {save_path}")
        except Exception as e:
            return (False, f"Failed to take screenshot: {e}")
    
    # ============ KNOWLEDGE RETRIEVAL ============
    def retrieve_knowledge(self, query: str):
        """Mock knowledge retrieval - in production, integrate with search or knowledge base"""
        try:
            # Simple response based on query keywords
            if "weather" in query.lower():
                return (True, "Weather refers to atmospheric conditions including temperature, humidity, precipitation, and wind patterns at a specific time and place.")
            elif "ai" in query.lower():
                return (True, "Artificial Intelligence (AI) refers to computer systems that can perform tasks typically requiring human intelligence, such as learning, reasoning, and problem-solving.")
            else:
                return (True, f"Knowledge about '{query}': [This would connect to a knowledge base or search API in production]")
        except Exception as e:
            return (False, f"Failed to retrieve knowledge: {e}")
    
    # ============ PARAMETER VALIDATION ============
    def _validate_and_map_params(self, operation_name: str, provided_params: dict) -> tuple:
        """Validate parameters against operations.txt definitions and map them correctly"""
        
        # Define the exact parameter mapping from operations.txt
        param_definitions = {
            "send_email": {"required": ["to", "subject"], "optional": ["info"]},
            "send_sms": {"required": ["to", "message"], "optional": []},
            "create_file": {"required": ["filename", "content"], "optional": []},
            "read_file": {"required": ["filename"], "optional": []},
            "update_file": {"required": ["filename", "new_content"], "optional": []},
            "delete_file": {"required": ["filename"], "optional": []},
            "list_files": {"required": ["directory"], "optional": []},
            "calculate": {"required": ["expression"], "optional": []},
            "generate_password": {"required": [], "optional": ["length"]},
            "get_weather": {"required": ["location"], "optional": []},
            "search_web": {"required": ["query"], "optional": []},
            "open_website": {"required": ["url"], "optional": []},
            "get_time": {"required": [], "optional": ["location"]},
            "take_screenshot": {"required": ["save_path"], "optional": []},
            "retrieve_knowledge": {"required": ["query"], "optional": []},
            "update_user_preference": {"required": ["key", "value"], "optional": []},
        }
        
        if operation_name not in param_definitions:
            return False, f"Unknown operation: {operation_name}"
        
        definition = param_definitions[operation_name]
        required_params = definition["required"]
        optional_params = definition["optional"]
        all_valid_params = required_params + optional_params
        
        # Check for invalid parameters
        invalid_params = [p for p in provided_params.keys() if p not in all_valid_params]
        if invalid_params:
            return False, f"Invalid parameters for {operation_name}: {invalid_params}. Valid parameters are: {all_valid_params}"
        
        # Check for missing required parameters
        missing_params = [p for p in required_params if p not in provided_params]
        if missing_params:
            return False, f"Missing required parameters for {operation_name}: {missing_params}"
        
        # Map common wrong parameters to correct ones
        corrected_params = provided_params.copy()
        if operation_name == "send_email":
            # Map 'body' or 'message' to 'info'
            if 'body' in corrected_params and 'info' not in corrected_params:
                corrected_params['info'] = corrected_params.pop('body')
            elif 'message' in corrected_params and 'info' not in corrected_params:
                corrected_params['info'] = corrected_params.pop('message')
        
        return True, corrected_params
    # ============ MAIN EXECUTION ============
    def _run(self, operations: List[Dict[str, Any]]) -> str:
        """
        operations: list of dicts: { "name": "create_file", "parameters": {...}, "description": "..." }
        Returns: multi-line string; each line should start with ✅ or ❌ for success/failure
        """
        lines = []
        
        for op in operations:
            name = op.get("name")
            params = op.get("parameters", {}) or {}
            desc = op.get("description", "")
            
            # First validate and correct parameters
            validation_result = self._validate_and_map_params(name, params)
            if not validation_result[0]:  # Validation failed
                lines.append(f"❌ {name}: {validation_result[1]}")
                continue
            
            corrected_params = validation_result[1]
            
            # Check if operation method exists
            if hasattr(self, name):
                try:
                    method = getattr(self, name)
                    res = method(**corrected_params)
                    
                    # Standardize response
                    if isinstance(res, tuple) and len(res) >= 2:
                        success, message = res[0], res[1]
                        if success:
                            lines.append(f"✅ {name}: {message}")
                        else:
                            lines.append(f"❌ {name}: {message}")
                    else:
                        lines.append(f"✅ {name}: {res}")
                        
                except TypeError as e:
                    lines.append(f"❌ {name}: Parameter error - {e}")
                except Exception as e:
                    lines.append(f"❌ {name}: Execution error - {e}")
            else:
                lines.append(f"❌ {name}: Operation not implemented")
        
        return "\n".join(lines)