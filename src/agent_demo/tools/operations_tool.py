# src/agent_demo/tools/operations_tool.py
from crewai.tools import BaseTool
from typing import Type, List, Dict, Any
from pydantic import BaseModel, Field
import os
import subprocess
from datetime import datetime

class OperationItem(BaseModel):
    name: str
    parameters: Dict[str, Any] = {}

class OperationsToolInput(BaseModel):
    """Input schema: list of operations."""
    operations: List[OperationItem] = Field(..., description="List of operations to execute")

class OperationsTool(BaseTool):
    """
    Centralized operations executor: move all operation implementations here.
    The tool exposes a simple _run that accepts a list of operations (each a dict).
    """
    name: str = "Operations"
    description: str = "Execute high-level operations (file, system, web, util...)."
    args_schema: Type[BaseModel] = OperationsToolInput

    def _run(self, operations: List[Dict[str, Any]]) -> str:
        results = []
        for op in operations:
            name = op.get("name")
            params = op.get("parameters", {}) or {}
            try:
                handler = getattr(self, f"_op__{name}", None)
                if handler is None:
                    results.append(f"❌ Operation '{name}' not implemented.")
                    continue
                res = handler(params)
                results.append(res)
            except Exception as e:
                results.append(f"❌ Error executing '{name}': {str(e)}")
        return "\n".join(results)

    # --- Handlers: copy/adapt implementations from your crew.py ---
    def _op__send_email(self, params):
        to = params.get("to", "")
        subject = params.get("subject", "")
        # demo only: not sending real mail
        return f"✅ Email sent to {to} with subject '{subject}'"

    def _op__create_file(self, params):
        filename = params.get("filename", "")
        content = params.get("content", "")
        try:
            with open(filename, "w", encoding="utf-8") as f:
                f.write(content)
            return f"✅ File '{filename}' created successfully"
        except Exception as e:
            return f"❌ Error creating file '{filename}': {e}"

    def _op__read_file(self, params):
        filename = params.get("filename", "")
        try:
            with open(filename, "r", encoding="utf-8") as f:
                content = f.read()
            return f"✅ File '{filename}' read successfully. Content: {content[:200]}..."
        except Exception as e:
            return f"❌ Error reading file '{filename}': {e}"

    def _op__list_files(self, params):
        directory = params.get("directory", ".")
        try:
            files = os.listdir(directory)
            return f"✅ Files in '{directory}': {', '.join(files[:50])}" + ("..." if len(files) > 50 else "")
        except Exception as e:
            return f"❌ Error listing files '{directory}': {e}"

    def _op__open_application(self, params):
        app_name = params.get("app_name")
        if not app_name:
            return "❌ open_application missing app_name"
        try:
            subprocess.Popen([app_name], shell=True)
            return f"✅ Opened application: {app_name}"
        except Exception as e:
            return f"❌ Error opening application '{app_name}': {e}"

    def _op__open_website(self, params):
        url = params.get("url", "")
        if not url:
            return "❌ open_website missing url"
        try:
            subprocess.run(["python", "-m", "webbrowser", url], check=False)
            return f"✅ Opened website: {url}"
        except Exception as e:
            return f"❌ Error opening website '{url}': {e}"

    def _op__get_time(self, params):
        location = params.get("location", "local")
        return f"✅ Current time ({location}): {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"

    def _op__calculate(self, params):
        expression = params.get("expression", "")
        allowed_chars = set("0123456789+-*/().% ")
        if not expression or not all(c in allowed_chars for c in expression):
            return f"❌ Invalid or missing expression: {expression}"
        try:
            result = eval(expression)
            return f"✅ Calculation result: {expression} = {result}"
        except Exception as e:
            return f"❌ Calculation error: {e}"

    def _op__generate_password(self, params):
        import random, string
        length = int(params.get("length", 12))
        chars = string.ascii_letters + string.digits + "!@#$%^&*"
        return f"✅ Generated password: {''.join(random.choice(chars) for _ in range(length))}"

    # add more _op__<operation> handlers as needed, exactly matching operation names
