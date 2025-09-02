# Modified: src/agent_demo/crew.py
# Changes: 
# - Imported RagTool
# - Added RagTool to analyzer agent's tools
# - Minor: Updated preprocess_query to use RAG fallback if needed (but primary usage is via agent)

import json
import os
import traceback
from datetime import datetime
from crewai import Agent, Crew, Process, Task, LLM
from crewai.project import CrewBase, agent, crew, task
from typing import List
from agent_demo.tools.file_manager_tool import FileManagerTool
from agent_demo.tools.operations_tool import OperationsTool
from agent_demo.tools.rag_tool import RagTool  # New import
import json5
import re

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
                tools=[FileManagerTool(), RagTool()],  # Added RagTool
                llm=self.llm,
                verbose=True
            )
        else:
            return Agent(
                config=agent_config,
                tools=[FileManagerTool(), RagTool()],  # Added RagTool
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

        # Use RAG for operations (fallback in preprocess, but agent will handle primarily)
        try:
            rag_tool = RagTool()
            relevant_ops = rag_tool._run(query)
            operations = relevant_ops.split("\n")  # Split back into list
        except Exception as e:
            print(f"Warning: Could not use RAG for operations: {e}")
            operations = []
            try:
                with open("knowledge/operations.txt", "r") as f:
                    for line in f:
                        if "|" in line and not line.startswith("#"):
                            parts = line.split("|")
                            operations.append(parts[0].strip())
            except Exception as ex:
                print(f"Warning: Could not read operations: {ex}")

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
        try:
            if isinstance(input_data, str) and os.path.exists(input_data):
                with open(input_data, 'r', encoding='utf-8') as f:
                    content = f.read().strip()
            else:
                content = json.dumps(self.preprocess_query(input_data))
            if content.startswith('"Sorry,') or content == '"Sorry, I can\'t do that yet. This feature will be available soon."':
                print(content.strip('"'))
                return
            # Enhanced cleaning:
            # 1. Remove markdown/code blocks
            content = re.sub(r'```(?:json)?\s*|\s*```', '', content).strip()
        
            # 2. Remove trailing commas (common LLM error)
            content = re.sub(r',\s*([}\]])', r'\1', content)  # Remove trailing , before } or ]
        
            # REMOVE this block - it's causing the truncation
            # match = re.search(r'\{.*?\}', content, re.DOTALL)
            # if match:
            #     content = match.group(0)
            
            # Parse with json5 (lenient: allows trailing commas, comments, etc.)
            try:
                plan = json5.loads(content)
            except Exception as e:
                print(f"❌ Lenient JSON parse failed: {e}")
                print("Raw content after cleaning:")
                print(content)
                return
            if not isinstance(plan, dict) or 'operations' not in plan:
                print("❌ Invalid execution plan format (missing 'operations')")
                return
            operations = plan.get('operations', [])
            if not operations:
                print("ℹ️ No operations to execute")
                return
            print(f"🚀 Executing {len(operations)} operation(s) using OperationsTool...\n")
            ops_tool = OperationsTool()
            raw_result = ops_tool._run(operations)
            for line in raw_result.splitlines():
                print(" " + line)
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