import json
from .utils import llm_call

def debug_project(error, failing_files, plan):
    """
    Uses a strong LLM model to analyze errors and suggest targeted edits.
    Sends minimal context (error + file contents) to keep token usage low.
    In future, could send diffs instead of full contents for efficiency.
    """
    # Prepare file contents string; to optimize, could summarize or select relevant files based on error
    files_str = "\n\n".join([f"File: {path}\n{content}" for path, content in failing_files.items()])
    context = json.dumps(plan, indent=2)
    prompt = f"""
You are an expert debugger. The generated project failed with this error/output:

{error}

Current file contents to debug/fix:
{files_str}

Overall project plan (for reference):
{context}

- Identify the root cause.
- Suggest minimal changes to fix the issue.
- Only edit necessary files; provide full new content for each edited file.

Output strict JSON:
{{
  "edits": [
    {{"path": "relative/path.py", "new_content": "full fixed code here"}}
  ],
  "explanation": "brief summary of changes and why"
}}
No extra text.
    """
    # Use strong model for complex debugging
    response = llm_call(prompt, model="gpt-4", max_tokens=4000)
    try:
        edits = json.loads(response)
        return edits
    except json.JSONDecodeError:
        raise ValueError("Failed to parse debug response as JSON.")