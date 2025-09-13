# AI Agentic Workflow Project

## Overview

This project implements an efficient AI agentic workflow for processing user queries, inspired by systems like Grok, ChatGPT, and Gemini. The goal is to handle both simple conversational queries ("direct" mode) and complex tasks requiring tools, reasoning, or external operations ("agentic" mode) while optimizing for token usage and staying within Gemini's free-tier limits (approximately 1M-2M token context window and 60 requests per minute).
The workflow uses a multi-agent architecture with early classification to route queries, history summarization to reduce token bloat, and staged analysis/planning/execution for agentic tasks. It integrates user preferences for personalization and a directory of available operations (e.g., web searches, code execution) for task handling.

### Key features:

- Efficiency: Minimizes LLM calls (3 for direct paths, 5-7 for agentic) and uses concise prompts (~200-250 tokens).
- Models: Primarily Gemini 1.5 Flash for lightweight tasks; DeepSeek R1 (or similar) for deeper reasoning in analysis.
- Token Management: Summarizes long chat histories to ~100-300 tokens; truncates if needed.
- Error Handling: Includes plan refinement for error detection and user clarification prompts if ambiguities arise.

This README explains the workflow steps, components, and setup to help team members understand and contribute.

## Project Structure

- src/: Core code files (e.g., workflow.py for main logic, prompts.py for system prompts).
- operations/: Directory containing available operations/tools (e.g., web_search.py, code_exec.py). Define your custom operations here.
- prompts/: Templates for system prompts (e.g., summarizer_prompt.txt, classifier_prompt.txt).
- config/: Settings like API keys, user preferences JSON, model selections.
- tests/: Unit tests for each step (e.g., test_classifier.py).
- docs/: Additional diagrams or examples (e.g., workflow_diagram.png).

## Workflow Overview

The workflow processes a user query as follows:

- Receive user query.
  \*Summarize chat history (if long) to compress context.
- Classify the query as "direct" (simple response) or "agentic" (needs tools/reasoning).
- If direct: Generate response directly.
- If agentic: Analyze and plan sub-tasks, refine for errors, execute operations, synthesize final response.

### LLM Call Breakdown:

- Direct Path: 3 calls (summarize + classify + generate).
- Agentic Path: 5-7 calls (summarize + classify + analyze/plan + refine + 1-2 for synthesis; plus any LLM-involved operations).

This branching minimizes unnecessary computation. Execution is sequential by default but can be parallelized for independent operations.

## Detailed Workflow Steps

1. User Query Input

Input: Raw user query (string).
Purpose: Entry point for the system.
Notes: Query is passed unchanged to subsequent steps.

2. Summarize Chat History

Input: Full chat history (list of messages).
Process: Use a lightweight LLM (e.g., Gemini 1.5 Flash) with a prompt like: "Summarize this chat history concisely, focusing on key topics, user intents, and recent exchanges."
Output: Condensed summary (~100-300 tokens).
Purpose: Prevents token overflow from long histories; Gemini handles internal summarization, but explicit summarization ensures efficiency.
LLM Call: 1 (lightweight).
Edge Cases: If history is short (<500 tokens), skip summarization.

3. Classifier/Router

Input: User query + summarized history + user preferences + classifier system prompt.
Process: LLM classifies the query. Prompt example: "Classify if this query needs a direct response or agentic handling (tools/reasoning). Output JSON: {'mode': 'direct' or 'agentic', 'reason': '...'}."
Output: JSON with mode and reason.
Purpose: Routes to efficient path; e.g., "What's the weather?" → agentic (needs web search); "Hi!" → direct.
LLM Call: 1.
Notes: Keep prompt <200 tokens for speed.

4. Direct Response Generation (If Classified as "Direct")

Input: User query + summarized history + user preferences + response system prompt.
Process: LLM generates a helpful response. Prompt example: "Generate a coherent, helpful response based on the query and context."
Output: Final response string sent to user.
Purpose: Quick exit for simple queries.
LLM Call: 1.
End of Path: Workflow stops here.

5. Query Analysis and Plan Generation (If Classified as "Agentic")

Input: User query + summarized history + user preferences + list of available operations + analysis system prompt.
Process: Use a deeper-reasoning LLM (e.g., DeepSeek R1). Prompt example: "Analyze the query: Break into sub-tasks, identify needed operations/tools, flag ambiguities/errors. Output JSON: {'subtasks': [...], 'operations': [{'name': '...', 'params': '...'}], 'potential_issues': '...'}."
Output: JSON plan with subtasks, operations, and issues.
Purpose: Decomposes complex queries (e.g., "Plan a trip to Paris") into actionable steps using operations from your directory.
LLM Call: 1 (deeper model for chain-of-thought).

6. Plan Refinement/Validation

Input: Output from Step 5 + available operations + refinement system prompt.
Process: Lightweight LLM reviews. Prompt example: "Review this plan for errors, feasibility, and completeness. Fix issues or flag if unresolvable. Output refined JSON plan or {'error': 'Need user clarification'}."
Output: Refined JSON plan or error flag.
Purpose: Catches mistakes before execution; if error (e.g., ambiguous query), prompt user for clarification and restart workflow.
LLM Call: 1.
Notes: Adds reflection for reliability; retry loop if minor issues.

7. Plan Execution

Input: Refined plan from Step 6.
Process: Execute each operation sequentially (or parallel for independents):

Invoke operations from the directory (e.g., API calls for web search).
Collect outputs/logs.
If an operation fails, retry once or log error.

Output: List of operation results.
Purpose: Performs actual tasks (e.g., fetch data, run code).
LLM Calls: 0-2 (only if operations require LLM guidance).
Notes: Operations are custom; ensure they're non-LLM where possible to save calls.

8. Final Response Synthesis

Input: User query + summarized history + user preferences + all operation outputs + synthesis system prompt.
Process: LLM aggregates results. Prompt example: "Synthesize these results into a coherent response. Include key outputs and explanations."
Output: Final response string sent to user.
Purpose: Compiles everything into a user-friendly answer.
LLM Call: 1-2 (one for draft, optional second for polishing).
End of Path: Workflow completes.

## Components and Agents

Summarizer: Handles history compression (Step 2).
Router/Classifier: Decides path (Step 3).
Analyzer/Planner: Decomposes and plans (Step 5).
Refiner: Validates and fixes plans (Step 6).
Executor: Runs operations (Step 7).
Synthesizer: Generates final output (Steps 4 or 8).

These align with agentic patterns (e.g., ReAct: Reason + Act + Reflect).

## Token Optimization and Limits

Use concise prompts and summaries.
Prefer Gemini 1.5 Flash for non-reasoning steps.
Dynamic truncation: If inputs exceed 80% of context window, shorten history further.
Batch operations if possible to reduce API requests.

## Dependencies

LLMs: Google Gemini API (free tier), DeepSeek API (for deeper analysis).
Languages: Python 3+.
Libraries: google-generativeai (for Gemini), requests (for APIs), json (for parsing).
Operations Directory: Populate with your tools (e.g., integrate APIs like weather, search).

## Setup and Running

Clone repo: git clone <repo-url>.
Install deps: pip install -r requirements.txt.
Set env vars: Add GEMINI_API_KEY, DEEPSEEK_API_KEY in .env.
Configure user preferences in config/preferences.json (e.g., {"style": "concise", "preferred_tools": ["web_search"]}).
Run: python src/workflow.py --query "Your test query" --history "path/to/history.json".

For testing: Use pytest tests/ to validate each step.

## Future Plans

Add more agents (e.g., full Planner, Executor, Reflector as discussed).
Parallel execution for faster agentic paths.
Integration with additional models (e.g., Grok API).
Monitoring: Track token usage and rate limits in real-time.
UI: Web/app interface for easier testing.

\knowledge\memory> git update-index --assume-unchanged long_term/extracted_facts.json long_term/projects_and_tasks.json narrative/summaries.json narrative/mood_logs.json

knowledge\memory> Remove-Item
-Recurse -Force short_term\*

## Firebase Integration

This project now uses Firebase Firestore for metadata (user profiles, tasks, projects, etc.) and Firebase Storage for files (snapshots, uploads). Local FAISS is used for vector search, with metadata stored in Firestore.

### Setup Steps

1. **Install Dependencies**:
   ```bash
   pip install firebase-admin
   langchain_huggingface
   ```
