import asyncio
import uuid
from typing import Dict, Any, List
from collections import defaultdict
# In-memory operation store: op_id -> operation dict
OP_STORE: Dict[str, Dict[str, Any]] = {}
# session_id -> list of asyncio.Queues used by SSE connections
SESSION_QUEUES: Dict[str, List[asyncio.Queue]] = defaultdict(list)
OP_LOCK = asyncio.Lock()
async def queue_operation_local(name: str, parameters: dict, session_id: str) -> str:
    """Create an operation entry in local in-memory store and return op_id."""
    async with OP_LOCK:
        op_id = str(uuid.uuid4())
        op = {
            "id": op_id,
            "name": name,
            "title": name,
            "description": parameters.get("summary", "") if parameters else "",
            "parameters": parameters or {},
            "session_id": session_id,
            "status": "pending",
            "createdAt": None, # fill with iso if you want
            "startedAt": None,
            "completedAt": None,
            "progress": 0,
            "result": None,
        }
        OP_STORE[op_id] = op
        # publish an initial event for the session so SSE clients see the op
        await publish_event(session_id, {"type": "op_created", "operation": op})
        return op_id
async def update_operation_local(op_id: str, status: str = None, result: Any = None, extra_fields: dict = None):
    """Update operation entry and notify subscribers."""
    async with OP_LOCK:
        op = OP_STORE.get(op_id)
        if not op:
            return None
        if status:
            op["status"] = status
        if result is not None:
            op["result"] = result
        if extra_fields:
            op.update(extra_fields)
        # publish update
        await publish_event(op["session_id"], {"type": "op_updated", "operation": op})
        return op
async def get_operation_local(op_id: str):
    async with OP_LOCK:
        return OP_STORE.get(op_id)
# SSE helpers
async def publish_event(session_id: str, payload: dict):
    """Put a payload into all SSE queues for this session_id."""
    queues = SESSION_QUEUES.get(session_id, [])
    for q in queues:
        # make non-blocking put
        try:
            q.put_nowait(payload)
        except asyncio.QueueFull:
            # if queue full, drop (or handle accordingly)
            pass
async def register_sse_queue(session_id: str, queue: asyncio.Queue):
    SESSION_QUEUES[session_id].append(queue)
async def unregister_sse_queue(session_id: str, queue: asyncio.Queue):
    if queue in SESSION_QUEUES.get(session_id, []):
        SESSION_QUEUES[session_id].remove(queue)
        if not SESSION_QUEUES[session_id]:
            del SESSION_QUEUES[session_id]