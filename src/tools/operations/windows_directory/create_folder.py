"""
windows_directory.py — Windows directory and application operations.
Contains functions for opening applications and managing directories.
"""

import os
import shutil
from pathlib import Path
import subprocess
import sys
import json
import time
import webbrowser
from difflib import SequenceMatcher
import re

# ---------- Config ----------
CACHE_FILE = "app_index.json"
ALIASES_FILE = "aliases.json"
CACHE_TTL_SECONDS = 60 * 60 * 24  # 24 hours
TOP_N = 6
AUTO_LAUNCH_THRESHOLD = 0.92  # auto-launch if >=
MIN_DISPLAY_SCORE = 0.30

DEFAULT_ALIASES = {
    "calculator": r"C:\Windows\System32\calc.exe",
    "notepad": r"C:\Windows\System32\notepad.exe"
}

# ---------- Utilities ----------
def read_json(p):
    try:
        with open(p, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None

def write_json(p, data):
    try:
        with open(p, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
    except Exception:
        pass

def is_windows():
    return os.name == "nt"

def create_folder(path):
    """
    Create a new directory at the specified path.
    
    Args:
        path (str): Path where the new directory will be created
        
    Returns:
        tuple: (success: bool, message: str)
    """
    if not is_windows():
        return (False, "This operation only runs on Windows.")

    if not path or not path.strip():
        return (False, "No path provided")
    
    try:
        path = os.path.expandvars(path.strip())
        os.makedirs(path, exist_ok=True)
        return (True, f"Successfully created directory at {path}")
    except PermissionError:
        return (False, f"Permission denied: Unable to create directory at {path}")
    except OSError as e:
        return (False, f"Failed to create directory at {path}: {str(e)}")
