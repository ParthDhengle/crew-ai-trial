#!/usr/bin/env python
import sys
import warnings
import json
from datetime import datetime
from crewai import Crew, Process
from agent_demo.crew import DynamicProjectCrew

warnings.filterwarnings("ignore", category=SyntaxWarning, module="pysbd")

def run():
    user_request = "Build a responsive e-commerce dashboard with user authentication"
    
    try:
        # Create the crew instance
        crew_instance = DynamicProjectCrew()
        
        # Create a temporary crew for analysis
        analysis_crew = Crew(
            agents=[crew_instance.analyzer()],
            tasks=[crew_instance.analyze_project()],
            process=Process.sequential,
            verbose=2
        )
        
        # Run the analysis crew
        analysis_result = analysis_crew.kickoff(inputs={
            "user_request": user_request
        })
        
        # Create the dynamic crew based on analysis
        crew_instance._create_dynamic_crew(analysis_result)
        
        # Run the main crew
        if crew_instance.agents and crew_instance.tasks:
            main_crew = Crew(
                agents=crew_instance.agents,
                tasks=crew_instance.tasks,
                process=Process.hierarchical,
                verbose=2
            )
            result = main_crew.kickoff()
            print(f"\n\nFinal result: {result}")
        else:
            print("Failed to create dynamic crew")
    
    except Exception as e:
        raise Exception(f"Crew execution failed: {e}")
    
def train():
    """
    Train the crew for a given number of iterations.
    """
    inputs = {
        "topic": "Ai jobs",
        'current_year': str(datetime.now().year)
    }
    try:
        AgentDemo().crew().train(n_iterations=int(sys.argv[1]), filename=sys.argv[2], inputs=inputs)

    except Exception as e:
        raise Exception(f"An error occurred while training the crew: {e}")

def replay():
    """
    Replay the crew execution from a specific task.
    """
    try:
        AgentDemo().crew().replay(task_id=sys.argv[1])

    except Exception as e:
        raise Exception(f"An error occurred while replaying the crew: {e}")

def test():
    """
    Test the crew execution and returns the results.
    """
    inputs = {
        "topic": "Ai jobs",
        "current_year": str(datetime.now().year)
    }
    
    try:
        AgentDemo().crew().test(n_iterations=int(sys.argv[1]), eval_llm=sys.argv[2], inputs=inputs)

    except Exception as e:
        raise Exception(f"An error occurred while testing the crew: {e}")
