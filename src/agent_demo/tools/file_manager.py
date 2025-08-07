# FILE: src/agent_demo/tools/file_manager.py
import os
from crewai_tools import BaseTool
from typing import Optional

class FileManagerTool(BaseTool):
    name = "FileManager"
    description = "Creates, updates, and manages files and directories for projects"

    def _run(self, action: str, path: str, content: Optional[str] = None) -> str:
        try:
            if action == "create_dir":
                os.makedirs(path, exist_ok=True)
                return f"Directory created: {path}"
            elif action == "create_file":
                os.makedirs(os.path.dirname(path), exist_ok=True)
                with open(path, "w") as f:
                    f.write(content or "")
                return f"File created: {path}"
            elif action == "update_file":
                with open(path, "w") as f:
                    f.write(content or "")
                return f"File updated: {path}"
            else:
                return "Invalid action. Valid actions: create_dir, create_file, update_file"
        except Exception as e:
            return f"Error: {str(e)}"