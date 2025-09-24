# src/tools/operations_tool.py
import os
import json
from typing import List, Dict, Any, Tuple
import re
from common_functions.Find_project_root import find_project_root
from .operations.document_processor import document_summarize, document_translate
from firebase_client import get_operations  # For defs; fallback to JSON

PROJECT_ROOT = find_project_root()

# Dynamic imports for active ops only
from .operations.custom_search import custom_search
from .operations.powerbi_dashboard import powerbi_generate_dashboard
from .operations.os_ai_file_search import ai_assistant_file_query  # For search_files wrapper
from .operations.run_terminal_command import run_command  # Note: returns dict, so wrap it
from .operations.app_opening import open_app  # New import for open_app function
from .operations.Mail_search import searchMail  # Import searchMail function
from .operations.send_mail import send_email  # Import send_email function
from .operations.tasks.create_task import create_task  # Import create_task function
from .operations.tasks.update_task import update_task  # Import update_task function    
from .operations.tasks.delete_task import delete_task  # Import delete_task function
from .operations.tasks.mark_complete import mark_complete  # Import mark_complete function
from .operations.tasks.read_task import read_task  # Import read_task function


class OperationsTool:
    """Dispatcher for active operations only. Maps 'name' to funcs; validates via Firebase/json defs."""

    def __init__(self):
        self.param_definitions = self._parse_operations()
        self.operation_map = {
            # Active ops only
            "custom_search": custom_search,
            "document_summarize": document_summarize,
            "document_translate": document_translate,
            "powerbi_generate_dashboard": powerbi_generate_dashboard,
            "search_files": self._search_files_wrapper,
            "run_command": self._run_command_wrapper,
            "open_app": open_app,
            "search_mail": searchMail,
            "send_mail": send_email,
            # Add task ops
            "create_task": create_task,
            "update_task": update_task,
            "delete_task": delete_task,
            "mark_complete": mark_complete,
            "read_task": read_task,
        }

    def _parse_operations(self) -> Dict[str, Dict[str, List[str]]]:
        """Load op defs from Firebase (fallback json)."""
        try:
            operations = get_operations()
        except:
            # Fallback to local JSON
            json_path = os.path.join(PROJECT_ROOT, "knowledge", "operations.json")
            with open(json_path, "r") as f:
                data = json.load(f)
                operations = data.get("operations", [])
        param_defs = {}
        for op in operations:
            name = op.get("name", "")
            required = op.get("required_parameters", [])
            optional = op.get("optional_parameters", [])
            param_defs[name] = {"required": required, "optional": optional}
        print(f"✅ Loaded {len(param_defs)} active ops from Firebase/JSON")
        return param_defs

    def _search_files_wrapper(self, query: str, path: str = None, use_semantic: bool = True) -> Tuple[bool, str]:
        """Wrapper for search_files to match op signature (returns tuple[bool, str])."""
        try:
            root_dir = path or os.path.join(os.path.expanduser('~'), 'Downloads')
            results = ai_assistant_file_query(query, root_dir, use_semantic)
            result_str = json.dumps(results, indent=2) if results else "No files found."
            return True, f"Search results for '{query}':\n{result_str}"
        except Exception as e:
            return False, f"Error in search_files: {str(e)}"

    def _run_command_wrapper(self, command: str) -> Tuple[bool, str]:
        """Wrapper for run_command to convert dict return to tuple[bool, str]."""
        try:
            result_dict = run_command(command)
            if result_dict["success"]:
                return True, f"Command '{command}' executed successfully.\nOutput: {result_dict['output']}"
            else:
                return False, f"Command '{command}' failed.\nError: {result_dict['error']}\nOutput: {result_dict['output']}"
        except Exception as e:
            return False, f"Error in run_command: {str(e)}"

    def _validate_params(self, operation_name: str, provided_params: dict) -> tuple[bool, str, List[str]]:
        """Validate params against defs."""
        if operation_name not in self.param_definitions:
            return False, f"Unknown op: {operation_name}", []
        definition = self.param_definitions[operation_name]
        required = definition["required"]
        optional = definition["optional"]
        all_valid = required + optional
        invalid = [p for p in provided_params if p not in all_valid]
        if invalid:
            return False, f"Invalid params for {operation_name}: {invalid}", []
        missing = [p for p in required if p not in provided_params]
        if missing:
            return False, f"Missing required for {operation_name}: {missing}", missing
        return True, "Valid", []

    def _run(self, operations: List[Dict[str, Any]]) -> str:
        """Exec ops sequentially; append results. Handles missing params via placeholders."""
        if not operations:
            return "No ops provided."
        lines = []
        for op in operations:
            name = op.get("name")
            params = op.get("parameters", {})
            if name not in self.operation_map:
                lines.append(f"❌ {name}: Not implemented (inactive).")
                continue
            is_valid, msg, missing = self._validate_params(name, params)
            if missing:
                lines.append(f"❌ {name}: {msg} (Skipping; add params).")
                continue
            if not is_valid:
                lines.append(f"❌ {name}: {msg}")
                continue
            try:
                func = self.operation_map[name]
                success, result = func(**params)
                lines.append(f"✅ {name}: {result}")
            except Exception as e:
                lines.append(f"❌ {name}: {str(e)}")
        return "\n".join(lines) if lines else "✅ Ops complete."