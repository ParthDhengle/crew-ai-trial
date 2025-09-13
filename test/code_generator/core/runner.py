import os
import subprocess
import shutil

def run_project(plan, root):
    """
    Executes the project in a sandboxed manner: changes to project dir, uses timeouts.
    Handles installation based on detected files (requirements.txt or package.json).
    Collects test and run commands from plan.
    Captures output/errors for debugging.
    For safety: timeouts prevent infinite loops; no network disable (could add env vars like HTTP_PROXY='').
    In production, use Docker for full sandbox.
    """
    original_dir = os.getcwd()
    try:
        os.chdir(root)
        # Collect unique test commands and main run command
        test_cmds = set()
        run_cmd = None
        languages = set(f["language"] for f in plan["files"])
        for file_info in plan["files"]:
            test_cmds.update(file_info["test_commands"])
            if file_info["run_command"]:
                run_cmd = file_info["run_command"]  # Assume one main entry point

        results = {"output": "", "error": ""}

        if "install" in plan["run_order"]:
            if os.path.exists("requirements.txt"):
                subprocess.run(["pip", "install", "-r", "requirements.txt"], check=True, capture_output=True, timeout=120)
            if os.path.exists("package.json"):
                subprocess.run(["npm", "install"], check=True, capture_output=True, timeout=120)

        success = True
        if "tests" in plan["run_order"] and test_cmds:
            for cmd in test_cmds:
                try:
                    out = subprocess.run(cmd.split(), check=True, capture_output=True, timeout=300)
                    results["output"] += out.stdout.decode() + "\n"
                except subprocess.TimeoutExpired:
                    success = False
                    results["error"] += "Test timeout.\n"
                except Exception as e:
                    success = False
                    results["error"] += str(e) + "\n"
                    results["output"] += getattr(e, 'stdout', b'').decode() + "\n"

        if success and "run" in plan["run_order"] and run_cmd:
            try:
                out = subprocess.run(run_cmd.split(), check=True, capture_output=True, timeout=300)
                results["output"] += out.stdout.decode() + "\n"
            except subprocess.TimeoutExpired:
                success = False
                results["error"] += "Run timeout.\n"
            except Exception as e:
                success = False
                results["error"] += str(e) + "\n"
                results["output"] += getattr(e, 'stdout', b'').decode() + "\n"

        return success, results
    finally:
        os.chdir(original_dir)