import os
import traceback
from datetime import datetime
from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from agent_demo.crew import AiAgent

app = FastAPI(title="Contextual AI Backend")

# ----- Models -----
class QueryRequest(BaseModel):
    query: str

# ----- Routes -----
@app.post("/process_query")
async def process_query(query: QueryRequest):
    """Process a query received from the frontend."""
    if not query.query:
        raise HTTPException(status_code=400, detail="Query cannot be empty")

    print(f"\n🔍 Processing: '{query.query}'")
    print("⏳ Analyzing your request...\n")
    
    # Construct absolute paths relative to server.py
    base_dir = os.path.dirname(os.path.abspath(__file__))  # Points to src/agent_demo/
    root_dir = os.path.dirname(os.path.dirname(base_dir))  # Points to crew-ai-trial/
    
    inputs = {
        'user_query': query.query,
        'current_year': str(datetime.now().year),
        'user_preferences_path': os.path.join(root_dir, 'knowledge', 'user_preference.txt'),
        'operations_file_path': os.path.join(root_dir, 'knowledge', 'operations.txt')
    }

    try:
        crew_instance = AiAgent()
        result = crew_instance.crew().kickoff(inputs=inputs)
        
        print("\n" + "="*50)
        print("📋 ANALYSIS COMPLETE")
        print("="*50)
        
        crew_instance.perform_operations("execution_plan.json")
        
        print("="*50)
        print()
        
        return JSONResponse(content={"status": "success", "result": str(result)})
        
    except FileNotFoundError as e:
        print(f"❌ File not found: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Missing required file: {str(e)}")
    except Exception as e:
        print("❌ Error during execution — full traceback below:")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Error processing query: {str(e)}")

# ----- Entry Point -----
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000, log_level="info")