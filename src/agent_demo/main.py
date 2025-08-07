import sys
import warnings
import json
from datetime import datetime
from crewai import Crew, Process, Agent
from agent_demo.crew import DynamicProjectCrew
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

warnings.filterwarnings("ignore", category=SyntaxWarning, module="pysbd")

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
        crew_instance = DynamicProjectCrew()
        
        # List of models to try in order
        models = [
            "openrouter/deepseek/deepseek-chat-v3-0324:free",
            "groq/gemma2-9b-it"
        ]
        
        # Step 1: Analyze the project with fallback logic
        print("📋 Step 1: Analyzing project requirements...")
        analysis_result = execute_with_fallback(crew_instance, user_request, models)
        
        config_json = analysis_result.output if hasattr(analysis_result, 'output') else str(analysis_result)
        print("✅ Project analysis completed")
        print(f"📄 Configuration generated (first 200 chars): {config_json[:200]}...")
        
        # Step 2: Create dynamic crew
        print("\n🔧 Step 2: Creating dynamic crew...")
        crew_instance._create_dynamic_crew(config_json)
        
        print(f"👥 Created {len(crew_instance.agents)} agents:")
        for i, agent in enumerate(crew_instance.agents, 1):
            print(f"   {i}. {agent.role}")
        
        print(f"📋 Created {len(crew_instance.tasks)} tasks:")
        for i, task in enumerate(crew_instance.tasks, 1):
            print(f"   {i}. {task.description[:60]}...")
        
        # Step 3: Execute main crew
        if crew_instance.agents and crew_instance.tasks:
            print("\n🚀 Step 3: Executing main project crew...")
            main_crew = crew_instance.get_main_crew()
            if main_crew:
                print("Tasks in main crew:")
                for task in main_crew.tasks:
                    print(f"- {task.description[:50]}...")
                
                result = main_crew.kickoff()
                print(f"\n✅ Project execution completed successfully!")
                print(f"📊 Final result: {result}")
                save_execution_summary(crew_instance, result)
            else:
                print("❌ Failed to create main crew")
        else:
            print("❌ No agents or tasks were created from the analysis")
    
    except Exception as e:
        import traceback
        print(f"\n❌ Error occurred during execution: {str(e)}")
        traceback.print_exc()
        print("\n🔍 Debugging information:")
        print("- Check project_config.json")
        print("- Verify tool dependencies")
        print("- Ensure API keys are set in .env")

def execute_with_fallback(crew_instance, user_request, models):
    """Execute the analysis crew with fallback to different models on rate limit errors"""
    for model in models:
        try:
            # Create a new analyzer agent with the current model
            analyzer = Agent(
                role="Project Type Analyzer",
                goal="Analyze user requests to determine project type, required agents, tasks, and optimal technologies",
                backstory="Expert in dissecting technical requirements, selecting appropriate technologies, and designing efficient development teams using crewAI tools.",
                verbose=True,
                allow_delegation=False,
                llm=model
            )
            analysis_crew = Crew(
                agents=[analyzer],
                tasks=[crew_instance.analyze_project()],
                process=Process.sequential,
                verbose=True
            )
            return analysis_crew.kickoff(inputs={"input": user_request})
        except Exception as e:
            if "rate_limit_exceeded" in str(e).lower() or "token_limit" in str(e).lower():
                print(f"Rate limit hit for {model}, trying next model")
                continue
            else:
                raise e
    raise Exception("All models hit rate limits or failed")

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