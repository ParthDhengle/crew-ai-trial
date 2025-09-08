import json
import os
import traceback
from typing import List
from datetime import date
import json5
import re
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

PROJECT_ROOT = find_project_root()
MEMORY_DIR = os.path.join(PROJECT_ROOT, 'knowledge', 'memory')

@CrewBase
class AiAgent():
    agents: List[Agent]
    tasks: List[Task]
    
    def __init__(self):
        # Define individual LLMs for each agent to avoid rate limits
        self.summarizer_llm = LLM(
            model="cohere/command-r-plus",
            api_key=os.getenv("COHERE_API_KEY")
        )
        self.summarizer_fallback1_llm = LLM(
            model="openrouter/openai/gpt-oss-20b:free",
            api_key=os.getenv("OPENROUTER_API_KEY1")
        )
        self.summarizer_fallback2_llm = LLM(
            model="gemini/gemini-1.5-flash-latest",
            api_key=os.getenv("GEMINI_API_KEY1")
        )
        
        # Classifier - Upgraded to better LLM
        self.classifier_llm = LLM(
            model="groq/llama-3.3-70b-versatile",
            api_key=os.getenv("GROQ_API_KEY1")
        )
        self.classifier_fallback1_llm = LLM(
            model="gemini/gemini-1.5-flash-latest",
            api_key=os.getenv("GEMINI_API_KEY2")
        )
        self.classifier_fallback2_llm = LLM(
            model="openrouter/deepseek/deepseek-chat-v3.1:free",
            api_key=os.getenv("OPENROUTER_API_KEY2")
        )
        
        # Direct Responder
        self.direct_responder_llm = LLM(
            model="openrouter/openai/gpt-oss-20b:free",
            api_key=os.getenv("OPENROUTER_API_KEY3")
        )
        self.direct_responder_fallback1_llm = LLM(
            model="openrouter/openai/gpt-oss-120b:free",
            api_key=os.getenv("OPENROUTER_API_KEY4")
        )
        self.direct_responder_fallback2_llm = LLM(
            model="gemini/gemini-1.5-flash-latest",
            api_key=os.getenv("GEMINI_API_KEY3")
        )
        
        # Planner (renamed from analyzer2)
        self.planner_llm = LLM(
            model="gemini/gemini-1.5-flash-latest",
            api_key=os.getenv("GEMINI_API_KEY2")
        )
        self.planner_fallback1_llm = LLM(
            model="openrouter/deepseek/deepseek-chat-v3.1:free",
            api_key=os.getenv("OPENROUTER_API_KEY3")
        )
        self.planner_fallback2_llm = LLM(
            model="groq/llama-3.1-8b-instant",
            api_key=os.getenv("GROQ_API_KEY3")
        )
        
        # Synthesizer
        self.synthesizer_llm = LLM(
            model="openrouter/openai/gpt-oss-120b:free",
            api_key=os.getenv("OPENROUTER_API_KEY4")
        )
        self.synthesizer_fallback1_llm = LLM(
            model="openrouter/deepseek/deepseek-chat-v3.1:free",
            api_key=os.getenv("OPENROUTER_API_KEY2")
        )
        self.synthesizer_fallback2_llm = LLM(
            model="gemini/gemini-1.5-flash-latest",
            api_key=os.getenv("GEMINI_API_KEY4")
        )
        
        self.memory_manager = MemoryManager()
        super().__init__()

    # === Agents ===
    @agent
    def summarizer(self) -> Agent:
        return Agent(config=self.agents_config['summarizer'], llm=self.summarizer_llm, verbose=True)

    @agent
    def classifier(self) -> Agent:
        return Agent(config=self.agents_config['classifier'], llm=self.classifier_llm, verbose=True)

    @agent
    def direct_responder(self) -> Agent:
        return Agent(config=self.agents_config['direct_responder'], llm=self.direct_responder_llm, verbose=True)

    @agent
    def planner(self) -> Agent:
        return Agent(config=self.agents_config['planner'], llm=self.planner_llm, verbose=True)

    @agent
    def synthesizer(self) -> Agent:
        return Agent(config=self.agents_config['synthesizer'], llm=self.synthesizer_llm, verbose=True)

    @agent
    def memory_extractor(self) -> Agent:
        # Reuse planner LLM for memory extractor
        return Agent(config=self.agents_config['memory_extractor'], llm=self.planner_llm, verbose=True)

    # === Tasks ===
    @task
    def summarize_history(self) -> Task:
        return Task(config=self.tasks_config['summarize_history'])

    @task
    def classify_query(self) -> Task:
        return Task(config=self.tasks_config['classify_query'])

    @task
    def generate_direct_response(self) -> Task:
        return Task(config=self.tasks_config['generate_direct_response'])

    @task
    def plan_execution(self) -> Task:
        return Task(config=self.tasks_config['plan_execution'])

    @task
    def synthesize_response(self) -> Task:
        return Task(config=self.tasks_config['synthesize_response'])

    @task
    def extract_memory(self) -> Task:
        return Task(config=self.tasks_config['extract_memory'])

    # === Internal Execution Helpers ===
    def _execute_task_with_fallbacks(self, agent, task, fallbacks):
        try:
            return agent.execute_task(task)
        except (RateLimitError, APIError) as e:
            if isinstance(e, APIError) and getattr(e, 'status_code', None) != 429:
                raise e
            if not fallbacks:
                print(f"Exhausted fallbacks for {agent.llm.model}. Returning error message.")
                return "Error: LLM request failed. Please try again later."
            print(f"Rate limit or API error with {agent.llm.model}. Switching to fallback.")
            agent.llm = fallbacks[0]
            return self._execute_task_with_fallbacks(agent, task, fallbacks[1:])

    # === Optimized Workflow ===
    def run_workflow(self, user_query: str):
        # 1. Input Handling
        user_query = user_query.strip()  # Normalize input
        history = ChatHistory.load_history()
        inputs = {
            'user_query': user_query,
            'full_history': json.dumps(history),
            'user_profile_path': os.path.join(PROJECT_ROOT, 'knowledge', 'user_profile.json'),
            'operations_file_path': os.path.join(PROJECT_ROOT, 'knowledge', 'operations.json')
        }

        # --- Read user profile and operations ---
        file_tool = FileManagerTool()
        user_profile_raw = file_tool._run(inputs['user_profile_path'])
        user_profile_raw_content = user_profile_raw.split(':\n', 1)[-1] if ':\n' in user_profile_raw else user_profile_raw
        user_profile = {}
        try:
            user_profile = json.loads(user_profile_raw_content.strip())
        except json.JSONDecodeError:
            print("Warning: Invalid or empty user profile JSON. Using default empty profile.")
            user_profile = {}

        available_operations_raw = file_tool._run(inputs['operations_file_path'])
        available_operations_content = available_operations_raw.split(':\n', 1)[-1] if ':\n' in available_operations_raw else available_operations_raw
        available_operations = []
        try:
            available_operations = json.loads(available_operations_content.strip())
        except json.JSONDecodeError:
            print("Warning: Invalid or empty operations JSON. Using default empty list.")
            available_operations = []

        # Extract operation names
        op_names = "\n".join([op['name'] for op in available_operations])

        # 2. Classification
        classify_task = self.classify_query()
        classify_task.description = classify_task.description.format(
            user_query=inputs['user_query'],
            op_names=op_names,
            user_profile=json.dumps(user_profile)
        )
        classify_agent = self.classifier()
        classification_raw = self._execute_task_with_fallbacks(
            classify_agent,
            classify_task,
            [self.classifier_fallback1_llm, self.classifier_fallback2_llm]
        )
        
        try:
            classification = json5.loads(re.sub(r'```json|```', '', classification_raw).strip())
        except Exception as e:
            print(f"Classification parsing failed: {e}. Defaulting to agentic with full KB.")
            classification = {
                'mode': 'agentic',
                'required_operations': [op['name'] for op in available_operations],
                'required_kb': ['short_term', 'long_term', 'narrative']
            }

        # 3. Knowledge Retrieval
        kb_context = {}
        required_kb = classification.get('required_kb', [])
        
        if 'short_term' in required_kb:
            if len(history) >= 10:
                summary_task = self.summarize_history()
                summary_task.description = summary_task.description.format(full_history=inputs['full_history'])
                summary_agent = self.summarizer()
                kb_context['short_term'] = self._execute_task_with_fallbacks(
                    summary_agent,
                    summary_task,
                    [self.summarizer_fallback1_llm, self.summarizer_fallback2_llm]
                )
            else:
                kb_context['short_term'] = json.dumps(history[-3:]) if history else "No history."

        if 'long_term' in required_kb:
            # Only do RAG if query is substantive
            kb_context['long_term'] = LongTermRagTool()._run(query=user_query) if len(user_query.split()) > 3 else ""

        if 'narrative' in required_kb:
            kb_context['narrative'] = self.memory_manager.get_narrative_summary()

        # Include user profile always for consistency
        kb_context['user_profile'] = json.dumps(user_profile)

        # Assemble kb_context as structured string
        kb_context_str = "\n".join([f"{k}: {v}" for k, v in kb_context.items()])

        # 4. Mode Routing
        if classification['mode'] == 'direct':
            # Direct: Use direct_responder
            response_task = self.generate_direct_response()
            response_task.description = response_task.description.format(
                user_query=inputs['user_query'],
                kb_context=kb_context_str
            )
            response_agent = self.direct_responder()
            final_response = self._execute_task_with_fallbacks(
                response_agent,
                response_task,
                [self.direct_responder_fallback1_llm, self.direct_responder_fallback2_llm]
            )
        else:  # agentic
            # Get full details for required ops (loose from classifier)
            required_ops_names = classification.get('required_operations', [])
            required_ops = [op for op in available_operations if op['name'] in required_ops_names]
            required_ops_str = json.dumps(required_ops)

            # Step A: Planner
            plan_task = self.plan_execution()
            plan_task.description = plan_task.description.format(
                user_query=inputs['user_query'],
                kb_context=kb_context_str,
                required_operations=required_ops_str
            )
            planner_agent = self.planner()
            plan_raw = self._execute_task_with_fallbacks(
                planner_agent,
                plan_task,
                [self.planner_fallback1_llm, self.planner_fallback2_llm]
            )
            
            try:
                plan = json5.loads(re.sub(r'```json|```', '', plan_raw).strip())
            except Exception as e:
                print(f"Plan parsing failed: {e}. Retrying with fallback prompt.")
                # Retry with instruction for strict JSON
                plan_task.description += "\nPrevious attempt failed. Output strict JSON only, no extra text."
                plan_raw = self._execute_task_with_fallbacks(
                    planner_agent,
                    plan_task,
                    [self.planner_fallback1_llm, self.planner_fallback2_llm]
                )
                try:
                    plan = json5.loads(re.sub(r'```json|```', '', plan_raw).strip())
                except:
                    plan = {'plan': [], 'error': 'Failed to generate valid plan JSON after retry.'}

            if 'error' in plan:
                final_response = plan['error']
            else:
                # Step B: Executor
                try:
                    op_results = self.perform_operations(plan)
                except Exception as e:
                    op_results = f"Execution failed: {str(e)}. Partial results may be available."
                
                # Step C: Synthesizer (Response Generator)
                synth_task = self.synthesize_response()
                synth_task.description = synth_task.description.format(
                    user_query=inputs['user_query'],
                    kb_context=kb_context_str,
                    op_results=op_results
                )
                synth_agent = self.synthesizer()
                final_response = self._execute_task_with_fallbacks(
                    synth_agent,
                    synth_task,
                    [self.synthesizer_fallback1_llm, self.synthesizer_fallback2_llm]
                )

        # 5. Error & Fallbacks handled in _execute_task_with_fallbacks

        # 6. Output to User (final_response is natural language)

        # --- Save history ---
        history.append({"role": "user", "content": user_query})
        history.append({"role": "assistant", "content": final_response})
        ChatHistory.save_history(history)

        # --- OPTIMIZATION: Memory extraction ---
        should_extract_memory = (
            len(history) % 5 == 0 or  
            classification['mode'] == 'agentic' or  
            any(keyword in user_query.lower() for keyword in ['remember', 'task', 'project', 'remind'])
        )

        if should_extract_memory:
            try:
                extract_inputs = {
                    'interaction': json.dumps({
                        "query": user_query, 
                        "response": final_response
                    })
                }
                extract_task = self.extract_memory()
                extract_task.description = extract_task.description.format(interaction=extract_inputs['interaction'])
                
                extracted_raw = self._execute_task_with_fallbacks(
                    self.memory_extractor(),
                    extract_task,
                    [self.planner_fallback1_llm, self.planner_fallback2_llm]
                )
                
                extracted = json5.loads(re.sub(r'```json|```', '', extracted_raw).strip())
                self.memory_manager.update_long_term(extracted)
            except Exception as e:
                print(f"Warning: Memory extraction failed: {e}")

        # --- Periodic narrative ---
        if len(history) % self.memory_manager.policy.get('narrative_interval', 20) == 0:  
            try:
                narrative = self.memory_manager.create_narrative_summary(kb_context.get('short_term', ''))
                summaries_path = os.path.join(MEMORY_DIR, 'narrative', 'summaries.json')
                summaries = self.memory_manager.safe_load_json(summaries_path)
                summaries.append({"date": date.today().isoformat(), "summary": narrative})
                with open(summaries_path, 'w', encoding='utf-8') as f:
                    json.dump(summaries, f, indent=2)
            except Exception as e:
                print(f"Warning: Narrative summary failed: {e}")

        return final_response

    def perform_operations(self, plan: dict) -> str:
        operations = plan.get('plan', [])
        # Log raw plan for debugging
        print(f"Raw plan received: {operations}")
        
        # Remap 'operation' to 'name' if needed
        for op in operations:
            if 'operation' in op and 'name' not in op:
                op['name'] = op.pop('operation')
            if 'params' in op and 'parameters' not in op:
                op['parameters'] = op.pop('params')  # Also handle params key mismatch if any
        
        ops_tool = OperationsTool()
        return ops_tool._run(operations)

    @crew
    def crew(self) -> Crew:
        return Crew(agents=self.agents, tasks=self.tasks, process=Process.sequential, verbose=True)