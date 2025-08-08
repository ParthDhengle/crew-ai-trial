# Fixed crew.py with proper async task handling
import os
from crewai import Agent, Crew, Process, Task
from crewai.project import CrewBase, agent, task
from typing import List, Dict, Any
import json
import re
from .tools.file_manager import FileManagerTool
from .tools.web_tools import CodeGeneratorTool, ProjectStructureTool, DatabaseTool

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
    
    def _get_model_with_fallback(self, primary_model: str, fallback_models: List[str]) -> str:
        """Get the best available model based on API key availability"""
        # Check if primary model API key exists
        if "openrouter" in primary_model and os.getenv("OPENROUTER_API_KEY"):
            return primary_model
        elif "together" in primary_model and os.getenv("TOGETHERAI_API_KEY"):
            return primary_model
        elif "gemini" in primary_model and os.getenv("GEMINI_API_KEY"):
            return primary_model
        elif "groq" in primary_model and os.getenv("GROQ_API_KEY"):
            return primary_model
        elif "openai" in primary_model and os.getenv("OPENAI_API_KEY"):
            return primary_model
        
        # Try fallback models
        for fallback in fallback_models:
            if "openrouter" in fallback and os.getenv("OPENROUTER_API_KEY"):
                return fallback
            elif "together" in fallback and os.getenv("TOGETHERAI_API_KEY"):
                return fallback
            elif "gemini" in fallback and os.getenv("GEMINI_API_KEY"):
                return fallback
            elif "groq" in fallback and os.getenv("GROQ_API_KEY"):
                return fallback
            elif "openai" in fallback and os.getenv("OPENAI_API_KEY"):
                return fallback
        
        # Default fallback
        return "groq/gemma2-9b-it"
    
    @agent
    def analyzer(self) -> Agent:
        model = self._get_model_with_fallback(
            "together_ai/deepseek-ai/DeepSeek-R1-Distill-Llama-70B-free",
            ["groq/gemma2-9b-it", "gemini/gemini-1.5-flash"]
        )
        return Agent(
            role="Project Type Analyzer",
            goal="Analyze user requests to determine project type, required agents, tasks, and optimal technologies",
            backstory="Expert in dissecting technical requirements, selecting appropriate technologies, and designing efficient development teams using crewAI tools.",
            verbose=True,
            allow_delegation=False,
            llm=model
        )
        
    @task
    def analyze_project(self) -> Task:
        return Task(
            description="""Analyze the following user request and determine project type, required agents, tasks, and technologies:
            {{input}}
            
            IMPORTANT CREWAI ASYNC RULES:
            - Only ONE task can be async: true, and it must be the LAST task in the sequence
            - All other tasks must be async: false
            - Tasks will execute in the order they appear in the JSON
            
            TOOL RULES:
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
                        "async": false,  // ONLY the last task can be true
                        "context": ["task_names"],
                        "output_file": "string"
                    }
                }
            }""",
            expected_output="Valid JSON configuration with project type, agents, tasks, and technologies following CrewAI async rules",
            agent=self.analyzer(),
            output_file="project_config.json"
        )

    def _create_dynamic_crew(self, config_json: str):
        """Create agents and tasks based on dynamic configuration"""
        try:
            config = self._extract_json_from_output(config_json)
            self.project_type = config.get("project_type", "unknown")
            print(f"Creating dynamic crew for project type: {self.project_type}")
            
            # Create agents
            self.agent_configs = config.get("agents", {})
            for agent_name, agent_cfg in self.agent_configs.items():
                valid_tools = self._get_valid_tools(agent_cfg.get("tools", []))
                
                # Assign models based on agent role with proper fallbacks
                if "Developer" in agent_cfg["role"]:
                    model = self._get_model_with_fallback(
                        "openrouter/qwen/qwen3-coder:free",
                        ["groq/gemma2-9b-it", "gemini/gemini-1.5-flash"]
                    )
                elif "Database" in agent_cfg["role"]:
                    model = self._get_model_with_fallback(
                        "gemini/gemini-1.5-flash",
                        ["groq/gemma2-9b-it", "together_ai/deepseek-ai/DeepSeek-R1-Distill-Llama-70B-free"]
                    )
                else:
                    model = self._get_model_with_fallback(
                        "together_ai/deepseek-ai/DeepSeek-R1-Distill-Llama-70B-free",
                        ["groq/gemma2-9b-it", "gemini/gemini-1.5-flash"]
                    )
                
                agent = Agent(
                    role=agent_cfg["role"],
                    goal=agent_cfg["goal"],
                    backstory=self._enhance_backstory(agent_cfg["backstory"], agent_cfg.get("technologies", [])),
                    tools=valid_tools,
                    verbose=True,
                    allow_delegation=agent_cfg.get("allow_delegation", True),
                    llm=model
                )
                setattr(self, agent_name.replace(" ", "_").lower(), agent)
                self.agents.append(agent)
            
            # Create tasks with proper async handling
            self.task_configs = config.get("tasks", {})
            task_names = list(self.task_configs.keys())
            
            # Fix async task configuration - only last task can be async
            for i, (task_name, task_cfg) in enumerate(self.task_configs.items()):
                agent_name = task_cfg["agent"]
                target_agent = self._find_agent_by_name(agent_name)
                
                if target_agent:
                    valid_tools = self._get_valid_tools(task_cfg.get("tools", []))
                    
                    # Force all tasks except the last one to be synchronous
                    is_async = (i == len(task_names) - 1) and task_cfg.get("async", False)
                    
                    task = Task(
                        description=task_cfg["description"],
                        expected_output=task_cfg["expected_output"],
                        agent=target_agent,
                        tools=valid_tools,
                        async_execution=is_async,
                        context=self._get_task_context(task_cfg.get("context", [])),
                        output_file=task_cfg.get("output_file") if task_cfg.get("output_file") != "undefined" else None
                    )
                    self.tasks.append(task)
                    
                    # Log async status for debugging
                    async_status = "ASYNC" if is_async else "SYNC"
                    print(f"Task {i+1}/{len(task_names)}: {task_name} [{async_status}]")
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
        
        # Validate async task count before creating crew
        async_tasks = [task for task in self.tasks if task.async_execution]
        print(f"Async tasks count: {len(async_tasks)}")
        
        if len(async_tasks) > 1:
            print("⚠️ Warning: Multiple async tasks detected. Fixing...")
            # Make only the last task async
            for task in self.tasks[:-1]:
                task.async_execution = False
            
            if self.tasks:
                self.tasks[-1].async_execution = False  # For safety, make all sync for now
                
        return Crew(
            agents=self.agents,
            tasks=self.tasks,
            process=Process.sequential,
            verbose=True
        )