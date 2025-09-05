# src/crew.py
import json
import os
import traceback
from crewai import Agent, Crew, Process, Task, LLM
from crewai.project import CrewBase, agent, crew, task
from typing import List
from tools.file_manager_tool import FileManagerTool
from tools.operations_tool import OperationsTool
from tools.rag_tool import RagTool
from chat_history import ChatHistory
import json5
import re
from common_functions.Find_project_root import find_project_root
from litellm.exceptions import RateLimitError, APIError
PROJECT_ROOT = find_project_root()

@CrewBase
class AiAgent():
    agents: List[Agent]
    tasks: List[Task]

    def __init__(self):
        # Define individual LLMs for each agent to avoid rate limits
        self.summarizer_llm = LLM(model="cohere/command-r-plus", api_key=os.getenv("COHERE_API_KEY"))
        self.summarizer_fallback1_llm = LLM(model="openrouter/openai/gpt-oss-20b:free", api_key=os.getenv("OPENROUTER_API_KEY1"))
        self.summarizer_fallback2_llm = LLM(model="gemini/gemini-1.5-flash-latest", api_key=os.getenv("GEMINI_API_KEY1"))
        
        # Classifier
        self.classifier_llm = LLM(model="groq/llama-3.1-8b-instant", api_key=os.getenv("GROQ_API_KEY1"))
        self.classifier_fallback1_llm = LLM(model="openrouter/google/gemma-2-9b-it:free", api_key=os.getenv("OPENROUTER_API_KEY2"))
        self.classifier_fallback2_llm = LLM(model="gemini/gemini-1.5-flash-latest", api_key=os.getenv("GEMINI_API_KEY2"))
        
        # Direct Responder
        self.direct_responder_llm = LLM(model="openrouter/openai/gpt-oss-20b:free", api_key=os.getenv("OPENROUTER_API_KEY3"))
        self.direct_responder_fallback1_llm = LLM(model="openrouter/openai/gpt-oss-120b:free", api_key=os.getenv("OPENROUTER_API_KEY4"))
        self.direct_responder_fallback2_llm = LLM(model="gemini/gemini-1.5-flash-latest", api_key=os.getenv("GEMINI_API_KEY3"))
        
        # Analyzer1
        self.analyzer1_llm = LLM(model="groq/llama-3.3-70b-versatile", api_key=os.getenv("GROQ_API_KEY2"))
        self.analyzer1_fallback1_llm = LLM(model="openrouter/deepseek/deepseek-chat-v3.1:free", api_key=os.getenv("OPENROUTER_API_KEY2"))
        self.analyzer1_fallback2_llm = LLM(model="gemini/gemini-1.5-flash-latest", api_key=os.getenv("GEMINI_API_KEY4"))
        
        # Analyzer2
        self.analyzer2_llm = LLM(model="gemini/gemini-1.5-flash-latest", api_key=os.getenv("GEMINI_API_KEY2"))
        self.analyzer2_fallback1_llm = LLM(model="openrouter/deepseek/deepseek-chat-v3.1:free", api_key=os.getenv("OPENROUTER_API_KEY3"))
        self.analyzer2_fallback2_llm = LLM(model="groq/llama-3.1-8b-instant", api_key=os.getenv("GROQ_API_KEY3"))
        
        # Refiner
        self.refiner_llm = LLM(model="openrouter/deepseek/deepseek-chat-v3.1:free", api_key=os.getenv("OPENROUTER_API_KEY1"))
        self.refiner_fallback1_llm = LLM(model="gemini/gemini-1.5-flash-latest", api_key=os.getenv("GEMINI_API_KEY3"))
        self.refiner_fallback2_llm = LLM(model="groq/llama-3.3-70b-versatile", api_key=os.getenv("GROQ_API_KEY4"))
        
        # Synthesizer
        self.synthesizer_llm = LLM(model="openrouter/openai/gpt-oss-120b:free", api_key=os.getenv("OPENROUTER_API_KEY4"))
        self.synthesizer_fallback1_llm = LLM(model="openrouter/deepseek/deepseek-chat-v3.1:free", api_key=os.getenv("OPENROUTER_API_KEY2"))
        self.synthesizer_fallback2_llm = LLM(model="gemini/gemini-1.5-flash-latest", api_key=os.getenv("GEMINI_API_KEY4"))


        super().__init__()

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
        return Agent(config=self.agents_config['analyzer1'], tools=[RagTool(), FileManagerTool()], llm=self.analyzer1_llm, verbose=True)

    @agent
    def analyzer2(self) -> Agent:
        return Agent(config=self.agents_config['analyzer2'], llm=self.analyzer2_llm, verbose=True)

    @agent
    def refiner(self) -> Agent:
        return Agent(config=self.agents_config['refiner'], llm=self.refiner_llm, verbose=True)

    @agent
    def synthesizer(self) -> Agent:
        return Agent(config=self.agents_config['synthesizer'], llm=self.synthesizer_llm, verbose=True)

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

    def run_workflow(self, user_query: str):
        history = ChatHistory.load_history()
        inputs = {
            'user_query': user_query,
            'full_history': json.dumps(history),
            'user_preferences_path': os.path.join(PROJECT_ROOT, 'knowledge', 'user_preference.txt'),
            'operations_file_path': os.path.join(PROJECT_ROOT, 'knowledge', 'operations.txt')
        }

        # Read user preferences and operations once
        file_tool = FileManagerTool()
        user_preferences = file_tool._run(inputs['user_preferences_path']).split('Content of ', 1)[-1]  # Extract content
        available_operations = file_tool._run(inputs['operations_file_path']).split('Content of ', 1)[-1]

        # Extract operation names for Analyzer1 (to minimize tokens)
        op_names = "\n".join([line.split('|')[0].strip() for line in available_operations.split('\n') if line.strip() and not line.startswith('#') and '|' in line])

        # Summarize history
        summary_task = self.summarize_history()
        summary_task.description = summary_task.description.format(full_history=inputs['full_history'])
        summary_agent = self.summarizer()
        summary = self._execute_task_with_fallbacks(summary_agent, summary_task, [self.summarizer_fallback1_llm, self.summarizer_fallback2_llm])
        inputs['summarized_history'] = summary

        # Classify query
        classify_task = self.classify_query()
        classify_task.description = classify_task.description.format(
            user_query=inputs['user_query'],
            summarized_history=inputs['summarized_history'],
            user_preferences_path=inputs['user_preferences_path'],
            user_preferences=user_preferences
        )
        classify_agent = self.classifier()
        classification_raw = self._execute_task_with_fallbacks(classify_agent, classify_task, [self.classifier_fallback1_llm, self.classifier_fallback2_llm])
        classification = json5.loads(re.sub(r'```json|```', '', classification_raw).strip())

        if classification['mode'] == 'direct':
            # Generate direct response
            response_task = self.generate_direct_response()
            response_task.description = response_task.description.format(
                user_query=inputs['user_query'],
                summarized_history=inputs['summarized_history'],
                user_preferences_path=inputs['user_preferences_path'],
                user_preferences=user_preferences
            )
            response_agent = self.direct_responder()
            response = self._execute_task_with_fallbacks(response_agent, response_task, [self.direct_responder_fallback1_llm, self.direct_responder_fallback2_llm])
            final_response = response
        else:
            # Analyzer1: Initial analysis with op names only
            analyze1_task = self.analyze1()
            analyze1_task.description = analyze1_task.description.format(
                user_query=inputs['user_query'],
                summarized_history=inputs['summarized_history'],
                user_preferences_path=inputs['user_preferences_path'],
                user_preferences=user_preferences,
                op_names=op_names
            )
            analyzer1_agent = self.analyzer1()
            analyze1_raw = self._execute_task_with_fallbacks(analyzer1_agent, analyze1_task, [self.analyzer1_fallback1_llm, self.analyzer1_fallback2_llm])
            analyze1_json = json5.loads(re.sub(r'```json|```', '', analyze1_raw).strip())

            # RAG Retrieval: Fetch relevant operations for each sub-task
            subtasks = analyze1_json.get('subtasks', [])
            rag_tool = RagTool()
            retrieved_ops_set = set()
            for subtask in subtasks:
                rag_results = rag_tool._run(query=subtask, k=5)
                retrieved_ops_set.update(rag_results.split('\n'))

            retrieved_ops = "\n".join(retrieved_ops_set)

            # Analyzer2: Generate plan with retrieved ops
            analyze2_task = self.analyze2()
            analyze2_task.description = analyze2_task.description.format(
                user_query=inputs['user_query'],
                summarized_history=inputs['summarized_history'],
                user_preferences_path=inputs['user_preferences_path'],
                user_preferences=user_preferences,
                intents=json.dumps(analyze1_json.get('intents', [])),
                subtasks=json.dumps(subtasks),
                retrieved_ops=retrieved_ops
            )
            analyzer2_agent = self.analyzer2()
            plan_raw = self._execute_task_with_fallbacks(analyzer2_agent, analyze2_task, [self.analyzer2_fallback1_llm, self.analyzer2_fallback2_llm])
            plan = json5.loads(re.sub(r'```json|```', '', plan_raw).strip())

            # Refine plan
            refine_inputs = {**inputs, 'plan': json.dumps(plan)}
            refine_task = self.refine_plan()
            refine_task.description = refine_task.description.format(
                plan=json.dumps(plan),
                operations_file_path=inputs['operations_file_path'],
                available_operations=available_operations,
                intents=json.dumps(analyze1_json.get('intents', [])),
                subtasks=json.dumps(subtasks)
            )
            refine_agent = self.refiner()
            refined_raw = self._execute_task_with_fallbacks(refine_agent, refine_task, [self.refiner_fallback1_llm, self.refiner_fallback2_llm])
            refined_plan = json5.loads(re.sub(r'```json|```', '', refined_raw).strip())

            if 'error' in refined_plan:
                final_response = refined_plan['error']
            else:
                # Execute operations
                op_results = self.perform_operations(refined_plan)

                # Synthesize response
                synth_inputs = {**inputs, 'op_results': op_results}
                synth_task = self.synthesize_response()
                synth_task.description = synth_task.description.format(
                    user_query=inputs['user_query'],
                    summarized_history=inputs['summarized_history'],
                    user_preferences_path=inputs['user_preferences_path'],
                    user_preferences=user_preferences,
                    op_results=op_results
                )
                synth_agent = self.synthesizer()
                final_response = self._execute_task_with_fallbacks(synth_agent, synth_task, [self.synthesizer_fallback1_llm, self.synthesizer_fallback2_llm])

        # Save history
        history.append({"role": "user", "content": user_query})
        history.append({"role": "assistant", "content": final_response})
        ChatHistory.save_history(history)

        return final_response

    def perform_operations(self, plan: dict) -> str:
        operations = plan.get('operations', [])
        ops_tool = OperationsTool()
        return ops_tool._run(operations)

    @crew
    def crew(self) -> Crew:
        return Crew(agents=self.agents, tasks=self.tasks, process=Process.sequential, verbose=True)