import os
from crewai import Agent, Crew, Process, Task
from crewai.project import CrewBase, agent, task
from typing import List, Dict, Any
import json
import re
from litellm import completion
from .tools.file_manager import FileManagerTool
from .tools.web_tools import CodeGeneratorTool, ProjectStructureTool, DatabaseTool

# Define LLM functions with correct provider prefixes and API keys from environment
def deepseek_v3(messages):
    return completion(
        model="openrouter/deepseek/deepseek-chat-v3-0324:free",
        messages=messages,
        api_key=os.getenv("open_router_api_key")
    )

def qwen3(messages):
    return completion(
        model="together_ai/Qwen/Qwen3-Coder-30B-A3B-Instruct",
        messages=messages,
        api_key=os.getenv("together_api_key")
    )

def gemini(messages):
    return completion(
        model="google/gemini-1.5-flash",
        messages=messages,
        api_key=os.getenv("gemini_api_key")
    )

def groq(messages):
    return completion(
        model="groq/gemma2-9b-it",
        messages=messages,
        api_key=os.getenv("GROQ_API_KEY")
    )

# Fallback wrapper to switch LLMs on rate limit errors
def resilient_completion(primary_llm, fallback_llm, messages):
    try:
        return primary_llm(messages)
    except Exception as e:
        if "rate_limit_exceeded" in str(e).lower() or "token_limit" in str(e).lower():
            print(f"Rate limit hit for {primary_llm.__name__}, switching to {fallback_llm.__name__}")
            return fallback_llm(messages)
        else:
            raise e

@CrewBase
class DynamicProjectCrew:
    """Fully dynamic project generator crew"""
    
    agents: List[Agent] = []
    tasks: List[Task] = []
    max_retries = 3
    
    def __init__(self):
        self.project_type = None
        self.agent_configs = {}
        self.task_configs = {}
        self.tool_functions = {
            'FileManager': FileManagerTool,
            'file_manager': FileManagerTool,
            'CodeGenerator': CodeGeneratorTool,
            'code_generator': CodeGeneratorTool,
            'ProjectStructure': ProjectStructureTool,
            'project_structure': ProjectStructureTool,
            'Database': DatabaseTool,
            'database': DatabaseTool,
        }
    
    @agent
    def analyzer(self) -> Agent:
        return Agent(
            role="Project Type Analyzer",
            goal="Analyze user requests to determine project type, required agents, tasks, and optimal technologies",
            backstory="Expert in dissecting technical requirements, selecting appropriate technologies, and designing efficient development teams using crewAI tools.",
            verbose=True,
            allow_delegation=False,
            llm="openrouter/deepseek/deepseek-chat-v3-0324:free"  # Use a specific model string
        )
        
    @task
    def analyze_project(self) -> Task:
        return Task(
            description="""Analyze the following user request and determine project type, required agents, tasks, and technologies:
            {{input}}
            
            IMPORTANT:
            - For tools, use only actual crewAI tool names (e.g., 'FileManager', 'CodeGenerator').
            - Do NOT use technology names (e.g., 'React.js', 'Node.js') as tools; list them in 'technologies'.
            - Suggest the best technologies for each agent/task based on the request.
            - Ensure every agent has at least one valid tool like 'FileManager' for file operations.
            
            Output MUST be valid JSON:
            {
                "project_type": "string",
                "agents": {
                    "agent_name": {
                        "role": "string",
                        "goal": "string",
                        "backstory": "string",
                        "tools": ["FileManager", "CodeGenerator"],
                        "allow_delegation": bool,
                        "technologies": ["React.js", "Node.js"]
                    }
                },
                "tasks": {
                    "task_name": {
                        "description": "string",
                        "expected_output": "string",
                        "agent": "agent_name",
                        "tools": ["FileManager", "CodeGenerator"],
                        "async": bool,
                        "context": ["task_names"],
                        "output_file": "string"
                    }
                }
            }""",
            expected_output="Valid JSON configuration with project type, agents, tasks, and technologies",
            agent=self.analyzer(),
            output_file="project_config.json"
        )

    def _create_dynamic_crew(self, config_json: str):
        """Create agents and tasks based on dynamic configuration"""
        try:
            config = self._extract_json_from_output(config_json)
            self.project_type = config.get("project_type", "unknown")
            print(f"Creating dynamic crew for project type: {self.project_type}")
            
            self.agent_configs = config.get("agents", {})
            for agent_name, agent_cfg in self.agent_configs.items():
                valid_tools = self._get_valid_tools(agent_cfg.get("tools", []))
                
                # Assign LLMs based on agent role
                if "Developer" in agent_cfg["role"]:
                    # Use Qwen for development tasks with fallback to Gemini
                    agent_llm = lambda messages: resilient_completion(qwen3, gemini, messages)
                elif "Database" in agent_cfg["role"]:
                    # Use Gemini for database tasks with fallback to Groq
                    agent_llm = lambda messages: resilient_completion(gemini, groq, messages)
                else:
                    # Default to DeepSeek with fallback to Groq
                    agent_llm = lambda messages: resilient_completion(deepseek_v3, groq, messages)
                
                agent = Agent(
                    role=agent_cfg["role"],
                    goal=agent_cfg["goal"],
                    backstory=self._enhance_backstory(agent_cfg["backstory"], agent_cfg.get("technologies", [])),
                    tools=valid_tools,
                    verbose=True,
                    allow_delegation=agent_cfg.get("allow_delegation", True),
                    llm=agent_llm
                )
                setattr(self, agent_name.replace(" ", "_").lower(), agent)
                self.agents.append(agent)
            
            self.task_configs = config.get("tasks", {})
            for task_name, task_cfg in self.task_configs.items():
                agent_name = task_cfg["agent"]
                target_agent = self._find_agent_by_name(agent_name)
                if target_agent:
                    valid_tools = self._get_valid_tools(task_cfg.get("tools", []))
                    task = Task(
                        description=task_cfg["description"],
                        expected_output=task_cfg["expected_output"],
                        agent=target_agent,
                        tools=valid_tools,
                        async_execution=task_cfg.get("async", False),
                        context=self._get_task_context(task_cfg.get("context", [])),
                        output_file=task_cfg.get("output_file") if task_cfg.get("output_file") != "undefined" else None
                    )
                    self.tasks.append(task)
                else:
                    print(f"Warning: Agent '{agent_name}' not found for task '{task_name}'")
                
        except Exception as e:
            import traceback
            traceback.print_exc()
            raise ValueError(f"Error creating dynamic crew: {str(e)}")

    def _extract_json_from_output(self, output: str) -> dict:
        """Extract JSON from various output formats"""
        try:
            return json.loads(output)
        except json.JSONDecodeError:
            try:
                pattern = r'```(?:json)?\s*(\{.*\})\s*```'
                match = re.search(pattern, output, re.DOTALL)
                if match:
                    return json.loads(match.group(1))
                json_pattern = r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}'
                matches = re.findall(json_pattern, output, re.DOTALL)
                for match in matches:
                    try:
                        return json.loads(match)
                    except:
                        continue
                raise ValueError("Could not find valid JSON in output")
            except Exception as e:
                raise ValueError(f"Failed to extract JSON: {str(e)}")

    def _get_valid_tools(self, tool_names: List[str]) -> List:
        """Get only valid tool instances, skip invalid ones"""
        valid_tools = []
        for tool_name in tool_names:
            if tool_name in self.tool_functions:
                valid_tools.append(self.tool_functions[tool_name]())
            else:
                if not valid_tools:
                    valid_tools.append(FileManagerTool())
        return valid_tools

    def _enhance_backstory(self, backstory: str, technologies: List[str]) -> str:
        """Enhance backstory with technology information"""
        if technologies:
            tech_str = ", ".join(technologies)
            return f"{backstory} Specializes in technologies: {tech_str}."
        return backstory

    def _find_agent_by_name(self, agent_name: str) -> Agent:
        """Find agent by name (case insensitive, handles spaces)"""
        normalized_name = agent_name.replace(" ", "_").lower()
        if hasattr(self, normalized_name):
            return getattr(self, normalized_name)
        for agent in self.agents:
            if (agent.role.lower() == agent_name.lower() or 
                agent.role.replace(" ", "_").lower() == normalized_name):
                return agent
        return self.agents[0] if self.agents else None

    def _get_task_context(self, context_names: List[str]) -> List[Task]:
        """Get context from previous tasks"""
        context_tasks = []
        for context_name in context_names:
            for task in self.tasks:
                if context_name.lower() in task.description.lower():
                    context_tasks.append(task)
                    break
        return context_tasks
    
    def get_main_crew(self) -> Crew:
        """Create the main crew with dynamic agents and tasks"""
        
        if not self.agents or not self.tasks:
            print("Warning: No agents or tasks created")
            return None
        return Crew(
            agents=self.agents,
            tasks=self.tasks,
            process=Process.sequential,
            verbose=True
        )