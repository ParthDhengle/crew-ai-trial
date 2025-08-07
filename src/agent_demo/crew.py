# FILE: src/agent_demo/crew.py
from crewai import Agent, Crew, Process, Task
from crewai.project import CrewBase, agent, crew, task
from typing import List, Dict, Any
import json
import re
from .tools.file_manager import FileManagerTool
from .tools.web_tools import CodeGeneratorTool, ProjectStructureTool, DatabaseTool

@CrewBase
class DynamicProjectCrew():
    """Fully dynamic project generator crew"""
    
    agents: List[Agent] = []
    tasks: List[Task] = []
    max_retries = 3
    
    def __init__(self):
        self.project_type = None
        self.agent_configs = {}
        self.task_configs = {}
        # Only register actual CrewAI tools
        self.tool_functions = {
            'FileManager': FileManagerTool,
            'file_manager': FileManagerTool,
            'CodeGenerator': CodeGeneratorTool,
            'code_generator': CodeGeneratorTool,
            'ProjectStructure': ProjectStructureTool,
            'project_structure': ProjectStructureTool,
            'Database': DatabaseTool,
            'database': DatabaseTool,
            # Add more actual tools here as needed
        }
    
    @agent
    def analyzer(self) -> Agent:
        return Agent(
            role="Project Type Analyzer",
            goal="Determine project type and required team composition",
            backstory="Expert in analyzing technical requirements and designing optimal development teams. Only uses actual CrewAI tools, not technology names.",
            verbose=True,
            allow_delegation=False
        )
    
    @task
    def analyze_project(self) -> Task:
        return Task(
            description="""Analyze the following user request and determine project type, required agents, and their configurations:
            {{input}}
            
            IMPORTANT: For tools, only use actual CrewAI tool names like 'FileManager', NOT technology names like 'HTML5', 'CSS3', 'React.js'.
            
            Output MUST be valid JSON with this structure:
            {
                "project_type": "string",
                "agents": {
                    "agent_name": {
                        "role": "string",
                        "goal": "string", 
                        "backstory": "string",
                        "tools": ["FileManager"],
                        "allow_delegation": bool,
                        "technologies": ["HTML5", "CSS3", "React.js"]
                    }
                },
                "tasks": {
                    "task_name": {
                        "description": "string",
                        "expected_output": "string",
                        "agent": "agent_name",
                        "tools": ["FileManager"],
                        "async": bool,
                        "context": ["task_names"],
                        "output_file": "string"
                    }
                }
            }""",
            expected_output="Valid JSON configuration with project type, agents, and tasks",
            agent=self.analyzer(),
            output_file="project_config.json"
        )

    
    def _create_dynamic_crew(self, config_json: str):
        """Create agents and tasks based on dynamic configuration"""
        try:
            # Parse JSON from the output
            config = self._extract_json_from_output(config_json)
                    
            self.project_type = config.get("project_type", "unknown")
            print(f"Creating dynamic crew for project type: {self.project_type}")
            
            # Create agent configurations
            self.agent_configs = config.get("agents", {})
            for agent_name, agent_cfg in self.agent_configs.items():
                # Get only valid tools
                valid_tools = self._get_valid_tools(agent_cfg.get("tools", []))
                
                agent = Agent(
                    role=agent_cfg["role"],
                    goal=agent_cfg["goal"],
                    backstory=self._enhance_backstory(agent_cfg["backstory"], 
                                                    agent_cfg.get("technologies", [])),
                    tools=valid_tools,
                    verbose=True,
                    allow_delegation=agent_cfg.get("allow_delegation", True)
                )
                setattr(self, agent_name.replace(" ", "_").lower(), agent)
                self.agents.append(agent)
            
            # Create task configurations
            self.task_configs = config.get("tasks", {})
            for task_name, task_cfg in self.task_configs.items():
                # Find the correct agent
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
            # First, try to parse the entire string as JSON
            return json.loads(output)
        except json.JSONDecodeError:
            try:
                # Try to extract JSON from markdown code block
                pattern = r'```(?:json)?\s*(\{.*\})\s*```'
                match = re.search(pattern, output, re.DOTALL)
                if match:
                    return json.loads(match.group(1))
                
                # Try to find JSON-like content without code blocks
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
            try:
                if tool_name in self.tool_functions:
                    valid_tools.append(self.tool_functions[tool_name]())
                else:
                    # Skip invalid tools silently or add FileManager as default
                    if not valid_tools:  # Add at least one tool
                        valid_tools.append(FileManagerTool())
            except Exception as e:
                print(f"Warning: Could not load tool {tool_name}: {e}")
        
        return valid_tools

    def _enhance_backstory(self, backstory: str, technologies: List[str]) -> str:
        """Enhance backstory with technology information"""
        if technologies:
            tech_str = ", ".join(technologies)
            return f"{backstory} Specializes in technologies including: {tech_str}."
        return backstory

    def _find_agent_by_name(self, agent_name: str) -> Agent:
        """Find agent by name (case insensitive, handles spaces)"""
        normalized_name = agent_name.replace(" ", "_").lower()
        
        # Try exact match first
        if hasattr(self, normalized_name):
            return getattr(self, normalized_name)
        
        # Try to find by role or partial match
        for agent in self.agents:
            if (agent.role.lower() == agent_name.lower() or 
                agent.role.replace(" ", "_").lower() == normalized_name):
                return agent
        
        # If no exact match, return the first agent as fallback
        return self.agents[0] if self.agents else None

    def _get_task_context(self, context_names: List[str]) -> List[Task]:
        """Get context from previous tasks"""
        context_tasks = []
        for context_name in context_names:
            for task in self.tasks:
                # Simple matching - you might want to improve this
                if context_name.lower() in task.description.lower():
                    context_tasks.append(task)
                    break
        return context_tasks
    
    @crew
    def crew(self) -> Crew:
        if not self.agents or not self.tasks:
            print("Warning: No agents or tasks created")
            return None
            
        return Crew(
            agents=self.agents,
            tasks=self.tasks,
            process=Process.sequential,  # Changed from hierarchical to sequential
            verbose=2
        )