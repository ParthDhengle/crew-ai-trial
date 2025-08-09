from datetime import datetime
from agent_demo.crew import AiAgent

def run():
    user_query = input("Enter your request: ")

    inputs = {
        'user_query': user_query,
        'current_year': str(datetime.now().year),
        'user_preferences_path': 'knowledge/user_preference.txt',
        'operations_file_path': 'knowledge/operations.txt'
    }

    crew_instance = AiAgent()
    crew_instance.crew().kickoff(inputs=inputs)
    crew_instance.perform_operations("execution_plan.json")

if __name__ == "__main__":
    run()
