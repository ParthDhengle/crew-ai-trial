# src/agent_demo/tools/operations_tool.py
from pydantic import BaseModel, Field
try:
    from crewai_tools import Tool
except ImportError:
    class Tool:
        name: str
        description: str
        def _run(self, *args, **kwargs):
            raise NotImplementedError("Subclasses must implement _run")

import importlib
import traceback
from typing import List, Dict, Any
from .operations.knowledge_retrieval import KnowledgeRetrievalTool

# Map operation name -> module filename under agent_demo.tools.operations
OP_MODULE_MAP = {
    # Application
    "open_application": "application",
    
    # Communication
    "send_email": "communication",
    "send_sms": "communication",
    "make_call": "communication",
    "send_whatsapp_message": "communication",

    # File Management
    "create_file": "file_management",
    "read_file": "file_management",
    "update_file": "file_management",
    "delete_file": "file_management",
    "list_files": "file_management",

    # Web & Search
    "search_web": "web_search",
    "download_file": "web_search",
    "open_website": "web_search",
    "get_weather": "web_search",
    "get_news": "web_search",

    # Calendar & Time
    "create_event": "calendarAndTime",
    "list_events": "calendarAndTime",
    "delete_event": "calendarAndTime",
    "get_time": "calendarAndTime",
    "set_reminder": "calendarAndTime",

    # Task Management
    "create_task": "task_management",
    "update_task": "task_management",
    "delete_task": "task_management",
    "list_tasks": "task_management",

    # Data handling
    "read_csv": "file_management",
    "write_csv": "file_management",
    "filter_csv": "file_management",
    "generate_report": "file_management",

    # Media
    "play_music": "media",
    "pause_music": "media",
    "stop_music": "media",
    "play_video": "media",
    "take_screenshot": "media",

    # Utilities
    "calculate": "utilities",
    "translate": "utilities",
    "unit_convert": "utilities",
    "spell_check": "utilities",
    "summarize_text": "utilities",
    "generate_password": "utilities",
    "scan_qr_code": "utilities",

    # AI
    "generate_text": "ai_generation",
    "generate_image": "ai_generation",
    "generate_code": "ai_generation",
    "analyze_sentiment": "ai_generation",
    "chat_with_ai": "ai_generation",

    # System
    "shutdown_system": "system",
    "restart_system": "system",
    "check_system_status": "system",
    "list_running_processes": "system",
    "kill_process": "system",

    # Knowledge
    "retrieve_knowledge": "knowledge_retrieval",
}

class OperationsToolSchema(BaseModel):
    operations: List[Dict[str, Any]] = Field(
        ..., description="List of operations to execute, each with name, parameters, and optional description."
    )

class OperationsTool(Tool):
    name = "OperationsTool"
    description = "Executes a list of operations defined in the execution plan."
    args_schema = OperationsToolSchema

    def __init__(self, operations_pkg="agent_demo.tools.operations"):
        self.operations_pkg = operations_pkg

    def _load_module(self, module_name: str):
        """Dynamically import a module from agent_demo.tools.operations"""
        full = f"{self.operations_pkg}.{module_name}"
        try:
            return importlib.import_module(full)
        except Exception:
            return None

    def _call_handler(self, module, op_name: str, params: Dict[str, Any]):
        """
        Handler resolution policy:
        1. For retrieve_knowledge, use KnowledgeRetrievalTool directly.
        2. If module has a function named exactly op_name, call it.
        3. Else if module has 'handle_operation' generic function, call that with (op_name, params).
        4. Else return a not-implemented message.
        """
        try:
            if op_name == "retrieve_knowledge":
                tool = KnowledgeRetrievalTool()
                return True, tool._run(**params)
            if hasattr(module, op_name):
                fn = getattr(module, op_name)
                return True, fn(**(params or {}))
            if hasattr(module, "handle_operation"):
                return True, module.handle_operation(op_name, params or {})
            return False, f"Handler {op_name} not implemented in module {module.__name__}"
        except TypeError as e:
            return False, f"Parameter mismatch calling {op_name}: {e}"
        except Exception as e:
            tb = traceback.format_exc()
            return False, f"Exception running {op_name}: {e}\n{tb}"

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
            module_name = OP_MODULE_MAP.get(name)

            if not module_name:
                lines.append(f"❌ {name}: Unknown operation (no module mapping).")
                continue

            # Special handling for retrieve_knowledge
            if name == "retrieve_knowledge":
                res = self._call_handler(None, name, params)
            else:
                module = self._load_module(module_name)
                if not module:
                    lines.append(f"❌ {name}: Module '{module_name}' not found or failed to import.")
                    continue
                res = self._call_handler(module, name, params)

            # Standardize response
            if isinstance(res, tuple) and len(res) >= 1 and isinstance(res[0], bool):
                ok = res[0]
                payload = res[1] if len(res) > 1 else ""
                if ok:
                    lines.append(f"✅ {name}: {payload or desc or 'Success'}")
                else:
                    lines.append(f"❌ {name}: {payload or 'Failed'}")
            elif isinstance(res, dict) and res.get("success") is not None:
                if res.get("success"):
                    lines.append(f"✅ {name}: {res.get('message', desc or 'Success')}")
                else:
                    lines.append(f"❌ {name}: {res.get('message', 'Failed')}")
            else:
                # Assume truthy -> success, falsy -> failure
                if res:
                    lines.append(f"✅ {name}: {res}")
                else:
                    lines.append(f"✅ {name}: {desc or 'Completed'}")

        return "\n".join(lines)