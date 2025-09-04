import os
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from .crew import AiAgent
from datetime import datetime
import uvicorn

app = FastAPI(title="Contextual AI Backend")

class QueryRequest(BaseModel):
    query: str

@app.post("/process_query")
async def process_query(request: QueryRequest):
    if not request.query:
        raise HTTPException(400, "No query provided")
    crew_instance = AiAgent()
    output = crew_instance.run_workflow(request.query)
    return {"result": output}

if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8000)