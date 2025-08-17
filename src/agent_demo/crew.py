# src/agent_demo/crew.py
import json
import os
import traceback
from datetime import datetime
from crewai import Agent, Crew, Process, Task, LLM
from crewai.project import CrewBase, agent, crew, task
from typing import List
from agent_demo.tools.file_manager_tool import FileManagerTool
from agent_demo.tools.operations_tool import OperationsTool

@CrewBase
class AiAgent():
    agents: List[Agent]
    tasks: List[Task]

    def __init__(self):
        # Configure Groq LLM
        self.llm = LLM(
            model="groq/gemma2-9b-it",  # or "groq/mixtral-8x7b-32768"
            api_key=os.getenv("GROQ_API_KEY")
        )
        super().__init__()

    @agent
    def analyzer(self) -> Agent:
        return Agent(
            config=self.agents_config['analyzer'],
            tools=[FileManagerTool()],
            llm=self.llm,
            verbose=True
        )
    @task
    def analyze_and_plan(self) -> Task:
        return Task(config=self.tasks_config['analyze_and_plan'])

    def perform_operations(self, json_file_path):
        """
        Read the execution plan and perform all operations in sequence using OperationsTool.
        """
        try:
            if not os.path.exists(json_file_path):
                print(f"❌ Execution plan file not found: {json_file_path}")
                return

            with open(json_file_path, 'r', encoding='utf-8') as f:
                content = f.read().strip()

            # Handle the pre-defined unavailable message or non-json
            if content.startswith('"Sorry,') or content == '"Sorry, I can\'t do that yet. This feature will be available soon."':
                print(content.strip('"'))
                return

            # Fix common JSON formatting issues
            content = content.strip()
            
            # Remove markdown code blocks if present
            if content.startswith('```json') and content.endswith('```'):
                content = content[7:-3].strip()
            elif content.startswith('```') and content.endswith('```'):
                content = content[3:-3].strip()
            
            # If the content starts with "operations": [...], wrap it in braces
            if content.startswith('"operations":'):
                content = '{' + content + '}'
            
            try:
                plan = json.loads(content)
            except json.JSONDecodeError as e:
                print("❌ Execution plan is not valid JSON. Attempting to fix...")
                print(f"JSON Error: {e}")
                print("Raw content:")
                print(content)
                
                # Try to extract just the operations array if it's malformed
                try:
                    # Look for operations array pattern
                    import re
                    operations_match = re.search(r'"operations":\s*(\[.*\])', content, re.DOTALL)
                    if operations_match:
                        operations_json = operations_match.group(1)
                        plan = {"operations": json.loads(operations_json)}
                        print("✅ Successfully extracted operations from malformed JSON")
                    else:
                        print("❌ Could not extract operations from malformed JSON")
                        return
                except Exception as fix_error:
                    print(f"❌ Failed to fix JSON: {fix_error}")
                    return

            if not isinstance(plan, dict) or 'operations' not in plan:
                print("❌ Invalid execution plan format (missing 'operations')")
                print(f"Plan structure: {type(plan)}")
                if isinstance(plan, dict):
                    print(f"Available keys: {list(plan.keys())}")
                return

            operations = plan.get('operations', [])
            if not operations:
                print("ℹ️ No operations to execute")
                return

            print(f"🚀 Executing {len(operations)} operation(s) using OperationsTool...\n")

            # Use the centralized OperationsTool to execute all operations
            ops_tool = OperationsTool()
            # The tool accepts a list; call its _run() directly (you're running local code)
            raw_result = ops_tool._run(operations)

            # Pretty print results (each line per op)
            for line in raw_result.splitlines():
                print("   " + line)

            # Quick summary
            success_count = len([l for l in raw_result.splitlines() if l.startswith("✅")])
            fail_count = len([l for l in raw_result.splitlines() if l.startswith("❌")])
            print("\n🎉 Execution completed!")
            print(f"📋 Summary: {success_count} successful, {fail_count} failed")

        except Exception as e:
            print("❌ Error executing operations:")
            traceback.print_exc()
    @crew
    def crew(self) -> Crew:
        return Crew(
            agents=self.agents,
            tasks=self.tasks,
            process=Process.sequential,
            verbose=True
        )