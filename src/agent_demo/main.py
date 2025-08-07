#!/usr/bin/env python
import sys
import warnings

from datetime import datetime

import json
from agent_demo.crew import DynamicProjectCrew

warnings.filterwarnings("ignore", category=SyntaxWarning, module="pysbd")

# This main file is intended to be a way for you to run your
# crew locally, so refrain from adding unnecessary logic into this file.
# Replace with inputs you want to test with, it will automatically
# interpolate any tasks and agents information

def run():
    user_request = "Build a responsive e-commerce dashboard with user authentication"
    
    try:
        crew = DynamicProjectCrew()
        crew.analyze_project().execute(inputs={"user_request": user_request})
        result = crew.crew().kickoff()
        print(f"\n\nFinal result: {result}")
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
