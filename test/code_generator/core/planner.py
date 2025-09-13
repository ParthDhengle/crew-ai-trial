import json
from .utils import llm_call

def plan_project(user_query):
    """
    Uses a cheap LLM model to analyze the user query and generate a structured JSON project plan.
    This plan dictates the project's structure, files, dependencies, and execution commands.
    """
    # Define the expected JSON schema for the plan in the prompt
    schema = """
{
  "project_name": "string",
  "complexity": "tiny|small|medium|large",
  "root_folder": "string",
  "files": [
    {
      "path": "src/main.py",
      "language": "python",
      "purpose": "project entry point",
      "run_command": "python src/main.py",
      "test_commands": ["pytest tests"],
      "dependencies": ["flask==2.2.2"],
      "est_size": "small"
    }
  ],
  "run_order": ["install", "tests", "run"],
  "guidance": "short, human-readable instructions"
}
    """
    prompt = f"""
You are an expert project planner. Analyze the user's natural language request: "{user_query}"

Based on the request, create a detailed project plan in strict JSON format matching this schema:
{schema}

- project_name: A concise name for the project.
- complexity: Estimate overall project scale (tiny for single-file, large for multi-module apps).
- root_folder: The base directory name for the project (e.g., "my_flask_app").
- files: List of all required files with relative paths from root.
  - path: Relative file path.
  - language: Programming language (e.g., "python", "javascript").
  - purpose: Brief description of the file's role.
  - run_command: Command to run this file if it's an entry point (optional, usually one per project).
  - test_commands: List of test commands for this file (e.g., ["pytest tests/test_main.py"]).
  - dependencies: List of required packages (e.g., ["flask==2.2.2"] for Python, ["express@4.17.1"] for JS).
  - est_size: Estimate file complexity ("tiny", "small", "medium", "large") to choose LLM model.
- run_order: Sequence of operations: always ["install", "tests", "run"].
- guidance: User instructions for running the project, including setup and commands.

Output only the JSON, no extra text.
    """
    # Use cheap model for planning to save costs
    response = llm_call(prompt, model="gpt-3.5-turbo", max_tokens=1500)
    try:
        plan = json.loads(response)
        return plan
    except json.JSONDecodeError:
        raise ValueError("Failed to parse planning response as JSON.")