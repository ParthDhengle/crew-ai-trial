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
        
        # Classifier
        self.classifier_llm = LLM(
            model="groq/llama-3.1-8b-instant",
            api_key=os.getenv("GROQ_API_KEY1")
        )
        self.classifier_fallback1_llm = LLM(
            model="openrouter/google/gemma-2-9b-it:free",
            api_key=os.getenv("OPENROUTER_API_KEY2")
        )
        self.classifier_fallback2_llm = LLM(
            model="gemini/gemini-1.5-flash-latest",
            api_key=os.getenv("GEMINI_API_KEY2")
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
        
        # Analyzer1
        self.analyzer1_llm = LLM(
            model="groq/llama-3.3-70b-versatile",
            api_key=os.getenv("GROQ_API_KEY2")
        )
        self.analyzer1_fallback1_llm = LLM(
            model="openrouter/deepseek/deepseek-chat-v3.1:free",
            api_key=os.getenv("OPENROUTER_API_KEY2")
        )
        self.analyzer1_fallback2_llm = LLM(
            model="gemini/gemini-1.5-flash-latest",
            api_key=os.getenv("GEMINI_API_KEY4")
        )
        
        # Analyzer2
        self.analyzer2_llm = LLM(
            model="gemini/gemini-1.5-flash-latest",
            api_key=os.getenv("GEMINI_API_KEY2")
        )
        self.analyzer2_fallback1_llm = LLM(
            model="openrouter/deepseek/deepseek-chat-v3.1:free",
            api_key=os.getenv("OPENROUTER_API_KEY3")
        )
        self.analyzer2_fallback2_llm = LLM(
            model="groq/llama-3.1-8b-instant",
            api_key=os.getenv("GROQ_API_KEY3")
        )
        
        # Refiner
        self.refiner_llm = LLM(
            model="openrouter/deepseek/deepseek-chat-v3.1:free",
            api_key=os.getenv("OPENROUTER_API_KEY1")
        )
        self.refiner_fallback1_llm = LLM(
            model="gemini/gemini-1.5-flash-latest",
            api_key=os.getenv("GEMINI_API_KEY3")
        )
        self.refiner_fallback2_llm = LLM(
            model="groq/llama-3.3-70b-versatile",
            api_key=os.getenv("GROQ_API_KEY4")
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
    def analyzer1(self) -> Agent:
        return Agent(
            config=self.agents_config['analyzer1'],
            tools=[RagTool(), FileManagerTool()],
            llm=self.analyzer1_llm,
            verbose=True
        )

    @agent
    def analyzer2(self) -> Agent:
        return Agent(config=self.agents_config['analyzer2'], llm=self.analyzer2_llm, verbose=True)

    @agent
    def refiner(self) -> Agent:
        return Agent(config=self.agents_config['refiner'], llm=self.refiner_llm, verbose=True)

    @agent
    def synthesizer(self) -> Agent:
        return Agent(config=self.agents_config['synthesizer'], llm=self.synthesizer_llm, verbose=True)

    @agent
    def memory_extractor(self) -> Agent:
        # Reuse Analyzer1 LLM
        return Agent(config=self.agents_config['memory_extractor'], llm=self.analyzer1_llm, verbose=True)

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
    def analyze1(self) -> Task:
        return Task(config=self.tasks_config['analyze1'])

    @task
    def analyze2(self) -> Task:
        return Task(config=self.tasks_config['analyze2'])

    @task
    def refine_plan(self) -> Task:
        return Task(config=self.tasks_config['refine_plan'])

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
                raise e
            print(f"Rate limit error with {agent.llm.model}. Switching to fallback.")
            agent.llm = fallbacks[0]
            return self._execute_task_with_fallbacks(agent, task, fallbacks[1:])

    # === Optimized Workflow ===
    def run_workflow(self, user_query: str):
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

        # Extract operation names for Analyzer1 (to minimize tokens)
        op_names = "\n".join([op['name'] for op in available_operations])

        # --- OPTIMIZATION: Only summarize if history is long ---
        summary = "No significant history."
        if len(history) >= 5:  # Changed from 2 to 5 to avoid unnecessary summarization
            summary_task = self.summarize_history()
            summary_task.description = summary_task.description.format(full_history=inputs['full_history'])
            summary_agent = self.summarizer()
            summary = self._execute_task_with_fallbacks(
                summary_agent,
                summary_task,
                [self.summarizer_fallback1_llm, self.summarizer_fallback2_llm]
            )
        else:
            # For short histories, just use the last few exchanges
            if history:
                recent_history = history[-3:]  # Last 3 exchanges
                summary = json.dumps(recent_history)

        # --- Preprocessor: Load/assemble memory (optimized) ---
        narrative_summary = self.memory_manager.get_narrative_summary()
        relevant_long_term = ""
        
        # Only do expensive RAG lookup for complex queries
        if len(user_query.split()) > 3:  # Simple heuristic
            relevant_long_term = LongTermRagTool()._run(query=user_query)

        prompt_context = self.memory_manager.assemble_prompt_context(
            summary, user_profile, narrative_summary, relevant_long_term
        )
        inputs['prompt_context'] = prompt_context

        # --- Classify query ---
        classify_task = self.classify_query()
        classify_task.description = classify_task.description.format(
            user_query=inputs['user_query'],
            prompt_context=inputs['prompt_context']
        )
        classify_agent = self.classifier()
        classification_raw = self._execute_task_with_fallbacks(
            classify_agent,
            classify_task,
            [self.classifier_fallback1_llm, self.classifier_fallback2_llm]
        )
        
        try:
            classification = json5.loads(re.sub(r'```json|```', '', classification_raw).strip())
        except:
            # Fallback if JSON parsing fails
            if 'direct' in classification_raw.lower():
                classification = {'mode': 'direct'}
            else:
                classification = {'mode': 'agentic'}

        if classification['mode'] == 'direct':
            # --- Direct Response (Optimized) ---
            response_task = self.generate_direct_response()
            response_task.description = response_task.description.format(
                user_query=inputs['user_query'],
                prompt_context=inputs['prompt_context']
            )
            response_agent = self.direct_responder()
            response = self._execute_task_with_fallbacks(
                response_agent,
                response_task,
                [self.direct_responder_fallback1_llm, self.direct_responder_fallback2_llm]
            )
            final_response = response
        else:
            # --- Agentic Path (existing code) ---
            # Analyzer1
            analyze1_task = self.analyze1()
            analyze1_task.description = analyze1_task.description.format(
                user_query=inputs['user_query'],
                prompt_context=inputs['prompt_context'],
                op_names=op_names
            )
            analyzer1_agent = self.analyzer1()
            analyze1_raw = self._execute_task_with_fallbacks(
                analyzer1_agent,
                analyze1_task,
                [self.analyzer1_fallback1_llm, self.analyzer1_fallback2_llm]
            )
            
            try:
                analyze1_json = json5.loads(re.sub(r'json|```', '', analyze1_raw).strip())
            except:
                # Fallback if parsing fails
                analyze1_json = {'intents': [], 'subtasks': [user_query]}

            # RAG Retrieval: Fetch relevant operations
            subtasks = analyze1_json.get('subtasks', [])
            rag_tool = RagTool()
            retrieved_ops_set = set()
            for subtask in subtasks:
                rag_results = rag_tool._run(query=subtask, k=5)
                retrieved_ops_set.update(rag_results.split('\n'))
            retrieved_ops = "\n".join(retrieved_ops_set)

            # Analyzer2
            analyze2_task = self.analyze2()
            analyze2_task.description = analyze2_task.description.format(
                user_query=inputs['user_query'],
                prompt_context=inputs['prompt_context'],
                intents=json.dumps(analyze1_json.get('intents', [])),
                subtasks=json.dumps(subtasks),
                retrieved_ops=retrieved_ops
            )
            analyzer2_agent = self.analyzer2()
            plan_raw = self._execute_task_with_fallbacks(
                analyzer2_agent,
                analyze2_task,
                [self.analyzer2_fallback1_llm, self.analyzer2_fallback2_llm]
            )
            
            try:
                plan = json5.loads(re.sub(r'json|```', '', plan_raw).strip())
            except:
                plan = {'operations': [], 'error': 'Failed to parse plan'}

            # Refine plan
            refine_task = self.refine_plan()
            refine_task.description = refine_task.description.format(
                plan=json.dumps(plan),
                operations_file_path=inputs['operations_file_path'],
                available_operations=json.dumps(available_operations),  # Convert to string
                intents=json.dumps(analyze1_json.get('intents', [])),
                subtasks=json.dumps(subtasks)
            )
            refine_agent = self.refiner()
            refined_raw = self._execute_task_with_fallbacks(
                refine_agent,
                refine_task,
                [self.refiner_fallback1_llm, self.refiner_fallback2_llm]
            )
            
            try:
                refined_plan = json5.loads(re.sub(r'json|```', '', refined_raw).strip())
            except:
                refined_plan = {'error': 'Failed to refine plan'}

            if 'error' in refined_plan:
                final_response = refined_plan['error']
            else:
                # Execute operations
                op_results = self.perform_operations(refined_plan)
                
                # Synthesize response
                synth_task = self.synthesize_response()
                synth_task.description = synth_task.description.format(
                    user_query=inputs['user_query'],
                    prompt_context=inputs['prompt_context'],
                    op_results=op_results
                )
                synth_agent = self.synthesizer()
                final_response = self._execute_task_with_fallbacks(
                    synth_agent,
                    synth_task,
                    [self.synthesizer_fallback1_llm, self.synthesizer_fallback2_llm]
                )

        # --- Save history ---
        history.append({"role": "user", "content": user_query})
        history.append({"role": "assistant", "content": final_response})
        ChatHistory.save_history(history)

        # --- OPTIMIZATION: Only extract memory periodically or for complex interactions ---
        should_extract_memory = (
            len(history) % 5 == 0 or  # Every 5 interactions
            classification['mode'] == 'agentic' or  # Complex interactions
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
                
                # FIX: Properly escape the format string
                interaction_data = extract_inputs['interaction']
                extract_task.description = extract_task.description.format(interaction=interaction_data)
                
                extracted_raw = self._execute_task_with_fallbacks(
                    self.memory_extractor(),
                    extract_task,
                    [self.analyzer1_fallback1_llm, self.analyzer1_fallback2_llm]
                )
                
                try:
                    extracted = json5.loads(re.sub(r'json|```', '', extracted_raw).strip())
                    self.memory_manager.update_long_term(extracted)
                except Exception as e:
                    print(f"Warning: Failed to parse memory extraction: {e}")
                    
            except Exception as e:
                print(f"Warning: Memory extraction failed: {e}")

        # --- Periodic narrative (less frequent) ---
        if len(history) % self.memory_manager.policy.get('narrative_interval', 20) == 0:  # Every 20 instead of 10
            try:
                narrative = self.memory_manager.create_narrative_summary(summary)
                summaries_path = os.path.join(MEMORY_DIR, 'narrative', 'summaries.json')
                summaries = self.memory_manager.safe_load_json(summaries_path)
                summaries.append({"date": date.today().isoformat(), "summary": narrative})
                with open(summaries_path, 'w', encoding='utf-8') as f:
                    json.dump(summaries, f, indent=2)
            except Exception as e:
                print(f"Warning: Narrative summary failed: {e}")

        return final_response

    def perform_operations(self, plan: dict) -> str:
        operations = plan.get('operations', [])
        ops_tool = OperationsTool()
        return ops_tool._run(operations)

    @crew
    def crew(self) -> Crew:
        return Crew(agents=self.agents, tasks=self.tasks, process=Process.sequential, verbose=True)