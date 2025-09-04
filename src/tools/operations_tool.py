# src/agent_demo/tools/operations_tool.py
import os
from typing import List, Dict, Any

# --- DYNAMIC IMPORTS FROM MODULARIZED OPERATION FILES ---
from .operations.windows_directory import open_application, create_folder, delete_folder
from .operations.communication import (send_email, send_reply_email, retrieveMails, searchMail, 
                                     make_call)
from .operations.file_management import (create_file, read_file, update_file, delete_file, 
                                       list_files, copy_file, move_file, search_files)
from .operations.web_and_search import (search_web, download_file, open_website, 
                                      get_weather, get_news, browse_url)
from .operations.calendar_and_time import (create_event, list_events, delete_event, 
                                         get_time, set_reminder, update_event)
from .operations.task_management import (create_task, update_task, delete_task, 
                                       list_tasks, mark_task_complete)
from .operations.data_handling import (read_csv, write_csv, filter_csv, generate_report, 
                                     read_json, write_json)
from .operations.media import (play_music, pause_music, stop_music, play_video, 
                             take_screenshot, record_audio, play_audio)
from .operations.utilities import (translate, summarize_text, scan_qr_code, calculate, 
                                 unit_convert, spell_check, generate_password)
from .operations.ai_and_content_generation import (generate_text, generate_image, generate_code, 
                                                 analyze_sentiment, chat_with_ai, generate_document)
from .operations.system import (shutdown_system, restart_system, check_system_status, 
                              list_running_processes, kill_process, run_command, update_system)
from .operations.development_tools import (git_clone, git_commit, git_push, git_pull, git_status, 
                                         pip_install, run_python_script, open_in_ide, 
                                         build_project, deploy_project, debug_code)
from .operations.knowledge import knowledge_retrieval
from .operations.preferences import update_user_preference

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..'))

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
            "searchMail": searchMail,  "make_call": make_call,
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

    def _parse_operations(self):
        """Parse operations.txt to get dynamic parameter definitions."""
        ops_path = os.path.join(PROJECT_ROOT, "knowledge", "operations.txt")
        param_defs = {}
        with open(ops_path, "r", encoding="utf-8") as f:
            for line in f:
                if line.strip() and not line.startswith("#") and "|" in line:
                    parts = [p.strip() for p in line.split("|")]
                    name = parts[0]
                    if len(parts) > 1:
                        params_str = parts[1][11:].strip() if parts[1].startswith("parameters:") else ""
                        if params_str.lower() == "none":
                            required, optional = [], []
                        else:
                            params = [p.strip() for p in params_str.split(",") if p.strip()]
                            required = [p for p in params if '=' not in p]
                            optional = [p.split('=')[0].strip() for p in params if '=' in p]
                        param_defs[name] = {"required": required, "optional": optional}
        return param_defs

    def _validate_and_map_params(self, operation_name: str, provided_params: dict) -> tuple:
        """Validate parameters against operations.txt definitions and map them correctly."""
        if operation_name not in self.param_definitions:
            return False, f"Unknown operation: {operation_name}"
        
        definition = self.param_definitions[operation_name]
        required_params = definition["required"]
        all_valid_params = required_params + definition["optional"]
        
        invalid_params = [p for p in provided_params if p not in all_valid_params]
        if invalid_params:
            return False, f"Invalid parameters for {operation_name}: {invalid_params}. Valid: {all_valid_params}"
            
        missing_params = [p for p in required_params if p not in provided_params]
        if missing_params:
            return False, f"Missing required parameters for {operation_name}: {missing_params}"
        
        # Friendly mapping for common LLM mistakes
        corrected_params = provided_params.copy()
        if operation_name in ["send_email", "send_reply_email"]:
            if 'body' in corrected_params and 'info' not in corrected_params:
                corrected_params['info'] = corrected_params.pop('body')
            elif 'message' in corrected_params and 'info' not in corrected_params:
                corrected_params['info'] = corrected_params.pop('message')

        return True, corrected_params

    def _run(self, operations: List[Dict[str, Any]]) -> str:
        """
        Executes a list of operations by looking them up in the operation_map.
        Returns a multi-line string with success/failure for each operation.
        """
        lines = []
        for op in operations:
            name = op.get("name")
            params = op.get("parameters", {}) or {}
            
            validation_ok, result = self._validate_and_map_params(name, params)
            if not validation_ok:
                lines.append(f"❌ {name}: {result}")
                continue
            
            corrected_params = result
            method = self.operation_map.get(name)
            
            if method:
                try:
                    success, message = method(**corrected_params)
                    if success:
                        lines.append(f"✅ {name}: {message}")
                    else:
                        lines.append(f"❌ {name}: {message}")
                except TypeError as e:
                    lines.append(f"❌ {name}: Parameter error - {e}")
                except Exception as e:
                    lines.append(f"❌ {name}: Execution error - {e}")
            else:
                lines.append(f"❌ {name}: Operation not implemented in the map")
        
        return "\n".join(lines)