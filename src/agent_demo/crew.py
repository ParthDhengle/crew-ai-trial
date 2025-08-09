import json
from crewai import Agent, Crew, Process, Task
from crewai.project import CrewBase, agent, crew, task
from typing import List

@CrewBase
class AiAgent():
    agents: List[Agent]
    tasks: List[Task]

    @agent
    def analyzer(self) -> Agent:
        return Agent(
            config=self.agents_config['analyzer'],
            verbose=True
        )

    @task
    def analyze_and_plan(self) -> Task:
        return Task(
            config=self.tasks_config['analyze_and_plan'],
        )

    def perform_operations(self, json_file_path):
        try:
            with open(json_file_path, 'r') as f:
                plan = json.load(f)

            if isinstance(plan, str):
                # It's a message, not a JSON plan
                print(plan)
                return

            for step in plan.get("operations", []):
                print(f"Performing: {step['name']}")
                # Here you'd call your actual operation logic
                # Example:
                if step["name"] == "send_email":
                    print(f"Sending email to {step['parameters']['to']}")

            print("✅ All operations completed.")
        except Exception as e:
            print(f"Error executing operations: {e}")

    @crew
    def crew(self) -> Crew:
        return Crew(
            agents=self.agents,
            tasks=self.tasks,
            process=Process.sequential,
            verbose=True
        )
