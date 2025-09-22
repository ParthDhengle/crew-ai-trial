import json
import os
import traceback
import platform
import re
import json5
from typing import List, Dict, Any
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
from typing import Optional
import inspect
import logging
import asyncio

# configure logging once in module
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

PROJECT_ROOT = find_project_root()
MEMORY_DIR = os.path.join(PROJECT_ROOT, "knowledge", "memory")

@CrewBase
class AiAgent:
    agents: List[Agent]
    tasks: List[Task]
    
    def __init__(self):
        # LLMs with fallbacks
        self.classifier_llm = LLM(model="groq/llama-3.3-70b-versatile", api_key=os.getenv("GROQ_API_KEY1"))
        self.classifier_fallback1_llm = LLM(model="gemini/gemini-1.5-flash-latest", api_key=os.getenv("GEMINI_API_KEY2"))
        self.classifier_fallback2_llm = LLM(model="openrouter/deepseek/deepseek-chat-v3.1:free", api_key=os.getenv("OPENROUTER_API_KEY2"))
       
        self.synthesizer_llm = LLM(model="openrouter/openai/gpt-oss-120b:free", api_key=os.getenv("OPENROUTER_API_KEY4"))
        self.synthesizer_fallback1_llm = LLM(model="openrouter/deepseek/deepseek-chat-v3.1:free", api_key=os.getenv("OPENROUTER_API_KEY2"))
        self.synthesizer_fallback2_llm = LLM(model="gemini/gemini-1.5-flash-latest", api_key=os.getenv("GEMINI_API_KEY4"))
       
        self.summarizer_llm = LLM(model="cohere/command-r-plus", api_key=os.getenv("COHERE_API_KEY"))
        self.summarizer_fallback1_llm = LLM(model="openrouter/openai/gpt-oss-20b:free", api_key=os.getenv("OPENROUTER_API_KEY1"))
        self.summarizer_fallback2_llm = LLM(model="gemini/gemini-1.5-flash-latest", api_key=os.getenv("GEMINI_API_KEY1"))
        
        self.memory_manager = MemoryManager()
        
        # Initialize operation_map - ADD THIS IF MISSING
        self.operation_map = self._initialize_operation_map()
        
        super().__init__()
    
    def _initialize_operation_map(self):
        """Initialize the operation mapping - customize based on your operations"""
        ops_tool = OperationsTool()
        return {
            'custom_search': getattr(ops_tool, 'custom_search', self._dummy_operation),
            'search_files': getattr(ops_tool, 'search_files', self._dummy_operation),
            'document_translate': getattr(ops_tool, 'document_translate', self._dummy_operation),
            'run_command': getattr(ops_tool, 'run_command', self._dummy_operation),
            # Add other operations as needed
        }
    
    def _dummy_operation(self, **kwargs):
        """Fallback for missing operations"""
        return True, f"Operation executed with params: {kwargs}"
    
    def parse_json_with_retry(self, raw: str, retries: int = 1) -> Dict:
        """Parse JSON with cleanup and retry logic"""
        for _ in range(retries):
            cleaned = re.sub(r'```json|```|markdown', '', raw).strip()
            try:
                return json5.loads(cleaned)
            except Exception as e:
                logger.warning(f"JSON parse attempt failed: {e}")
        
        # Fallback
        logger.error(f"JSON parsing completely failed for: {raw[:100]}...")
        return {'mode': 'direct', 'display_response': f"Classification failed: {raw[:100]}... Please rephrase."}
    
    async def get_classification(self, user_query: str, file_path: str = None, session_id: str = None) -> Dict:
        """Extract classification logic for API to call separately"""
        try:
            user_query = user_query.strip()
            if not user_query:
                return {"mode": "direct", "display_response": "No query provided."}
            
            # Assemble inputs
            history = ChatHistory.load_history(session_id)
            user_profile = self.memory_manager.get_user_profile()
            file_content = self._process_file(file_path)
            
            # Load operations from json
            file_tool = FileManagerTool()
            ops_path = os.path.join(PROJECT_ROOT, 'knowledge', 'operations.json')
            available_operations_raw = file_tool._run(ops_path)
            
            # Robust JSON extraction
            json_match = re.search(r'\{.*\}', available_operations_raw, re.DOTALL)
            if json_match:
                available_operations_content = json_match.group(0)
            else:
                available_operations_content = "{}"
            
            try:
                available_operations = json.loads(available_operations_content.strip()).get("operations", [])
            except json.JSONDecodeError:
                logger.warning("Invalid operations JSON. Using empty list.")
                available_operations = []
            
            available_ops_info = "\\n".join([
                f"{op['name']}: {op['description']} | Required params: {', '.join(op['required_parameters'])} | Optional params: {', '.join(op.get('optional_parameters', []))}" 
                for op in available_operations
            ])
            
            full_history = json.dumps(history)
            if len(full_history) > 2000:
                history_summary = ChatHistory.summarize(history)
                full_history = f"Summary: {history_summary}"
            
            os_info = f"{platform.system()} {platform.release()}"
            
            inputs = {
                'user_query': user_query,
                'file_content': file_content,
                'full_history': full_history,
                'available_ops_info': available_ops_info,
                'user_profile': json.dumps(user_profile),
                'os_info': os_info
            }
            
            # Execute classification task
            classify_task = self.classify_query()
            classify_task.description = classify_task.description.format(**inputs)
            classify_agent = self.classifier()
            
            classification_raw = await self._execute_task_with_fallbacks(
                classify_agent, classify_task, [self.classifier_fallback1_llm, self.classifier_fallback2_llm]
            )
            
            classification = self.parse_json_with_retry(classification_raw)
            return classification
            
        except Exception as e:
            logger.error(f"Error in get_classification: {e}")
            traceback.print_exc()
            return {"mode": "direct", "display_response": f"Classification error: {str(e)}"}
    
    # === Agents ===
    @agent
    def classifier(self) -> Agent:
        return Agent(config=self.agents_config['classifier'], llm=self.classifier_llm, verbose=True)
    
    @agent
    def synthesizer(self) -> Agent:
        return Agent(config=self.agents_config['synthesizer'], llm=self.synthesizer_llm, verbose=True)
    
    @agent
    def summarizer(self) -> Agent:
        return Agent(config=self.agents_config['summarizer'], llm=self.summarizer_llm, verbose=True)
    
    # === Tasks ===
    @task
    def classify_query(self) -> Task:
        return Task(config=self.tasks_config['classify_query'])
    
    @task
    def synthesize_response(self) -> Task:
        return Task(config=self.tasks_config['synthesize_response'])
    
    @task
    def summarize_history(self) -> Task:
        return Task(config=self.tasks_config['summarize_history'])
    
    # === Internal Execution Helpers ===
    async def _execute_task_with_fallbacks(self, agent, task, fallbacks: Optional[List[LLM]] = None):
        """Execute task with fallback LLMs on failure"""
        if fallbacks is None:
            fallbacks = []

        try:
            # CRITICAL FIX: Use CrewAI's proper task execution
            # Instead of agent.execute_task, use the crew execution pattern
            temp_crew = Crew(
                agents=[agent],
                tasks=[task],
                process=Process.sequential,
                verbose=False
            )
            
            # Execute the crew and get result
            result = temp_crew.kickoff()
            
            # Handle different result types
            if hasattr(result, 'raw'):
                return result.raw
            elif hasattr(result, 'result'):
                return result.result
            else:
                return str(result)
                
        except (RateLimitError, APIError) as e:
            # Handle API errors with fallbacks
            status_code = getattr(e, "status_code", None)
            if isinstance(e, APIError) and status_code not in (None, 429):
                logger.exception("Non-retryable APIError from model %s: %s", getattr(agent.llm, "model", None), e)
                raise

            if not fallbacks:
                logger.error("Exhausted fallbacks for %s. Returning error string.", getattr(agent.llm, "model", None))
                return "Error: LLM request failed. Please try again later."

            # Switch to next fallback LLM and retry
            next_llm = fallbacks[0]
            logger.warning("RateLimit/API error with %s. Switching to fallback %s and retrying.", 
                          getattr(agent.llm, "model", None), getattr(next_llm, "model", None))
            agent.llm = next_llm
            return await self._execute_task_with_fallbacks(agent, task, fallbacks[1:])
            
        except Exception as e:
            logger.exception("Unexpected error in _execute_task_with_fallbacks: %s", e)
            return f"Task execution failed: {str(e)}"
    
    def _process_file(self, file_path: str) -> str:
        """Extract text from file"""
        if not file_path or not os.path.exists(file_path):
            return ""
        
        ext = os.path.splitext(file_path)[1].lower()
        file_tool = FileManagerTool()
        
        try:
            if ext in ['.txt', '.doc', '.ppt']:
                return file_tool._run(file_path)
            elif ext == '.pdf':
                content = file_tool._run(file_path)
                return f"PDF Content Extracted: {content[:2000]}..."
            else:
                return f"Unsupported file type: {ext}. Only txt, pdf, doc, ppt supported."
        except Exception as e:
            logger.error(f"File processing error: {e}")
            return f"Error processing file: {str(e)}"
    
    async def execute_agentic_background(self, operations: List[Dict], user_summarized_requirements: str, session_id: str, uid: str):
        """Background: Execute ops, synthesize, save response"""
        try:
            # Execute operations
            op_results = await self.perform_operations_async(operations)
            
            # Synthesize response
            synth_task = self.synthesize_response()
            synth_task.description = synth_task.description.format(
                user_summarized_requirements=user_summarized_requirements,
                op_results=op_results
            )
            synth_agent = self.synthesizer()
            
            synth_raw = await self._execute_task_with_fallbacks(
                synth_agent, synth_task, [self.synthesizer_fallback1_llm, self.synthesizer_fallback2_llm]
            )
            
            synth = self.parse_json_with_retry(synth_raw)
            final_response = synth.get('display_response', 'Synthesis failed.')
            
            # Extract and add facts to KB
            extracted_facts = synth.get('extracted_fact', [])
            if extracted_facts:
                self.memory_manager.update_long_term({
                    'facts': extracted_facts if isinstance(extracted_facts, list) else [extracted_facts]
                })
                logger.info(f"Added {len(extracted_facts)} facts to KB.")
            
            # Save assistant response
            await save_chat_message(session_id, uid, "assistant", final_response, datetime.now().isoformat())
            
        except Exception as e:
            logger.error(f"Error in execute_agentic_background: {e}")
            error_response = f"Background execution failed: {str(e)}"
            await save_chat_message(session_id, uid, "assistant", error_response, datetime.now().isoformat())
    
    async def perform_operations_async(self, operations: List[Dict[str, Any]]) -> str:
        """Execute list of operations sequentially (async version)"""
        if not operations:
            return "No operations to execute."
        
        lines = []
        for op in operations:
            name = op.get('name')
            params = op.get('parameters', {})
            
            if name not in self.operation_map:
                lines.append(f"Operation '{name}' not implemented.")
                continue
            
            # Queue and update status
            op_id = queue_operation(name, params)
            update_operation_status(op_id, 'running')
            
            try:
                func = self.operation_map[name]
                # Execute operation (make it async-safe)
                if asyncio.iscoroutinefunction(func):
                    success, result = await func(**params)
                else:
                    success, result = func(**params)
                    
                update_operation_status(op_id, 'success' if success else 'failed', result)
                lines.append(f"Operation '{name}': {result}")
                
            except Exception as e:
                error_msg = str(e)
                update_operation_status(op_id, 'failed', error_msg)
                lines.append(f"Operation '{name}' failed: {error_msg}")
                logger.error(f"Operation {name} failed: {e}")
        
        return "\n".join(lines) if lines else "All operations completed."
    
    def perform_operations(self, operations: List[Dict[str, Any]]) -> str:
        """Synchronous version of perform_operations for backward compatibility"""
        if not operations:
            return "No operations to execute."
        
        lines = []
        for op in operations:
            name = op.get('name')
            params = op.get('parameters', {})
            
            if name not in self.operation_map:
                lines.append(f"Operation '{name}' not implemented.")
                continue
            
            # Queue and update status
            op_id = queue_operation(name, params)
            update_operation_status(op_id, 'running')
            
            try:
                func = self.operation_map[name]
                success, result = func(**params)
                update_operation_status(op_id, 'success' if success else 'failed', result)
                lines.append(f"Operation '{name}': {result}")
                
            except Exception as e:
                error_msg = str(e)
                update_operation_status(op_id, 'failed', error_msg)
                lines.append(f"Operation '{name}' failed: {error_msg}")
        
        return "\n".join(lines) if lines else "All operations completed."
    
    async def run_workflow(self, user_query: str, file_path: str = None, session_id: str = None):
        """Optimized workflow execution"""
        try:
            # Input validation
            user_query = user_query.strip()
            if not user_query:
                return {"display_response": "No query provided.", "mode": "direct"}
           
            # Load context
            history = ChatHistory.load_history(session_id)
            user_profile = self.memory_manager.get_user_profile()
            file_content = self._process_file(file_path)
           
            # Load operations
            file_tool = FileManagerTool()
            ops_path = os.path.join(PROJECT_ROOT, 'knowledge', 'operations.json')
            available_operations_raw = file_tool._run(ops_path)
            
            json_match = re.search(r'\{.*\}', available_operations_raw, re.DOTALL)
            if json_match:
                available_operations_content = json_match.group(0)
            else:
                available_operations_content = "{}"
            
            try:
                available_operations = json.loads(available_operations_content.strip()).get("operations", [])
            except json.JSONDecodeError:
                logger.warning("Invalid operations JSON. Using empty list.")
                available_operations = []
           
            available_ops_info = "\n".join([
                f"{op['name']}: {op['description']} | Required params: {', '.join(op['required_parameters'])} | Optional params: {', '.join(op.get('optional_parameters', []))}" 
                for op in available_operations
            ])
            
            # Prepare inputs
            full_history = json.dumps(history)
            if len(full_history) > 2000:
                history_summary = ChatHistory.summarize(history)
                full_history = f"Summary: {history_summary}"
            
            os_info = f"{platform.system()} {platform.release()}"
            inputs = {
                'user_query': user_query,
                'file_content': file_content,
                'full_history': full_history,
                'available_ops_info': available_ops_info,
                'user_profile': json.dumps(user_profile),
                'os_info': os_info
            }
            
            # Classification
            classify_task = self.classify_query()
            classify_task.description = classify_task.description.format(**inputs)
            classify_agent = self.classifier()
            
            classification_raw = await self._execute_task_with_fallbacks(
                classify_agent, classify_task, [self.classifier_fallback1_llm, self.classifier_fallback2_llm]
            )
           
            classification = self.parse_json_with_retry(classification_raw)
           
            # Mode routing
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
                   
                    # Execute operations
                    op_results = await self.perform_operations_async(operations)
                   
                    # Synthesize response
                    synth_task = self.synthesize_response()
                    synth_task.description = synth_task.description.format(
                        user_summarized_requirements=user_summarized_requirements,
                        op_results=op_results
                    )
                    synth_agent = self.synthesizer()
                    
                    synth_raw = await self._execute_task_with_fallbacks(
                        synth_agent, synth_task, [self.synthesizer_fallback1_llm, self.synthesizer_fallback2_llm]
                    )
                    
                    synth = self.parse_json_with_retry(synth_raw)
                    final_response = synth.get('display_response', 'Synthesis failed.')
                   
                    # Extract and add to KB
                    extracted_facts = synth.get('extracted_fact', [])
                    if extracted_facts:
                        self.memory_manager.update_long_term({
                            'facts': extracted_facts if isinstance(extracted_facts, list) else [extracted_facts]
                        })
                        logger.info(f"Added {len(extracted_facts)} facts to KB.")
           
            # Save history
            history.append({"role": "user", "content": user_query + (f" [File: {file_path}]" if file_path else "")})
            history.append({"role": "assistant", "content": final_response})
            ChatHistory.save_history(history, session_id)
           
            # Periodic narrative
            if len(history) % 10 == 0:
                try:
                    narrative = self.memory_manager.create_narrative_summary(json.dumps(history[-5:]))
                except Exception as e:
                    logger.warning(f"Narrative summary failed: {e}")
           
            return {"display_response": final_response, "mode": mode}
            
        except Exception as e:
            logger.error(f"Error in run_workflow: {e}")
            traceback.print_exc()
            return {"display_response": f"Workflow error: {str(e)}", "mode": "error"}
    
    @crew
    def crew(self) -> Crew:
        return Crew(agents=self.agents, tasks=self.tasks, process=Process.sequential, verbose=True)