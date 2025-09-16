# src/agent_demo/tools/file_manager_tool.py
from crewai.tools import BaseTool
from typing import Type
from pydantic import BaseModel, Field
import os
from ..utils.logger import setup_logger

class FileManagerToolInput(BaseModel):
    """Input schema for FileManagerTool."""
    file_path: str = Field(..., description="Path to the file to read")

class FileManagerTool(BaseTool):
    # SHORT, NO-SPACES NAME — helps YAML/registry matching
    name: str = "FileManager"
    description: str = (
        "Tool for reading files. Useful for accessing user preferences, operations lists, "
        "and other configuration files. Provide the file path to read its contents."
    )
    args_schema: Type[BaseModel] = FileManagerToolInput

    def _run(self, file_path: str) -> str:
        logger = setup_logger()
        try:
            if not os.path.exists(file_path):
                logger.error(f"File not found: {file_path}")
                return f"Error: File '{file_path}' not found."
            with open(file_path, 'r', encoding='utf-8') as file:
                content = file.read()
            logger.info(f"Read file successfully: {file_path}")
            return f"Content of {file_path}:\n{content}"
        except Exception as e:
            logger.error(f"Error reading file '{file_path}': {str(e)}")
            return f"Error reading file '{file_path}': {str(e)}"