from fastapi import FastAPI, HTTPException, Depends, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional
from routes.auth import auth_router
from routes.events import events_router
from routes.tasks import tasks_router
from routes.sync import sync_router
from routes.other import other_router
from crew import AiAgent
from firebase_client import initialize_firebase
from operations_store import OP_STORE, OP_LOCK, publish_event, register_sse_queue, unregister_sse_queue
from fastapi.responses import StreamingResponse
import asyncio
from datetime import datetime
import inspect
import json 
from firebase_client import get_current_uid, db, get_user_profile, update_user_profile
from firebase_client import save_chat_message, get_chat_history    
from operations_store import queue_operation_local, update_operation_local
from typing import List
from firebase_client import complete_user_profile
# Initialize Firebase
initialize_firebase()

# FastAPI app
app = FastAPI(title="AI Assistant API")

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(auth_router)
app.include_router(events_router)
app.include_router(tasks_router)
app.include_router(sync_router)
app.include_router(other_router)

class QueryRequest(BaseModel):
    query: str
    session_id: Optional[str] = None

class OperationRequest(BaseModel):
    name: str
    parameters: dict

@app.post("/process_query")
async def process_query(request: QueryRequest, background_tasks: BackgroundTasks, uid: str = Depends(get_current_uid)):
    from firebase_client import set_user_id
    set_user_id(uid)
    try:
        timestamp = datetime.now().isoformat()
        session_id = await save_chat_message(request.session_id, uid, "user", request.query, timestamp)
        
        if not session_id:
            raise RuntimeError("Failed to create or retrieve session_id")
        
        async with OP_LOCK:
            to_delete = [oid for oid, op in list(OP_STORE.items()) if op.get('session_id') == session_id]
            for oid in to_delete:
                del OP_STORE[oid]
        await publish_event(session_id, {"type": "ops_cleared"})
        await publish_event(session_id, {
            "type": "nova_thinking",
            "message": "Nova is analyzing your request..."
        })
        
        crew_instance = AiAgent()
        result = await crew_instance.run_workflow(
            request.query,
            session_id=session_id,
            uid=uid
        )
        
        mode = result.get('mode', 'direct')
        final_response = result.get('display_response', 'No response generated.')
        
        save_result = save_chat_message(session_id, uid, "assistant", final_response, datetime.now().isoformat())
        if inspect.iscoroutine(save_result):
            await save_result
        
        if mode == 'direct':
            await publish_event(session_id, {
                "type": "direct_response",
                "message": final_response
            })
            return {
                "result": {
                    "display_response": final_response,
                    "mode": mode
                },
                "session_id": str(session_id)
            }
        else:
            operations = result.get('operations', [])
            response_ops = []
            for op in operations:
                if isinstance(op, dict) and 'name' in op:
                    response_ops.append({
                        "id": str(op.get('op_id', 'unknown')),
                        "name": str(op.get('name', 'unknown')),
                        "parameters": op.get('parameters', {})
                    })
            await publish_event(session_id, {
                "type": "agentic_mode_activated",
                "message": "Nova agentic mode activated",
                "operations_count": len(operations)
            })
            return {
                "result": {
                    "mode": "agentic",
                    "operations": response_ops,
                    "display_response": final_response,
                    "message": "Operations are being executed with real-time updates"
                },
                "session_id": str(session_id)
            }
        
    except Exception as e:
        await publish_event(session_id, {
            "type": "error",
            "message": f"Processing failed: {str(e)}"
        })
        error_response = {
            "result": {
                "mode": "error",
                "display_response": f"Processing failed: {str(e)}"
            },
            "session_id": request.session_id or "error"
        }
        raise HTTPException(status_code=500, detail=error_response)

@app.post("/operations")
async def queue_operation(request: OperationRequest, uid: str = Depends(get_current_uid)):
    op_id = await queue_operation_local(request.name, request.parameters, session_id="")
    return {"op_id": op_id}

@app.get("/operations")
async def get_operations(status: str = None, uid: str = Depends(get_current_uid)):
    ops = [op for op in OP_STORE.values() if not status or op["status"] == status]
    return ops

@app.put("/operations/{op_id}/status")
async def update_op_status(op_id: str, status: str, uid: str = Depends(get_current_uid)):
    try:
        await update_operation_local(op_id, status=status, extra_fields={"updatedBy": uid, "updatedAt": datetime.now().isoformat()})
        return {"success": True}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/profile/complete")
async def complete_profile(profile_data: dict, uid: str = Depends(get_current_uid)):
    try:
        success = complete_user_profile(uid, profile_data)
        if not success:
            raise HTTPException(status_code=500, detail="Profile completion failed")
        return {"success": True, "profile_complete": True}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/profile")
async def get_profile(uid: str = Depends(get_current_uid)):
    profile = get_user_profile(uid)
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")
    
    profile['profile_complete'] = profile.get('profile_completed', False)
    return profile

@app.put("/profile")
async def update_profile(updates: dict, uid: str = Depends(get_current_uid)):
    # Update the authenticated user's profile
    success = update_user_profile(uid, updates)
    if not success:
        raise HTTPException(status_code=500, detail="Update failed")
    return {"success": True}

@app.get("/chat_history")
async def get_chat_history_api(session_id: str = None, uid: str = Depends(get_current_uid)):
    try:
        history: List[dict] = get_chat_history(session_id, uid)
        if not isinstance(history, list):
            history = []
        for msg in history:
            iso_ts = msg.get("timestamp")
            if iso_ts:
                try:
                    msg["timestamp"] = int(datetime.fromisoformat(iso_ts).timestamp() * 1000)
                except Exception:
                    try:
                        msg["timestamp"] = int(msg["timestamp"])
                    except Exception:
                        msg["timestamp"] = None
        return history
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/chat_sessions")
async def get_chat_sessions(uid: str = Depends(get_current_uid)):
    try:
        user_ref = db.collection("users").document(uid)
        sessions_ref = user_ref.collection("chat_sessions").stream()
        session_list = []
        for session_doc in sessions_ref:
            sid = session_doc.id
            data = session_doc.to_dict() or {}
            created_at = data.get("createdAt")
            updated_at = data.get("updatedAt")
            def to_ms(v):
                if v is None:
                    return None
                if isinstance(v, str):
                    return int(datetime.fromisoformat(v).timestamp() * 1000)
                if hasattr(v, "timestamp"):
                    return int(v.timestamp() * 1000)
                try:
                    return int(v)
                except Exception:
                    return None
            created_ms = to_ms(created_at)
            updated_ms = to_ms(updated_at)
            messages = get_chat_history(sid, uid)
            summary = f"{len(messages)} messages" if isinstance(messages, list) else "0 messages"
            session_list.append({
                "id": sid,
                "title": data.get("title", "Untitled"),
                "summary": summary,
                "messages": [],
                "createdAt": created_ms,
                "updatedAt": updated_ms
            })
        session_list.sort(key=lambda s: (s["updatedAt"] is not None, s["updatedAt"] or 0), reverse=True)
        return session_list
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/chat_sessions/{session_id}")
async def delete_chat_session(session_id: str, uid: str = Depends(get_current_uid)):
    try:
        user_ref = db.collection("users").document(uid)
        session_ref = user_ref.collection("chat_sessions").document(session_id)
        messages_ref = session_ref.collection("messages")
        while True:
            docs = list(messages_ref.limit(500).stream())
            if not docs:
                break
            batch = db.batch()
            for d in docs:
                batch.delete(d.reference)
            batch.commit()
        session_ref.delete()
        return {"success": True}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/operations/stream")
async def operations_stream(session_id: str):
    async def event_generator():
        q = asyncio.Queue()
        await register_sse_queue(session_id, q)
        try:
            current_ops = [op for op in OP_STORE.values() if op.get("session_id") == session_id]
            await q.put({"type": "initial_state", "operations": current_ops})
            while True:
                payload = await q.get()
                yield f"data: {json.dumps(payload)}\n\n"
        except asyncio.CancelledError:
            pass
        finally:
            await unregister_sse_queue(session_id, q)
    return StreamingResponse(event_generator(), media_type="text/event-stream")

async def run_server():
    from uvicorn import Config, Server
    config = Config(app=app, host="127.0.0.1", port=8001, log_level="info")
    server = Server(config)
    await server.serve()

if __name__ == "__main__":
    asyncio.run(run_server())