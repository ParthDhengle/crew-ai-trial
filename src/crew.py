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

        # Read user preferences and operations once (using FileManagerTool or open)
        file_tool = FileManagerTool()
        user_preferences = file_tool._run(inputs['user_preferences_path']).split('Content of ', 1)[-1]  # Extract content
        available_operations = file_tool._run(inputs['operations_file_path']).split('Content of ', 1)[-1]

        # Summarize history
        summary_task = self.summarize_history()
        summary_task.description = summary_task.description.format(full_history=inputs['full_history'])
        summary_agent = self.summarizer()
        summary = summary_agent.execute_task(summary_task)
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
        classification_raw = classify_agent.execute_task(classify_task)
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
            response = response_agent.execute_task(response_task)
            final_response = response
        else:
            # Analyze and plan
            plan_task = self.analyze_and_plan()
            plan_task.description = plan_task.description.format(
                user_query=inputs['user_query'],
                summarized_history=inputs['summarized_history'],
                user_preferences_path=inputs['user_preferences_path'],
                user_preferences=user_preferences,
                operations_file_path=inputs['operations_file_path'],
                available_operations=available_operations
            )
            plan_agent = self.analyzer_planner()
            plan_raw = plan_agent.execute_task(plan_task)
            plan = json5.loads(re.sub(r'```json|```', '', plan_raw).strip())

            # Refine plan
            refine_inputs = {**inputs, 'plan': json.dumps(plan)}
            refine_task = self.refine_plan()
            refine_task.description = refine_task.description.format(
                plan=json.dumps(plan),
                operations_file_path=inputs['operations_file_path'],
                available_operations=available_operations
            )
            refine_agent = self.refiner()
            refined_raw = refine_agent.execute_task(refine_task)
            refined_plan = json5.loads(re.sub(r'```json|```', '', refined_raw).strip())

            if 'error' in refined_plan:
                final_response = refined_plan['error']
            else:
                # Execute operations (custom, no change)
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
                final_response = synth_agent.execute_task(synth_task)

        # Save history (no change)
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