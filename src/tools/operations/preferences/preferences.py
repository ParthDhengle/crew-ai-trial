# src/agent_demo/tools/operations/preferences.py
import os

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..', '..'))
PREFS_PATH = os.path.join(PROJECT_ROOT, "knowledge", "user_preference.txt")

def update_user_preference(key: str, value: str):
    """Update or add a key-value pair in user_preference.txt."""
    prefs = {}
    if os.path.exists(PREFS_PATH):
        with open(PREFS_PATH, "r") as f:
            for line in f:
                if ":" in line:
                    k, v = line.split(":", 1)
                    prefs[k.strip()] = v.strip()
    
    prefs[key] = value
    
    with open(PREFS_PATH, "w") as f:
        for k, v in prefs.items():
            f.write(f"{k}: {v}\n")
    
    return (True, f"Updated {key} to {value}")