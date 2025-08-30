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
        # Configure Groq LLM - check if API key exists
        groq_key = os.getenv("GROQ_API_KEY")
        gemini_key = os.getenv("GEMINI_API_KEY")
        
        if groq_key:
            self.llm = LLM(
                model="groq/gemma2-9b-it",
                api_key=groq_key
            )
        elif gemini_key:
            self.llm = LLM(
                model="gemini/gemini-pro",
                api_key=gemini_key
            )
        else:
            print("Warning: No API key found. Using default LLM.")
            self.llm = None
        
        super().__init__()

    @agent
    def analyzer(self) -> Agent:
        agent_config = self.agents_config['analyzer'].copy()
        
        # Create agent with or without LLM
        if self.llm:
            return Agent(
                config=agent_config,
                tools=[FileManagerTool()],
                llm=self.llm,
                verbose=True
            )
        else:
            return Agent(
                config=agent_config,
                tools=[FileManagerTool()],
                verbose=True
            )

    @task
    def analyze_and_plan(self) -> Task:
        return Task(config=self.tasks_config['analyze_and_plan'])

    def preprocess_query(self, query: str) -> dict:
        """
        Preprocess the user query to generate an execution plan.
        Returns a JSON execution plan or a fallback message.
        """
        # Read user preferences
        preferences = {}
        try:
            with open("knowledge/user_preference.txt", "r") as f:
                for line in f:
                    if ":" in line:
                        key, value = line.split(":", 1)
                        preferences[key.strip()] = value.strip()
        except Exception as e:
            print(f"Warning: Could not read preferences: {e}")

        # Read operations
        operations = []
        try:
            with open("knowledge/operations.txt", "r") as f:
                for line in f:
                    if "|" in line and not line.startswith("#"):
                        parts = line.split("|")
                        operations.append(parts[0].strip())
        except Exception as e:
            print(f"Warning: Could not read operations: {e}")

        # Match query to operations
        query_lower = query.lower()
        if any(keyword in query_lower for keyword in ["what is", "explain", "define"]):
            # Personalize based on preferences
            personalized_query = query
            if preferences.get("User is interested in") == "AI Agents" and "ai" in query_lower:
                personalized_query = f"{query} with a focus on AI agents"
            
            if "retrieve_knowledge" in operations:
                return {
                    "operations": [
                        {
                            "name": "retrieve_knowledge",
                            "parameters": {"query": personalized_query},
                            "description": f"Retrieving information for: {personalized_query}"
                        }
                    ]
                }

        # Fallback for unmatched queries
        return {"message": "Sorry, I can't do that yet. This feature will be available soon."}

    def perform_operations(self, input_data):
        """
        Process input (query or JSON file path) and perform operations.
        """
        try:
            # Check if input is a JSON file path
            if isinstance(input_data, str) and os.path.exists(input_data):
                with open(input_data, 'r', encoding='utf-8') as f:
                    content = f.read().strip()
            else:
                # Assume input is a query and preprocess it
                content = json.dumps(self.preprocess_query(input_data))

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
