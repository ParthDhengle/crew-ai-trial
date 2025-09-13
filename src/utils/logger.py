# src/utils/logger.py
import logging
import os
from datetime import datetime
try:
    from common_functions.Find_project_root import find_project_root
except ImportError as e:
    print(f"Error importing find_project_root: {e}. Using current directory as fallback.")
    def find_project_root():
        return os.path.dirname(os.path.abspath(__file__))

# Configure logger
def setup_logger():
    logger = logging.getLogger("AIAssistant")
    logger.setLevel(logging.DEBUG)  # Capture all log levels

    # Avoid duplicate handlers if logger is already configured
    if not logger.handlers:
        try:
            # Create file handler for app.log
            project_root = find_project_root()
            log_file = os.path.join(project_root, "app.log")
            file_handler = logging.FileHandler(log_file, encoding="utf-8")
            file_handler.setLevel(logging.DEBUG)
        except Exception as e:
            print(f"Error setting up file handler for {log_file}: {e}. Using console only.")
            file_handler = None

        # Create console handler for terminal output
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)

        # Define log format
        formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S"
        )
        if file_handler:
            file_handler.setFormatter(formatter)
        console_handler.setFormatter(formatter)

        # Add handlers to logger
        if file_handler:
            logger.addHandler(file_handler)
        logger.addHandler(console_handler)

    return logger