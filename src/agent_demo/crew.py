# FILE: src/agent_demo/crew.py
from crewai import Agent, Crew, Process, Task
from crewai.project import CrewBase, agent, crew, task
from typing import List, Dict, Any
import json
from .tools.file_manager import FileManagerTool

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
        self.tool_functions = {'FileManager': FileManagerTool}
    
    @agent
    def analyzer(self) -> Agent:
        return Agent(
            role="Project Type Analyzer",
            goal="Determine project type and required team composition",
            backstory="Expert in analyzing technical requirements and designing optimal development teams",
            verbose=True,
            allow_delegation=False
        )
    
    @task
    def analyze_project(self) -> Task:
        return Task(
            description="Analyze user request and determine project type, required agents, and their configurations",
            expected_output="JSON containing project type, agent configurations, and task configurations",
            agent=self.analyzer(),
            output_file="project_config.json"
        )
    
    def _create_dynamic_crew(self, config_json: str):
        """Create agents and tasks based on dynamic configuration"""
        try:
            config = json.loads(config_json)
            self.project_type = config.get("project_type", "unknown")
            
            # Create agent configurations
            self.agent_configs = config.get("agents", {})
            for agent_name, agent_cfg in self.agent_configs.items():
                agent = Agent(
                    role=agent_cfg["role"],
                    goal=agent_cfg["goal"],
                    backstory=agent_cfg["backstory"],
                    tools=[self._get_tool(t) for t in agent_cfg.get("tools", [])],
                    verbose=True,
                    allow_delegation=agent_cfg.get("allow_delegation", True)
                )
                setattr(self, agent_name, agent)
                self.agents.append(agent)
            
            # Create task configurations
            self.task_configs = config.get("tasks", {})
            for task_name, task_cfg in self.task_configs.items():
                task = Task(
                    description=task_cfg["description"],
                    expected_output=task_cfg["expected_output"],
                    agent=getattr(self, task_cfg["agent"]),
                    tools=[self._get_tool(t) for t in task_cfg.get("tools", [])],
                    async_execution=task_cfg.get("async", False),
                    context=self._get_task_context(task_cfg.get("context", [])),
                    output_file=task_cfg.get("output_file")
                )
                self.tasks.append(task)
                
        except Exception as e:
            raise ValueError(f"Error creating dynamic crew: {str(e)}")
    
    def _get_tool(self, tool_name: str):
        """Get tool instance by name"""
        if tool_name in self.tool_functions:
            return self.tool_functions[tool_name]()
        raise ValueError(f"Tool {tool_name} not available")
    
    def _get_task_context(self, context_names: List[str]):
        """Get context from previous tasks"""
        return [t for t in self.tasks if t.config_id in context_names]
    
    @crew
    def crew(self) -> Crew:
        return Crew(
            agents=self.agents,
            tasks=self.tasks,
            process=Process.hierarchical,
            verbose=2
        )













# from crewai import Agent, Crew, Process, Task
# from crewai.project import CrewBase, agent, crew, task
# from typing import List, Dict, Any
# import json
# from .tools.file_manager import FileManagerTool  # Add this import

# @CrewBase
# class DynamicProjectCrew():
#     """Fully dynamic project generator crew"""
    
#     agents: List[Agent] = []
#     tasks: List[Task] = []
#     max_retries = 3
    
#     def __init__(self):
#         self.project_type = None
#         self.agent_configs = {}
#         self.task_configs = {}
#         self.tool_functions = {'FileManager': FileManagerTool}  # Register the tool
    
#     @agent
#     def analyzer(self) -> Agent:
#         return Agent(
#             role="Project Type Analyzer",
#             goal="Determine project type and required team composition",
#             backstory="Expert in analyzing technical requirements and designing optimal development teams",
#             verbose=True,
#             allow_delegation=False
#         )
    
#     @task
#     def analyze_project(self) -> Task:
#         return Task(
#             description="Analyze user request and determine project type, required agents, and their configurations",
#             expected_output="JSON containing project type, agent configurations, and task configurations",
#             agent=self.analyzer(),
#             output_file="project_config.json",
#             callback=self._create_dynamic_crew
#         )
    
#     def _create_dynamic_crew(self, config_json: str):
#         """Create agents and tasks based on dynamic configuration"""
#         try:
#             config = json.loads(config_json)
#             self.project_type = config.get("project_type", "unknown")
            
#             # Create agent configurations
#             self.agent_configs = config.get("agents", {})
#             for agent_name, agent_cfg in self.agent_configs.items():
#                 agent = Agent(
#                     role=agent_cfg["role"],
#                     goal=agent_cfg["goal"],
#                     backstory=agent_cfg["backstory"],
#                     tools=[self._get_tool(t) for t in agent_cfg.get("tools", [])],
#                     verbose=True,
#                     allow_delegation=agent_cfg.get("allow_delegation", True)
#                 )
#                 setattr(self, agent_name, agent)
#                 self.agents.append(agent)
            
#             # Create task configurations
#             self.task_configs = config.get("tasks", {})
#             for task_name, task_cfg in self.task_configs.items():
#                 task = Task(
#                     description=task_cfg["description"],
#                     expected_output=task_cfg["expected_output"],
#                     agent=getattr(self, task_cfg["agent"]),
#                     tools=[self._get_tool(t) for t in task_cfg.get("tools", [])],
#                     async_execution=task_cfg.get("async", False),
#                     context=self._get_task_context(task_cfg.get("context", [])),
#                     output_file=task_cfg.get("output_file"),
#                     callback=self._debug_callback if task_name == "quality_assurance" else None
#                 )
#                 self.tasks.append(task)
                
#         except Exception as e:
#             raise ValueError(f"Error creating dynamic crew: {str(e)}")
    
#     def _get_tool(self, tool_name: str):
#         """Get tool instance by name"""
#         if tool_name in self.tool_functions:
#             return self.tool_functions[tool_name]()
#         raise ValueError(f"Tool {tool_name} not available")
    
#     def _get_task_context(self, context_names: List[str]):
#         """Get context from previous tasks"""
#         return [t for t in self.tasks if t.config_id in context_names]
    
#     def _debug_callback(self):
#         """Handle debugging recursively"""
#         for i in range(self.max_retries):
#             if self._verify_build():
#                 return "Project verified successfully"
            
#             # Create debug task dynamically
#             debug_task = Task(
#                 description=f"Debug iteration {i+1}: Fix errors in {self.project_type} project",
#                 expected_output="Error-free project code",
#                 agent=self.debugger,
#                 tools=[self._get_tool("FileManager")],
#                 context=self.tasks
#             )
#             debug_task.execute()
        
#         return "Max debug iterations reached"
    
#     def _verify_build(self):
#         """Project-specific verification"""
#         # Implementation would vary by project type
#         return True  # Simplified for example
    
#     @crew
#     def crew(self) -> Crew:
#         return Crew(
#             agents=self.agents,
#             tasks=self.tasks,
#             process=Process.hierarchical,
#             manager_llm=self.manager.llm if hasattr(self, "manager") else None,
#             verbose=2
#         )