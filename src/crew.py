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

def find_project_root(marker_file='pyproject.toml') -> str:
    """Find the project root by searching upwards for the marker file."""
    current_dir = os.path.dirname(os.path.abspath(__file__))
    while current_dir != os.path.dirname(current_dir):  # Stop at system root
        if os.path.exists(os.path.join(current_dir, marker_file)):
            return current_dir
        current_dir = os.path.dirname(current_dir)
    raise FileNotFoundError("Project root not found. Ensure 'pyproject.toml' exists at the root.")

PROJECT_ROOT = find_project_root()

@CrewBase
class AiAgent():
    agents: List[Agent]
    tasks: List[Task]

    def __init__(self):
        gemini_key = os.getenv("GEMINI_API_KEY")
        openrouter_key = os.getenv("OPENROUTER_API_KEY")

        self.light_llm = LLM(model="gemini/gemini-1.5-flash", api_key=gemini_key) if gemini_key else None
        self.deep_llm = LLM(model="openrouter/deepseek/deepseek-chat", api_key=openrouter_key) if openrouter_key else self.light_llm

        super().__init__()

    @agent
    def summarizer(self) -> Agent:
        return Agent(config=self.agents_config['summarizer'], llm=self.light_llm, verbose=True)

    @agent
    def classifier(self) -> Agent:
        return Agent(config=self.agents_config['classifier'], llm=self.light_llm, verbose=True)

    @agent
    def direct_responder(self) -> Agent:
        return Agent(config=self.agents_config['direct_responder'], llm=self.light_llm, verbose=True)

    @agent
    def analyzer_planner(self) -> Agent:
        return Agent(config=self.agents_config['analyzer_planner'], tools=[RagTool(), FileManagerTool()], llm=self.deep_llm, verbose=True)

    @agent
    def refiner(self) -> Agent:
        return Agent(config=self.agents_config['refiner'], llm=self.light_llm, verbose=True)

    @agent
    def synthesizer(self) -> Agent:
        return Agent(config=self.agents_config['synthesizer'], llm=self.light_llm, verbose=True)

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
    def analyze_and_plan(self) -> Task:
        return Task(config=self.tasks_config['analyze_and_plan'])

    @task
    def refine_plan(self) -> Task:
        return Task(config=self.tasks_config['refine_plan'])

    @task
    def synthesize_response(self) -> Task:
        return Task(config=self.tasks_config['synthesize_response'])

    def run_workflow(self, user_query: str):
        history = ChatHistory.load_history()
        inputs = {
            'user_query': user_query,
            'full_history': json.dumps(history),
            'user_preferences_path': os.path.join(PROJECT_ROOT, 'knowledge', 'user_preference.txt'),
            'operations_file_path': os.path.join(PROJECT_ROOT, 'knowledge', 'operations.txt')
        }

        summary_task = self.summarize_history()
        summary = summary_task.execute(inputs)
        inputs['summarized_history'] = summary

        classify_task = self.classify_query()
        classification_raw = classify_task.execute(inputs)
        classification = json5.loads(re.sub(r'```json|```', '', classification_raw).strip())

        if classification['mode'] == 'direct':
            response_task = self.generate_direct_response()
            response = response_task.execute(inputs)
            final_response = response
        else:
            plan_task = self.analyze_and_plan()
            plan_raw = plan_task.execute(inputs)
            plan = json5.loads(re.sub(r'```json|```', '', plan_raw).strip())

            refine_inputs = {**inputs, 'plan': json.dumps(plan)}
            refine_task = self.refine_plan()
            refined_raw = refine_task.execute(refine_inputs)
            refined_plan = json5.loads(re.sub(r'```json|```', '', refined_raw).strip())

            if 'error' in refined_plan:
                final_response = refined_plan['error']
            else:
                op_results = self.perform_operations(refined_plan)
                synth_inputs = {**inputs, 'op_results': op_results}
                synth_task = self.synthesize_response()
                final_response = synth_task.execute(synth_inputs)

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