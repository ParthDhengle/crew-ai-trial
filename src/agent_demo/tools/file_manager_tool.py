# src/agent_demo/tools/file_manager_tool.py
import os
from typing import Optional

class FileManagerTool:
    """Small helper used by analyzer agent to read knowledge files, write output, etc."""

    def read_text(self, path: str) -> Optional[str]:
        try:
            with open(path, "r", encoding="utf-8") as f:
                return f.read()
        except FileNotFoundError:
            return None
        except Exception:
            return None

    def write_text(self, path: str, content: str) -> bool:
        try:
            d = os.path.dirname(path)
            if d and not os.path.exists(d):
                os.makedirs(d, exist_ok=True)
            with open(path, "w", encoding="utf-8") as f:
                f.write(content)
            return True
        except Exception:
            return False

    def exists(self, path: str) -> bool:
        return os.path.exists(path)
