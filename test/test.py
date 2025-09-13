# command_runner.py
import subprocess

def run_command(command: str):
    """
    Run a shell command and return its output and error if any.
    
    Args:
        command (str): The command to run (e.g., "mkdir test_folder").
    
    Returns:
        dict: Contains 'success' (bool), 'output' (str), and 'error' (str).
    """
    try:
        result = subprocess.run(
            command,
            shell=True,
            check=True,
            capture_output=True,
            text=True
        )
        return {"success": True, "output": result.stdout.strip(), "error": ""}
    except subprocess.CalledProcessError as e:
        return {"success": False, "output": e.stdout.strip(), "error": e.stderr.strip()}


response = run_command("echo > sample.cpp")
response = run_command("echo \"#include <iostream>\nusing namespace std;\nint main() {\n    cout << \\\"Hello from C++!\\\" << endl;\n    return 0;\n}\" > sample.cpp")
print(response)