import sys
import warnings
import json
from datetime import datetime
from crewai import Crew, Process
from agent_demo.crew import DynamicProjectCrew

warnings.filterwarnings("ignore", category=SyntaxWarning, module="pysbd")

def run():
    """Main function to run the dynamic project crew"""
    # Test case; will be replaced with user input later
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
        
        # Step 1: Analyze the project
        print("📋 Step 1: Analyzing project requirements...")
        analysis_crew = Crew(
            agents=[crew_instance.analyzer()],
            tasks=[crew_instance.analyze_project()],
            process=Process.sequential,
            verbose=True
        )
        
        analysis_result = analysis_crew.kickoff(inputs={"input": user_request})
        
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
        print("- Ensure OpenAI API key is set in .env")

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