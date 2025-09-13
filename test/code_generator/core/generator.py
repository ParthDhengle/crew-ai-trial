import json
from .utils import llm_call, choose_model

def generate_files(plan):
    """
    Generates content for each file in the plan using targeted LLM calls.
    Uses file est_size to select cheap or strong model for cost optimization.
    Passes project context to ensure consistency across files.
    """
    generated = {}
    # Serialize plan as context to avoid repeated token usage; could cache if prompts repeat
    context = json.dumps(plan, indent=2)
    for file_info in plan["files"]:
        model = choose_model(file_info["est_size"])
        prompt = f"""
You are an expert {file_info["language"]} developer. Generate the complete code for this file based on the details below.

File path: {file_info["path"]}
Language: {file_info["language"]}
Purpose: {file_info["purpose"]}
Dependencies: {', '.join(file_info["dependencies"])}
Overall project plan (for context, ensure compatibility with other files):
{context}

- Include clear comments in the code.
- Handle errors gracefully where appropriate.
- If tests are needed, ensure the code is testable.

Output only strict JSON: {{"path": "{file_info["path"]}", "content": "the full file content here, escaped if needed"}}
No extra text outside the JSON.
        """
        response = llm_call(prompt, model=model, max_tokens=4000)  # Higher tokens for large files
        try:
            data = json.loads(response)
            if data["path"] != file_info["path"]:
                raise ValueError("Generated path mismatch.")
            generated[data["path"]] = data["content"]
        except json.JSONDecodeError:
            raise ValueError("Failed to parse generation response as JSON.")
    return generated