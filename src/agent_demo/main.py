# FILE: src/agent_demo/main.py
import sys
import warnings
import json
from datetime import datetime
from crewai import Crew, Process
from agent_demo.crew import DynamicProjectCrew

warnings.filterwarnings("ignore", category=SyntaxWarning, module="pysbd")

def run():
    """
    Main function to run the dynamic project crew
    """
    # You can modify this user request as needed
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
        
        # Step 1: Analyze the project and generate configuration
        print("📋 Step 1: Analyzing project requirements...")
        analysis_crew = Crew(
            agents=[crew_instance.analyzer()],
            tasks=[crew_instance.analyze_project()],
            process=Process.sequential,
            verbose=True
        )
        
        analysis_result = analysis_crew.kickoff(inputs={
            "input": user_request
        })
        
        # Extract the JSON output
        if hasattr(analysis_result, 'output'):
            config_json = analysis_result.output
        else:
            config_json = str(analysis_result)
        
        print("✅ Project analysis completed")
        print(f"📄 Configuration generated (first 200 chars): {config_json[:200]}...")
        
        # Step 2: Create the dynamic crew based on analysis
        print("\n🔧 Step 2: Creating dynamic crew...")
        crew_instance._create_dynamic_crew(config_json)
        
        print(f"👥 Created {len(crew_instance.agents)} agents:")
        for i, agent in enumerate(crew_instance.agents, 1):
            print(f"   {i}. {agent.role}")
        
        print(f"📋 Created {len(crew_instance.tasks)} tasks:")
        for i, task in enumerate(crew_instance.tasks, 1):
            print(f"   {i}. {task.description[:60]}...")
        
        # Step 3: Execute the main crew
        if crew_instance.agents and crew_instance.tasks:
            print("\n🚀 Step 3: Executing main project crew...")
            
            main_crew = crew_instance.crew()
            if main_crew:
                result = main_crew.kickoff()
                print(f"\n✅ Project execution completed successfully!")
                print(f"📊 Final result: {result}")
                
                # Save results summary
                save_execution_summary(crew_instance, result)
            else:
                print("❌ Failed to create main crew")
        else:
            print("❌ No agents or tasks were created from the analysis")
    
    except Exception as e:
        import traceback
        print(f"\n❌ Error occurred during execution:")
        print(f"Error: {str(e)}")
        traceback.print_exc()
        print("\n🔍 Debugging information:")
        print(f"- Check if the project_config.json was created properly")
        print(f"- Verify all tool dependencies are installed")
        print(f"- Ensure OpenAI API key is set in .env file")


def save_execution_summary(crew_instance, result):
    """Save a summary of the execution"""
    try:
        summary = {
            "project_type": crew_instance.project_type,
            "execution_timestamp": datetime.now().isoformat(),
            "agents_created": len(crew_instance.agents),
            "tasks_executed": len(crew_instance.tasks),
            "agent_roles": [agent.role for agent in crew_instance.agents],
            "final_result": str(result)[:500]  # Truncate for readability
        }
        
        with open("execution_summary.json", "w") as f:
            json.dump(summary, f, indent=2)
        
        print("📄 Execution summary saved to execution_summary.json")
    except Exception as e:
        print(f"Warning: Could not save execution summary: {e}")


def train():
    """
    Train the crew for a given number of iterations.
    """
    inputs = {
        "topic": "AI jobs",
        'current_year': str(datetime.now().year)
    }
    try:
        # Note: You'll need to implement a proper training setup
        print("Training functionality not implemented for dynamic crews yet")
        
    except Exception as e:
        raise Exception(f"An error occurred while training the crew: {e}")


def replay():
    """
    Replay the crew execution from a specific task.
    """
    try:
        # Note: You'll need to implement replay functionality
        print("Replay functionality not implemented for dynamic crews yet")
        
    except Exception as e:
        raise Exception(f"An error occurred while replaying the crew: {e}")


def test():
    """
    Test the crew execution and returns the results.
    """
    try:
        # Note: You'll need to implement testing functionality
        print("Test functionality not implemented for dynamic crews yet")
        
    except Exception as e:
        raise Exception(f"An error occurred while testing the crew: {e}")


if __name__ == "__main__":
    run()