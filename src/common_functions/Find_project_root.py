import os
def find_project_root(marker_file='pyproject.toml') -> str:
    """Find the project root by searching upwards for the marker file."""
    current_dir = os.path.dirname(os.path.abspath(__file__))
    while current_dir != os.path.dirname(current_dir):  # Stop at system root
        if os.path.exists(os.path.join(current_dir, marker_file)):
            return current_dir
        current_dir = os.path.dirname(current_dir)
    raise FileNotFoundError("Project root not found. Ensure 'pyproject.toml' exists at the root.")
