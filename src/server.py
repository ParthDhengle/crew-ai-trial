import os
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from agent_demo.crew import AiAgent
from datetime import datetime
import uvicorn

app = FastAPI(title="Contextual AI Backend")

class QueryRequest(BaseModel):
    query: str

@app.post("/process_query")
async def process_query(request: QueryRequest):
    if not request.query:
        raise HTTPException(400, "No query provided")

    inputs = {
        'user_query': request.query,
        'current_year': str(datetime.now().year),
        'user_preferences_path': 'knowledge/user_preference.txt',
        'operations_file_path': 'knowledge/operations.txt'
    }

    try:
        crew_instance = AiAgent()
        crew_instance.crew().kickoff(inputs=inputs)
        output = crew_instance.perform_operations("execution_plan.json")
        return {"result": output}
    except Exception as e:
        raise HTTPException(500, str(e))

if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8000)