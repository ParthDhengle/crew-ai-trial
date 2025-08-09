from crewai.tools import BaseTool
from typing import Type, List, Dict, Any
from pydantic import BaseModel, Field
import os
import subprocess
import ctypes

class SystemOperationToolInput(BaseModel):
    """Input schema for SystemOperationTool."""
    operations: List[Dict[str, Any]] = Field(..., description="List of operations to perform, each with 'operation' and 'parameters'.")

class SystemOperationTool(BaseTool):
    name: str = "SystemOperationTool"
    description: str = "Executes a list of system-level operations based on provided configuration."
    args_schema: Type[BaseModel] = SystemOperationToolInput

    def _run(self, operations: List[Dict[str, Any]]) -> str:
        results = []
        for op in operations:
            operation = op.get("operation")
            parameters = op.get("parameters", {})
            try:
                if operation == "change_brightness":
                    try:
                        import screen_brightness_control as sbc
                        brightness = parameters.get("brightness", 50)
                        sbc.set_brightness(brightness)
                        results.append(f"Brightness set to {brightness}%")
                    except ImportError:
                        results.append("Error: screen_brightness_control library is not installed.")
                elif operation == "change_wallpaper":
                    wallpaper_path = parameters.get("path")
                    if not os.path.exists(wallpaper_path):
                        results.append("Error: Wallpaper path does not exist.")
                    else:
                        ctypes.windll.user32.SystemParametersInfoW(20, 0, wallpaper_path, 0)
                        results.append("Wallpaper changed successfully.")
                elif operation == "open_application":
                    app_name = parameters.get("app_name")
                    subprocess.run([app_name], shell=True)
                    results.append(f"Opened application: {app_name}")
                elif operation == "shutdown":
                    os.system('shutdown /s /t 0')
                    results.append("System shutting down.")
                else:
                    results.append(f"Operation '{operation}' not supported.")
            except Exception as e:
                results.append(f"Error executing operation '{operation}': {str(e)}")
        return "\n".join(results)