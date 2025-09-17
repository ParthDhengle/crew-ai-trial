# src/tools/operations_tool.py
import os
from typing import List, Dict, Any, Tuple
import json
import re
from common_functions.Find_project_root import find_project_root
from .operations.document_processor import document_summarize, document_translate
from firebase_client import get_operations  # For defs

PROJECT_ROOT = find_project_root()

# Dynamic imports for your ops
from .operations.web_search import web_search
from .operations.translate import translate_text
from .operations.summarization import summarize_text
from .operations.ragsearch import rag_search
from .operations.file_search import file_search
from .operations.app_opening import open_app
from .operations.run_terminal_command import run_command
from .operations.events.create_event import create_event
from .operations.tasks.create_task import create_task
from .operations.tasks.read_task import read_task
from .operations.tasks.update_task import update_task
from .operations.tasks.mark_complete import mark_complete

class OperationsTool:
    """Dispatcher for your specified operations. Maps 'name' to funcs; validates via Firebase/json defs."""

    def __init__(self):
        self.param_definitions = self._parse_operations()
        self.operation_map = {
            # Direct ops
            "web_search": web_search,
            "translate": translate_text,
            "summarization": summarize_text,
            "ragsearch": rag_search,
            "file_search": file_search,
            "app_opening": open_app,
            "run_terminal_command": run_command,
            # Calendar
            "calendar.create_event": create_event,
            # Tasks
            "task.create": create_task,
            "task.list": read_task,
            "task.update": update_task,
            "task.mark_complete": mark_complete,
            # Document processing
            "document_summarize": document_summarize,
            "document_translate": document_translate,
        }

    def _parse_operations(self) -> Dict[str, Dict[str, List[str]]]:
        """Load op defs from Firebase (fallback json)."""
        operations = get_operations()
        param_defs = {}
        for op in operations:
            name = op.get("name", "")
            required = op.get("required_parameters", [])
            optional = op.get("optional_parameters", [])
            param_defs[name] = {"required": required, "optional": optional}
        print(f"✅ Loaded {len(param_defs)} ops from Firebase/json")
        return param_defs

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
                lines.append(f"❌ {name}: Not implemented.")
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