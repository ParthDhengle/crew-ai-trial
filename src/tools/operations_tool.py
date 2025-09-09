# src/agent_demo/tools/operations_tool.py
import os
from typing import List, Dict, Any
import json
import re
# --- DYNAMIC IMPORTS FROM MODULARIZED OPERATION FILES ---
from .operations.windows_directory.open_application import open_application
from .operations.windows_directory.create_folder import create_folder
from .operations.windows_directory.delete_folder import delete_folder
from .operations.communication.send_email import send_email
from .operations.communication.send_reply_email import send_reply_email
from .operations.communication.retrieveMails import retrieveMails
from .operations.communication.searchMail import searchMail
# from .operations.communication.make_call import make_call

from .operations.file_management.create_file import create_file
from .operations.file_management.read_file import read_file
from .operations.file_management.update_file import update_file
from .operations.file_management.delete_file import delete_file
from .operations.file_management.list_files import list_files
from .operations.file_management.copy_file import copy_file
from .operations.file_management.move_file import move_file
from .operations.file_management.search_files import search_files
from .operations.web_and_search.search_web import search_web
from .operations.web_and_search.download_file import download_file
from .operations.web_and_search.open_website import open_website
from .operations.web_and_search.get_weather import get_weather
from .operations.web_and_search.get_news import get_news
from .operations.web_and_search.browse_url import browse_url
from .operations.calendar_and_time.create_event import create_event
from .operations.calendar_and_time.list_events import list_events
from .operations.calendar_and_time.delete_event import delete_event
from .operations.calendar_and_time.get_time import get_time
from .operations.calendar_and_time.set_reminder import set_reminder
from .operations.calendar_and_time.update_event import update_event
from .operations.task_management.create_task import create_task
from .operations.task_management.update_task import update_task
from .operations.task_management.delete_task import delete_task
from .operations.task_management.list_tasks import list_tasks
from .operations.task_management.mark_task_complete import mark_task_complete
from .operations.data_handling.read_csv import read_csv
from .operations.data_handling.write_csv import write_csv
from .operations.data_handling.filter_csv import filter_csv
from .operations.data_handling.generate_report import generate_report
from .operations.data_handling.read_json import read_json
from .operations.data_handling.write_json import write_json
from .operations.media.play_music import play_music
from .operations.media.pause_music import pause_music
from .operations.media.stop_music import stop_music
from .operations.media.play_video import play_video
from .operations.media.take_screenshot import take_screenshot
from .operations.media.record_audio import record_audio
from .operations.media.play_audio import play_audio
from .operations.utilities.translate import translate
from .operations.utilities.summarize_text import summarize_text
from .operations.utilities.scan_qr_code import scan_qr_code
from .operations.utilities.calculate import calculate
from .operations.utilities.unit_convert import unit_convert
from .operations.utilities.spell_check import spell_check
from .operations.utilities.generate_password import generate_password
from .operations.ai_and_content_generation.generate_text import generate_text
from .operations.ai_and_content_generation.generate_image import generate_image
from .operations.ai_and_content_generation.generate_code import generate_code
from .operations.ai_and_content_generation.analyze_sentiment import analyze_sentiment
from .operations.ai_and_content_generation.chat_with_ai import chat_with_ai
from .operations.ai_and_content_generation.generate_document import generate_document
from .operations.system.shutdown_system import shutdown_system
from .operations.system.restart_system import restart_system
from .operations.system.check_system_status import check_system_status
from .operations.system.list_running_processes import list_running_processes
from .operations.system.kill_process import kill_process
from .operations.system.run_command import run_command
from .operations.system.update_system import update_system
from .operations.development_tools.git_clone import git_clone
from .operations.development_tools.git_commit import git_commit
from .operations.development_tools.git_push import git_push
from .operations.development_tools.git_pull import git_pull
from .operations.development_tools.git_status import git_status
from .operations.development_tools.pip_install import pip_install
from .operations.development_tools.run_python_script import run_python_script
from .operations.development_tools.open_in_ide import open_in_ide
from .operations.development_tools.build_project import build_project
from .operations.development_tools.deploy_project import deploy_project
from .operations.development_tools.debug_code import debug_code
from .operations.knowledge.knowledge_retrieval import knowledge_retrieval
from .operations.preferences.update_user_preference import update_user_preference
from common_functions.Find_project_root import find_project_root

PROJECT_ROOT =find_project_root()

class OperationsTool:
    """Central dispatcher: accepts a list of operation dicts and executes them using modular functions."""
    
    def __init__(self):
        self.param_definitions = self._parse_operations()
        
        # --- DYNAMIC OPERATION MAP ---
        # This map connects the string names from operations.txt to the actual imported functions.
        self.operation_map = {
            # Windows Directory
            "open_application": open_application, "create_folder": create_folder, "delete_folder": delete_folder,
            # Communication
            "send_email": send_email, "send_reply_email": send_reply_email, "retrieveMails": retrieveMails,
            "searchMail": searchMail, # "make_call": make_call,
            # File Management
            "create_file": create_file, "read_file": read_file, "update_file": update_file, "delete_file": delete_file,
            "list_files": list_files, "copy_file": copy_file, "move_file": move_file, "search_files": search_files,
            # Web & Search
            "search_web": search_web, "download_file": download_file, "open_website": open_website,
            "get_weather": get_weather, "get_news": get_news, "browse_url": browse_url,
            # Calendar & Time
            "create_event": create_event, "list_events": list_events, "delete_event": delete_event, "get_time": get_time,
            "set_reminder": set_reminder, "update_event": update_event,
            # Task Management
            "create_task": create_task, "update_task": update_task, "delete_task": delete_task,
            "list_tasks": list_tasks, "mark_task_complete": mark_task_complete,
            # Data Handling
            "read_csv": read_csv, "write_csv": write_csv, "filter_csv": filter_csv, "generate_report": generate_report,
            "read_json": read_json, "write_json": write_json,
            # Media
            "play_music": play_music, "pause_music": pause_music, "stop_music": stop_music, "play_video": play_video,
            "take_screenshot": take_screenshot, "record_audio": record_audio, "play_audio": play_audio,
            # Utilities
            "translate": translate, "summarize_text": summarize_text, "scan_qr_code": scan_qr_code,
            "calculate": calculate, "unit_convert": unit_convert, "spell_check": spell_check, "generate_password": generate_password,
            # AI & Content Generation
            "generate_text": generate_text, "generate_image": generate_image, "generate_code": generate_code,
            "analyze_sentiment": analyze_sentiment, "chat_with_ai": chat_with_ai, "generate_document": generate_document,
            # System
            "shutdown_system": shutdown_system, "restart_system": restart_system, "check_system_status": check_system_status,
            "list_running_processes": list_running_processes, "kill_process": kill_process, "run_command": run_command, "update_system": update_system,
            # Development Tools
            "git_clone": git_clone, "git_commit": git_commit, "git_push": git_push, "git_pull": git_pull, "git_status": git_status,
            "pip_install": pip_install, "run_python_script": run_python_script, "open_in_ide": open_in_ide,
            "build_project": build_project, "deploy_project": deploy_project, "debug_code": debug_code,
            # Knowledge
            "knowledge_retrieval": knowledge_retrieval,
            # Preferences
            "update_user_preference": update_user_preference,
        }

    def _parse_operations(self) -> Dict[str, Dict[str, List[str]]]:
        """Parse operations.json to get dynamic parameter definitions."""
        param_defs = {}
        try:
            # Use operations.json instead of operations.txt for faster parsing
            ops_path = os.path.join(PROJECT_ROOT, "knowledge", "operations.json")
            with open(ops_path, "r", encoding="utf-8") as f:
                operations_data = json.load(f)
            
            for op in operations_data:
                name = op.get("name", "")
                required_params = op.get("required_parameters", [])
                optional_params = op.get("optional_parameters", [])
                
                param_defs[name] = {
                    "required": required_params,
                    "optional": optional_params
                }
            
            print(f"✅ Loaded {len(param_defs)} operation definitions from operations.json")
            return param_defs
            
        except Exception as e:
            print(f"Error parsing operations.txt: {e}")
            return {}
        
        return param_defs

    def _validate_params(self, operation_name: str, provided_params: dict) -> tuple[bool, str, List[str]]:
        """Validate parameters and return success status, message, and missing parameters."""
        if operation_name not in self.param_definitions:
            return False, f"Unknown operation: {operation_name}", []
        
        definition = self.param_definitions[operation_name]
        required_params = definition["required"]
        optional_params = definition["optional"]
        all_valid_params = required_params + optional_params
        
        # Check for invalid parameters
        invalid_params = [p for p in provided_params if p not in all_valid_params]
        if invalid_params:
            return False, f"Invalid parameters for {operation_name}: {invalid_params}. Valid: {all_valid_params}", []
        
        # Check for missing required parameters
        missing_params = [p for p in required_params if p not in provided_params]
        if missing_params:
            return False, f"Missing required parameters for {operation_name}: {missing_params}", missing_params
        
        return True, "Valid parameters", []

    def _apply_parameter_corrections(self, operation_name: str, params: dict) -> dict:
        """Apply friendly parameter name corrections for common LLM mistakes."""
        corrected_params = params.copy()
        
        # Removed unnecessary remapping for send_email as function uses 'body' directly
        
        return corrected_params

    def _extract_parameters_from_response(self, user_response: str, missing_params: Dict[str, List[str]]) -> Dict[str, dict]:
        """Extract parameters from user's natural language response using AI."""
        try:
            extract_prompt = f"""Extract parameter values from this user response: "{user_response}"

Missing parameters:
"""
            for op_name, params in missing_params.items():
                extract_prompt += f"- {op_name}: {', '.join(params)}\n"
            
            extract_prompt += """
Output ONLY a valid JSON object where keys are operation names and values contain the extracted parameters.
If you cannot extract a parameter value, omit it from the JSON.
Example: {{"send_email": {{"to": "user@example.com", "subject": "Meeting"}}}}"""

            # Use generate_text operation to extract parameters
            if "generate_text" in self.operation_map:
                success, generated = self.operation_map["generate_text"](prompt=extract_prompt)
                if not success:
                    return {}
                
                # Clean the generated output
                generated = re.sub(r'```json|```', '', generated).strip()
                
                # Try to parse the JSON
                extracted = json.loads(generated)
                return extracted if isinstance(extracted, dict) else {}
            
        except Exception as e:
            print(f"Error extracting parameters: {e}")
        
        return {}

    def ask_parameters(self, missing_params: Dict[str, List[str]], max_attempts: int = 3) -> Dict[str, dict]:
        """Ask user for missing parameters and extract them from natural language response."""
        collected_params = {}
        remaining_params = missing_params.copy()
        
        for attempt in range(max_attempts):
            if not remaining_params:
                break
            
            # Create user-friendly question
            question = "\nI need some additional information to proceed:\n"
            for op_name, params in remaining_params.items():
                question += f"• For {op_name}: {', '.join(params)}\n"
            question += "\nPlease provide these details: "
            
            try:
                user_response = input(question)
                if not user_response.strip():
                    continue
                
                # Extract parameters from response
                extracted = self._extract_parameters_from_response(user_response, remaining_params)
                
                # Update collected parameters
                for op_name, new_params in extracted.items():
                    if op_name not in collected_params:
                        collected_params[op_name] = {}
                    collected_params[op_name].update(new_params)
                
                # Update remaining parameters
                new_remaining = {}
                for op_name, params in remaining_params.items():
                    still_missing = []
                    for param in params:
                        if op_name not in collected_params or param not in collected_params[op_name]:
                            still_missing.append(param)
                    if still_missing:
                        new_remaining[op_name] = still_missing
                
                remaining_params = new_remaining
                
                if not remaining_params:
                    print("✅ All parameters collected successfully!")
                    break
                    
            except KeyboardInterrupt:
                print("\n❌ Parameter collection cancelled by user")
                break
            except Exception as e:
                print(f"❌ Error collecting parameters: {e}")
                continue
        
        return collected_params

    def _run(self, operations: List[Dict[str, Any]]) -> str:
        """Execute operations with automatic parameter collection."""
        if not operations:
            return "❌ No operations provided"
        
        lines = []
        
        try:
            # Step 1: Validate all operations and collect missing parameters
            missing_params = {}
            validated_ops = {}
            
            for op in operations:
                name = op.get("name")
                if not name:
                    lines.append("❌ Operation missing 'name' field")
                    continue
                
                params = op.get("parameters", {})
                
                # Check if operation exists
                if name not in self.operation_map:
                    lines.append(f"❌ {name}: Operation not implemented")
                    continue
                
                # Validate parameters
                is_valid, message, missing = self._validate_params(name, params)
                
                if missing:
                    missing_params[name] = missing
                elif not is_valid:
                    lines.append(f"❌ {name}: {message}")
                    continue
                
                validated_ops[name] = params
            
            # Return early if there are fatal errors
            if lines and not missing_params:
                return "\n".join(lines)
            
            # Step 2: Collect missing parameters if any
            collected_params = {}
            if missing_params:
                print(f"\n🔍 Found {len(missing_params)} operations with missing parameters")
                collected_params = self.ask_parameters(missing_params)
            
            # Step 3: Execute all operations
            for op in operations:
                name = op.get("name")
                if name not in self.operation_map:
                    continue  # Already handled above
                
                # Combine original and collected parameters
                original_params = op.get("parameters", {})
                additional_params = collected_params.get(name, {})
                final_params = {**original_params, **additional_params}
                
                # Apply corrections
                corrected_params = self._apply_parameter_corrections(name, final_params)
                
                # Final validation
                is_valid, message, missing = self._validate_params(name, corrected_params)
                if not is_valid:
                    lines.append(f"❌ {name}: {message}")
                    continue
                
                # Execute operation
                try:
                    method = self.operation_map[name]
                    success, result = method(**corrected_params)
                    
                    if success:
                        lines.append(f"✅ {name}: {result}")
                    else:
                        lines.append(f"❌ {name}: {result}")
                        
                except TypeError as e:
                    lines.append(f"❌ {name}: Parameter error - {str(e)}")
                except Exception as e:
                    lines.append(f"❌ {name}: Execution error - {str(e)}")
            
            return "\n".join(lines) if lines else "✅ All operations completed successfully"
            
        except Exception as e:
            return f"❌ Critical error in operation execution: {str(e)}"