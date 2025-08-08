import sys
import warnings
import json
import os
from datetime import datetime
from crewai import Crew, Process, Agent
from agent_demo.crew import DynamicProjectCrew
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

warnings.filterwarnings("ignore", category=SyntaxWarning, module="pysbd")

def get_available_model():
    """Get the first available model based on API keys"""
    models_with_keys = [
        ("openrouter/qwen/qwen3-coder:free", "OPENROUTER_API_KEY"),
        ("groq/gemma2-9b-it", "GROQ_API_KEY"),
        ("gemini/gemini-1.5-flash", "GEMINI_API_KEY"),
        ("together_ai/deepseek-ai/DeepSeek-R1-Distill-Llama-70B-free", "TOGETHERAI_API_KEY")
    ]
    
    for model, key_name in models_with_keys:
        if os.getenv(key_name):
            return model
    
    print("⚠️  Warning: No API keys found in environment variables.")
    print("Please set one of the following environment variables:")
    for model, key_name in models_with_keys:
        print(f"   - {key_name}")
    
    return "gemini/gemini-1.5-flash"  # Default fallback to free model

def create_simplified_project_config():
    """Create a simplified project configuration that follows CrewAI async rules"""
    return {
        "project_type": "E-commerce Dashboard Web Application",
        "agents": {
            "project_setup_agent": {
                "role": "Project Setup Specialist",
                "goal": "Initialize project structure and setup development environment",
                "backstory": "Expert in setting up project structures and development environments for web applications.",
                "tools": ["FileManager", "ProjectStructure"],
                "allow_delegation": True,
                "technologies": ["Node.js", "React.js", "MongoDB"]
            },
            "backend_developer": {
                "role": "Backend Developer",
                "goal": "Build secure RESTful APIs and implement business logic",
                "backstory": "Seasoned backend developer with expertise in creating robust server-side applications.",
                "tools": ["FileManager", "CodeGenerator"],
                "allow_delegation": True,
                "technologies": ["Node.js", "Express.js", "MongoDB", "JWT"]
            },
            "frontend_developer": {
                "role": "Frontend Developer", 
                "goal": "Develop responsive user interface components",
                "backstory": "Frontend specialist focused on creating modern, responsive web interfaces.",
                "tools": ["FileManager", "CodeGenerator"],
                "allow_delegation": True,
                "technologies": ["React.js", "Tailwind CSS", "Chart.js"]
            }
        },
        "tasks": {
            "setup_project": {
                "description": "Initialize project structure with proper folder organization for frontend and backend",
                "expected_output": "Complete project structure with package.json files and basic configuration",
                "agent": "project_setup_agent",
                "tools": ["FileManager", "ProjectStructure"],
                "async": False,
                "context": [],
                "output_file": "project_setup.md"
            },
            "create_backend_api": {
                "description": "Create RESTful API endpoints for product management, orders, and user authentication",
                "expected_output": "Fully functional REST API with authentication and CRUD operations",
                "agent": "backend_developer",
                "tools": ["FileManager", "CodeGenerator"],
                "async": False,
                "context": ["setup_project"],
                "output_file": "backend_api.md"
            },
            "build_frontend": {
                "description": "Implement responsive React components for the dashboard interface",
                "expected_output": "Complete set of React components for the e-commerce dashboard",
                "agent": "frontend_developer",
                "tools": ["FileManager", "CodeGenerator"],
                "async": False,  # Making all tasks synchronous for now
                "context": ["create_backend_api"],
                "output_file": "frontend_components.md"
            }
        }
    }

def run():
    """Main function to run the dynamic project crew"""
    user_request = """Build a fully responsive e-commerce dashboard web application that includes:
    - Product management (CRUD operations)
    - Order tracking and management
    - Customer management
    - Sales analytics and reporting
    - Inventory management
    - User authentication and authorization
    - Mobile-responsive design
    - API integration for payment processing
    
    The application should be modern, scalable, and follow best practices for security and performance."""
    
    try:
        print("🚀 Starting Dynamic Project Crew Analysis...")
        
        # Check for API keys
        available_model = get_available_model()
        print(f"🔑 Using model: {available_model}")
        
        crew_instance = DynamicProjectCrew()
        
        try:
            # Step 1: Try to analyze the project
            print("📋 Step 1: Analyzing project requirements...")
            analysis_result = execute_analysis(crew_instance, user_request, available_model)
            config_json = analysis_result.output if hasattr(analysis_result, 'output') else str(analysis_result)
            print("✅ Project analysis completed")
        except Exception as analysis_error:
            print(f"⚠️ Analysis failed: {analysis_error}")
            print("🔄 Using fallback simplified configuration...")
            config_json = json.dumps(create_simplified_project_config())
        
        # Step 2: Create dynamic crew
        print("\n🔧 Step 2: Creating dynamic crew...")
        try:
            crew_instance._create_dynamic_crew(config_json)
            
            print(f"👥 Created {len(crew_instance.agents)} agents:")
            for i, agent in enumerate(crew_instance.agents, 1):
                print(f"   {i}. {agent.role}")
            
            print(f"📋 Created {len(crew_instance.tasks)} tasks:")
            for i, task in enumerate(crew_instance.tasks, 1):
                async_status = " [ASYNC]" if task.async_execution else " [SYNC]"
                print(f"   {i}. {task.description[:60]}...{async_status}")
        except Exception as crew_error:
            print(f"❌ Failed to create dynamic crew: {crew_error}")
            print("🔄 Creating minimal crew...")
            create_minimal_crew(crew_instance)
        
        # Step 3: Execute main crew
        if crew_instance.agents and crew_instance.tasks:
            print("\n🚀 Step 3: Executing main project crew...")
            try:
                main_crew = crew_instance.get_main_crew()
                if main_crew:
                    print("Tasks in execution order:")
                    for i, task in enumerate(main_crew.tasks, 1):
                        async_status = " [ASYNC]" if task.async_execution else " [SYNC]"
                        print(f"   {i}. {task.description[:50]}...{async_status}")
                    
                    result = main_crew.kickoff()
                    print(f"\n✅ Project execution completed successfully!")
                    print(f"📊 Final result: {str(result)[:200]}...")
                    save_execution_summary(crew_instance, result)
                else:
                    print("❌ Failed to create main crew")
            except Exception as execution_error:
                print(f"❌ Execution failed: {execution_error}")
                print("💡 This might be due to model API limits or connectivity issues.")
        else:
            print("❌ No agents or tasks were created")
    
    except Exception as e:
        import traceback
        print(f"\n❌ Error occurred during execution: {str(e)}")
        traceback.print_exc()
        print("\n🔍 Debugging information:")
        print("- Check your API keys in .env file")
        print("- Verify internet connectivity")
        print("- Ensure CrewAI is properly installed")

def create_minimal_crew(crew_instance):
    """Create a minimal working crew as fallback"""
    try:
        from .tools.file_manager import FileManagerTool
        
        # Create minimal agent
        agent = Agent(
            role="Project Creator",
            goal="Create basic project files",
            backstory="Simple agent for creating project documentation",
            tools=[FileManagerTool()],
            verbose=True,
            allow_delegation=False,
            llm="groq/gemma2-9b-it"
        )
        crew_instance.agents = [agent]
        
        # Create minimal task
        task = Task(
            description="Create a basic project structure and README file",
            expected_output="Project documentation and basic file structure",
            agent=agent,
            tools=[FileManagerTool()],
            async_execution=False,
            output_file="minimal_project.md"
        )
        crew_instance.tasks = [task]
        
        print("✅ Created minimal fallback crew")
    except Exception as e:
        print(f"❌ Failed to create minimal crew: {e}")

def execute_analysis(crew_instance, user_request, model):
    """Execute the analysis crew with the specified model"""
    try:
        # Create analyzer with the available model
        analyzer = Agent(
            role="Project Type Analyzer",
            goal="Analyze user requests to determine project type, required agents, tasks, and optimal technologies",
            backstory="Expert in dissecting technical requirements and creating valid CrewAI configurations. Understands CrewAI async task limitations.",
            verbose=True,
            allow_delegation=False,
            llm=model
        )
        
        # Create the analysis task with updated prompt
        analysis_task = Task(
            description=f"""Analyze this request and create a valid CrewAI configuration:
            {user_request}
            
            CRITICAL CREWAI RULES:
            1. Only ONE task can have "async": true, and it must be the LAST task
            2. All other tasks must have "async": false
            3. Tasks execute in the order they appear in the JSON
            4. Use only these tools: ["FileManager", "CodeGenerator", "ProjectStructure", "Database"]
            
            Create a JSON with 3-4 agents and 3-5 tasks following these rules exactly.""",
            expected_output="Valid JSON configuration following CrewAI async task rules",
            agent=analyzer,
            async_execution=False,
            output_file="project_config.json"
        )
        
        analysis_crew = Crew(
            agents=[analyzer],
            tasks=[analysis_task],
            process=Process.sequential,
            verbose=True
        )
        
        return analysis_crew.kickoff(inputs={"input": user_request})
        
    except Exception as e:
        print(f"❌ Analysis failed with model {model}: {str(e)}")
        raise e

def save_execution_summary(crew_instance, result):
    """Save a summary of the execution"""
    try:
        summary = {
            "project_type": crew_instance.project_type,
            "execution_timestamp": datetime.now().isoformat(),
            "agents_created": len(crew_instance.agents),
            "tasks_executed": len(crew_instance.tasks),
            "agent_roles": [agent.role for agent in crew_instance.agents],
            "final_result": str(result)[:500]
        }
        with open("execution_summary.json", "w") as f:
            json.dump(summary, f, indent=2)
        print("📄 Execution summary saved to execution_summary.json")
    except Exception as e:
        print(f"Warning: Could not save execution summary: {e}")

if __name__ == "__main__":
    run()