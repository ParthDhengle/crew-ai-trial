import json
import os
import traceback
import platform
import re
import json5
from typing import List, Dict, Any, Optional
from datetime import datetime
from crewai import Agent, Crew, Process, Task, LLM
from crewai.project import CrewBase, agent, crew, task
from litellm.exceptions import RateLimitError, APIError
from tools.file_manager_tool import FileManagerTool
from tools.operations_tool import OperationsTool
from tools.rag_tool import RagTool
from tools.long_term_rag_tool import LongTermRagTool
from chat_history import ChatHistory
from common_functions.Find_project_root import find_project_root
from memory_manager import MemoryManager
from firebase_client import get_user_profile, queue_operation, update_operation_status, save_chat_message
import inspect
import logging
import asyncio

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

PROJECT_ROOT = find_project_root()


@CrewBase
class AiAgent:
    """Cleaned AiAgent module: keeps core workflow, frontend connections and operation execution.

    Removed stray/duplicate helper code and kept stable, well-documented methods only.
    """

    agents: List[Agent]
    tasks: List[Task]

    def __init__(self):
        # Primary LLMs and fallbacks (models & keys expected to be in environment)
        self.classifier_llm = LLM(model=os.getenv("CLASSIFIER_MODEL", "gemini/gemini-1.5-flash-latest"), api_key=os.getenv("GEMINI_API_KEY1"))
        self.classifier_fallback1_llm = LLM(model=os.getenv("CLASSIFIER_FALLBACK1_MODEL", "openrouter/deepseek/deepseek-chat-v3.1:free"), api_key=os.getenv("OPENROUTER_API_KEY2"))
        self.classifier_fallback2_llm = LLM(model=os.getenv("CLASSIFIER_FALLBACK2_MODEL", "cohere/command-r-plus"), api_key=os.getenv("COHERE_API_KEY"))

        self.synthesizer_llm = LLM(model=os.getenv("SYNTH_MODEL", "openrouter/openai/gpt-oss-20b:free"), api_key=os.getenv("OPENROUTER_API_KEY1"))
        self.synthesizer_fallbacks = [
            LLM(model=os.getenv("SYNTH_FB1", "openrouter/deepseek/deepseek-chat-v3.1:free"), api_key=os.getenv("OPENROUTER_API_KEY2")),
            LLM(model=os.getenv("SYNTH_FB2", "gemini/gemini-1.5-flash-latest"), api_key=os.getenv("GEMINI_API_KEY4")),
        ]

        self.summarizer_llm = LLM(model=os.getenv("SUM_MODEL", "cohere/command-r-plus"), api_key=os.getenv("COHERE_API_KEY"))

        # Memory manager and RAG tools
        self.memory_manager = MemoryManager()
        self.rag_tool = RagTool()
        self.long_term_rag_tool = LongTermRagTool()

        # Initialize operation mapping
        self.operation_map = self._initialize_operation_map()

        # agent/task configs are expected to be provided via CrewBase
        super().__init__()

    # ----------------------- Helpers -----------------------
    def parse_json_with_retry(self, raw: str, retries: int = 2) -> Dict:
        """Try to parse JSON from LLM output with some cleanup retries.

        Returns a dict fallbacking to a safe direct-response dict on complete failure.
        """
        if not raw:
            return {"mode": "direct", "display_response": "Empty model response."}

        cleaned = raw
        for attempt in range(retries):
            # Strip common markdown/code fences
            cleaned = re.sub(r'```(?:json)?', '', cleaned)
            cleaned = cleaned.replace('```', '').replace('markdown', '').strip()
            # Attempt to load with json5 first (tolerant)
            try:
                return json5.loads(cleaned)
            except Exception:
                try:
                    return json.loads(cleaned)
                except Exception:
                    # Try to extract first JSON-looking block
                    m = re.search(r'\{.*\}', cleaned, re.DOTALL)
                    if m:
                        try:
                            return json.loads(m.group(0))
                        except Exception:
                            pass
            # If not successful, make a milder cleanup for next iteration
            cleaned = re.sub(r'[^\x00-\x7F]+', ' ', cleaned)

        logger.error("JSON parsing failed for model output (truncated): %s", (raw[:200] + '...') if raw else raw)
        return {"mode": "direct", "display_response": f"Could not parse model response. Raw: {raw[:200]}..."}

    def _initialize_operation_map(self) -> Dict[str, Any]:
        """Create operation map by checking OperationsTool and providing safe fallbacks.

        The OperationsTool implementation should expose either wrapper methods
        (e.g. _open_app_wrapper) or an operation_map dict with callables. If an operation
        is missing, a dummy fallback will be used so workflows won't crash.
        """
        ops = OperationsTool()
        operation_map: Dict[str, Any] = {}

        # Commonly used operations (extend as required by operations.json)
        candidates = [
            'custom_search', 'search_files', 'document_translate', 'document_summarize',
            'run_command', 'powerbi_generate_dashboard', 'open_app', 'searchMail', 'send_email'
        ]

        for name in candidates:
            wrapper_name = f'_{name}_wrapper'
            if hasattr(ops, wrapper_name):
                operation_map[name] = getattr(ops, wrapper_name)
            else:
                # If OperationsTool exposes a dict mapping, prefer it
                fallback = getattr(ops, 'operation_map', {}).get(name)
                if fallback:
                    operation_map[name] = fallback
                else:
                    # Final fallback: local wrapper using ops._run if available
                    operation_map[name] = self._create_operation_wrapper(name, ops)

        logger.info("Operation map initialized with %d operations.", len(operation_map))
        return operation_map

    def _create_operation_wrapper(self, op_name: str, ops_tool: OperationsTool):
        """Return a callable wrapper that calls ops_tool._run with a standard payload.

        The wrapper returns (success: bool, result: Any)
        """
        def wrapper(**kwargs):
            try:
                payload = [{'name': op_name, 'parameters': kwargs}]
                if hasattr(ops_tool, '_run'):
                    result = ops_tool._run(payload)
                else:
                    # If _run is not available, return a descriptive fallback
                    return True, f"Fallback executed for {op_name} with params: {kwargs}"

                # Normalize response: operations implementations are encouraged to prefix with ✅/❌
                if isinstance(result, str):
                    if result.startswith('✅'):
                        return True, result
                    if result.startswith('❌'):
                        return False, result
                return True, result

            except Exception as e:
                logger.exception("Operation wrapper for %s failed: %s", op_name, e)
                return False, f"Operation {op_name} failed: {str(e)}"

        return wrapper

    # ----------------------- File & Context helpers -----------------------
    def _process_file(self, file_path: Optional[str]) -> str:
        if not file_path:
            return ""
        if not os.path.exists(file_path):
            return ""

        ext = os.path.splitext(file_path)[1].lower()
        ft = FileManagerTool()
        try:
            content = ft._run(file_path)
            if ext == '.pdf':
                # avoid huge dumps
                return f"PDF Content Extracted: {content[:2000]}..."
            return content
        except Exception as e:
            logger.warning("File processing failed for %s: %s", file_path, e)
            return f"Error processing file: {str(e)}"

    # ----------------------- Crew agents & tasks -----------------------
    @agent
    def classifier(self) -> Agent:
        return Agent(config=self.agents_config['classifier'], llm=self.classifier_llm, verbose=False)

    @agent
    def synthesizer(self) -> Agent:
        return Agent(config=self.agents_config['synthesizer'], llm=self.synthesizer_llm, verbose=False)

    @agent
    def summarizer(self) -> Agent:
        return Agent(config=self.agents_config['summarizer'], llm=self.summarizer_llm, verbose=False)

    @task
    def classify_query(self) -> Task:
        return Task(config=self.tasks_config['classify_query'])

    @task
    def synthesize_response(self) -> Task:
        return Task(config=self.tasks_config['synthesize_response'])

    @task
    def summarize_history(self) -> Task:
        return Task(config=self.tasks_config['summarize_history'])

    # ----------------------- Task execution with fallbacks -----------------------
    async def _execute_task_with_fallbacks(self, agent: Agent, task: Task, fallbacks: Optional[List[LLM]] = None) -> Any:
        if fallbacks is None:
            fallbacks = []

        try:
            temp_crew = Crew(agents=[agent], tasks=[task], process=Process.sequential, verbose=False)
            result = temp_crew.kickoff()

            # Normalize result
            if hasattr(result, 'raw'):
                return result.raw
            if hasattr(result, 'result'):
                return result.result
            return str(result)

        except (RateLimitError, APIError) as e:
            status_code = getattr(e, 'status_code', None)
            # If non-retryable, re-raise
            if isinstance(e, APIError) and status_code not in (None, 429):
                logger.exception("Non-retryable APIError: %s", e)
                raise

            if not fallbacks:
                logger.error("No fallbacks left for agent %s", getattr(agent.llm, 'model', None))
                return f"Error: LLM request failed: {str(e)}"

            next_llm = fallbacks[0]
            logger.warning("Switching LLM to fallback %s due to error: %s", getattr(next_llm, 'model', None), e)
            agent.llm = next_llm
            return await self._execute_task_with_fallbacks(agent, task, fallbacks[1:])

        except Exception as e:
            logger.exception("Unexpected execution error: %s", e)
            return f"Task execution failed: {str(e)}"

    # ----------------------- Operations execution -----------------------
    async def perform_operations_async(self, operations: List[Dict[str, Any]], uid: str) -> str:
        """Execute a list of operations asynchronously and report results as a joined string."""
        logger.debug("Starting operations execution. Count=%d", len(operations) if operations else 0)

        if not operations:
            return "No operations to execute."

        lines = []
        for op in operations:
            if not isinstance(op, dict) or 'name' not in op:
                lines.append(f"Invalid operation format: {op}")
                continue

            name = op['name']
            params = op.get('parameters', {})

            if name not in self.operation_map:
                lines.append(f"Operation '{name}' not implemented.")
                continue

            # Prepare operation object for queueing
            operation_obj = {
                'name': name,
                'parameters': params,
                'uid': uid,
                'status': 'queued',
                'timestamp': datetime.now().isoformat()
            }

            try:
                # Queue operation (best-effort)
                try:
                    op_id = queue_operation(uid, operation_obj)
                    if inspect.iscoroutine(op_id):
                        op_id = await op_id
                except Exception as q_err:
                    logger.warning("Queue operation failed: %s", q_err)
                    op_id = f"local_{name}_{int(datetime.now().timestamp())}"

                # Update running status
                try:
                    update_operation_status(uid, op_id, 'running')
                except Exception:
                    logger.debug("Could not update running status for op %s", name)

                # Execute
                func = self.operation_map[name]
                logger.info("Executing operation %s with params: %s", name, params)

                if asyncio.iscoroutinefunction(func):
                    success, result = await func(**params)
                else:
                    success, result = func(**params)

                # Update final status (best-effort)
                try:
                    update_operation_status(uid, op_id, 'success' if success else 'failed', str(result))
                except Exception:
                    logger.debug("Could not update final status for op %s", name)

                lines.append(("✅" if success else "❌") + f" Operation '{name}': {result}")

            except Exception as e:
                logger.exception("Operation %s failed: %s", name, e)
                try:
                    if 'op_id' in locals():
                        update_operation_status(uid, op_id, 'failed', str(e))
                except Exception:
                    pass
                lines.append(f"❌ Operation '{name}' failed: {str(e)}")

        return "\n".join(lines) if lines else "All operations completed."

    
async def execute_agentic_background(self, operations: List[Dict[str, Any]], user_summarized_requirements: str, session_id: str, uid: str):
    """
    Background task to execute agentic operations and synthesize response.
    Saves the final assistant response to chat history.
    """
    try:
        logger.info(f"Starting background agentic execution for session {session_id}")
        
        # Execute operations
        op_results = await self.perform_operations_async(operations, uid)
        
        # Synthesize response
        synth_task = self.synthesize_response()
        synth_task.description = synth_task.description.format(
            user_summarized_requirements=user_summarized_requirements,
            op_results=op_results
        )
        synth_agent = self.synthesizer()
        
        synth_raw = await self._execute_task_with_fallbacks(
            synth_agent,
            synth_task,
            self.synthesizer_fallbacks
        )
        
        synth = self.parse_json_with_retry(synth_raw)
        final_response = synth.get('display_response', 'Synthesis completed.')
        
        # Extract and persist facts
        extracted_facts = synth.get('extracted_fact', [])
        if extracted_facts:
            self.memory_manager.update_long_term({
                'facts': extracted_facts if isinstance(extracted_facts, list) else [extracted_facts]
            })
        
        # Save assistant response to chat history
        timestamp = datetime.now().isoformat()
        save_result = save_chat_message(session_id, uid, "assistant", final_response, timestamp)
        if inspect.iscoroutine(save_result):
            await save_result
            
        logger.info(f"Background agentic execution completed for session {session_id}")
        
    except Exception as e:
        logger.exception(f"Background agentic execution failed for session {session_id}: {e}")
        
        # Save error response
        error_response = f"Background processing failed: {str(e)}"
        timestamp = datetime.now().isoformat()
        try:
            save_result = save_chat_message(session_id, uid, "assistant", error_response, timestamp)
            if inspect.iscoroutine(save_result):
                await save_result
        except Exception as save_err:
            logger.error(f"Failed to save error response: {save_err}")


    def perform_operations(self, operations: List[Dict[str, Any]]) -> str:
        """Synchronous convenience wrapper for perform_operations_async (not blocking here)."""
        # For backward compatibility, run sync operations by dispatching to operation_map
        if not operations:
            return "No operations to execute."

        results = []
        for op in operations:
            name = op.get('name')
            params = op.get('parameters', {})

            if name not in self.operation_map:
                results.append(f"Operation '{name}' not implemented.")
                continue

            try:
                func = self.operation_map[name]
                if asyncio.iscoroutinefunction(func):
                    # run coroutine synchronously via event loop
                    res = asyncio.get_event_loop().run_until_complete(func(**params))
                else:
                    res = func(**params)

                success, out = res if isinstance(res, tuple) else (True, res)
                results.append(f"Operation '{name}': {out}")

            except Exception as e:
                logger.exception("Sync operation %s failed: %s", name, e)
                results.append(f"Operation '{name}' failed: {str(e)}")

        return "\n".join(results)

    # ----------------------- Main workflow -----------------------
    async def get_classification(self, user_query: str, file_path: Optional[str] = None, session_id: Optional[str] = None) -> Dict:
        """Return classification dict for a user query. Keeps integration with chat history and available operations."""
        try:
            user_query = (user_query or "").strip()
            if not user_query:
                return {"mode": "direct", "display_response": "No query provided."}

            history = ChatHistory.load_history(session_id)
            user_profile = self.memory_manager.get_user_profile()
            file_content = self._process_file(file_path)

            # Load available operations for context (best-effort)
            try:
                ft = FileManagerTool()
                ops_raw = ft._run(os.path.join(PROJECT_ROOT, 'knowledge', 'operations.json'))
                m = re.search(r'\{.*\}', ops_raw, re.DOTALL)
                ops_json = json.loads(m.group(0)) if m else {}
                available_operations = ops_json.get('operations', [])
            except Exception:
                available_operations = []

            available_ops_info = "\n".join([
                f"{op.get('name')}: {op.get('description','')} | Required: {', '.join(op.get('required_parameters',[]))}"
                for op in available_operations
            ])

            full_history = json.dumps(history)
            if len(full_history) > 2000:
                full_history = f"Summary: {ChatHistory.summarize(history)}"

            inputs = {
                'user_query': user_query,
                'file_content': file_content,
                'full_history': full_history,
                'available_ops_info': available_ops_info,
                'user_profile': json.dumps(user_profile),
                'os_info': f"{platform.system()} {platform.release()}"
            }

            classify_task = self.classify_query()
            classify_task.description = classify_task.description.format(**inputs)
            classify_agent = self.classifier()

            classification_raw = await self._execute_task_with_fallbacks(
                classify_agent,
                classify_task,
                [self.classifier_fallback1_llm, self.classifier_fallback2_llm]
            )

            classification = self.parse_json_with_retry(classification_raw)
            return classification

        except Exception as e:
            logger.exception("Error in get_classification: %s", e)
            return {"mode": "direct", "display_response": f"Classification error: {str(e)}"}

    async def run_workflow(self, user_query: str, file_path: Optional[str] = None, session_id: Optional[str] = None, uid: Optional[str] = None) -> Dict[str, Any]:
        """Core end-to-end workflow used by the frontend.

        Returns a dict with display_response and mode. Keeps chat history, executes operations
        when classification returns agentic plan, and synthesizes final assistant response.
        """
        try:
            user_query = (user_query or "").strip()
            if not user_query:
                return {"display_response": "No query provided.", "mode": "direct"}

            uid = uid or "anonymous"

            history = ChatHistory.load_history(session_id)
            user_profile = self.memory_manager.get_user_profile()
            file_content = self._process_file(file_path)

            classification = await self.get_classification(user_query, file_path, session_id)
            mode = classification.get('mode', 'direct')

            if mode == 'direct':
                final_response = classification.get('display_response', 'No response generated.')

            else:  # agentic
                operations = classification.get('operations', [])
                if not isinstance(operations, list) or not all(isinstance(op, dict) and 'name' in op for op in operations):
                    final_response = "Invalid operations plan generated. Please rephrase your query."
                    mode = 'direct'
                else:
                    user_summarized_requirements = classification.get('user_summarized_requirements', 'User intent unclear.')

                    op_results = await self.perform_operations_async(operations, uid)

                    synth_task = self.synthesize_response()
                    synth_task.description = synth_task.description.format(
                        user_summarized_requirements=user_summarized_requirements,
                        op_results=op_results
                    )
                    synth_agent = self.synthesizer()

                    synth_raw = await self._execute_task_with_fallbacks(
                        synth_agent,
                        synth_task,
                        self.synthesizer_fallbacks
                    )

                    synth = self.parse_json_with_retry(synth_raw)
                    final_response = synth.get('display_response', 'Synthesis failed.')

                    # Persist extracted facts if present
                    extracted_facts = synth.get('extracted_fact', [])
                    if extracted_facts:
                        self.memory_manager.update_long_term({
                            'facts': extracted_facts if isinstance(extracted_facts, list) else [extracted_facts]
                        })

            # Save history and return
            history.append({"role": "user", "content": user_query + (f" [File: {file_path}]" if file_path else "")})
            history.append({"role": "assistant", "content": final_response})
            ChatHistory.save_history(history, session_id)

            return {"display_response": final_response, "mode": mode}

        except Exception as e:
            logger.exception("Error in run_workflow: %s", e)
            return {"display_response": f"Workflow error: {str(e)}", "mode": "error"}

    @crew
    def crew(self) -> Crew:
        return Crew(agents=self.agents, tasks=self.tasks, process=Process.sequential, verbose=True)
