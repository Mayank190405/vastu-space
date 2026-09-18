"""
VĀSTU API: Real-Time WebSocket Router
Broadcasting live pipeline progress, cluster notifications, and spatial synchronization.
"""

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from typing import List, Dict, Any
import asyncio
import json

router = APIRouter(prefix="/ws", tags=["WebSocket"])

class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)

    async def broadcast(self, message: Dict[str, Any]):
        dead = []
        for connection in self.active_connections:
            try:
                await connection.send_text(json.dumps(message))
            except Exception:
                dead.append(connection)
        for d in dead:
            self.disconnect(d)

manager = ConnectionManager()

@router.websocket("/events")
async def websocket_events(websocket: WebSocket):
    """Real-time event stream for system events, job completions, and alerts."""
    await manager.connect(websocket)
    try:
        # Acknowledge connection
        await websocket.send_text(json.dumps({
            "type": "CONNECTION_ESTABLISHED",
            "service": "vastu-event-bus",
            "timestamp": asyncio.get_event_loop().time()
        }))
        while True:
            # Keep-alive receive
            data = await websocket.receive_text()
            # Echo or process client events
            if data == "ping":
                await websocket.send_text(json.dumps({"type": "pong"}))
    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception:
        manager.disconnect(websocket)

@router.websocket("/jobs/{job_id}")
async def websocket_job_progress(websocket: WebSocket, job_id: str):
    """Real-time progress telemetry for a specific pipeline job."""
    await websocket.accept()
    try:
        from core.orchestrator.workflow_engine import _WORKFLOW_JOBS
        last_progress = -1
        while True:
            if job_id in _WORKFLOW_JOBS:
                job = _WORKFLOW_JOBS[job_id]
                if job.overall_progress_pct != last_progress:
                    last_progress = job.overall_progress_pct
                    await websocket.send_text(json.dumps(job.model_dump()))
                if job.status.value in ["COMPLETED", "FAILED", "CANCELLED"]:
                    break
            await asyncio.sleep(0.5)
    except WebSocketDisconnect:
        pass
    except Exception:
        pass
