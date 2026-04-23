import json
from datetime import datetime
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from typing import List

router = APIRouter(prefix="/ws", tags=["scam-guardian"])

class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)

    async def broadcast(self, message: dict):
        """Send a message to all connected clients."""
        # Add server timestamp if not present
        if "timestamp" not in message:
            message["timestamp"] = datetime.utcnow().isoformat()
            
        disconnected_clients = []
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except Exception:
                disconnected_clients.append(connection)
        
        # Cleanup stale connections
        for client in disconnected_clients:
            self.disconnect(client)

manager = ConnectionManager()

@router.websocket("/scams")
async def websocket_endpoint(websocket: WebSocket):
    """Real-time scam event feed."""
    await manager.connect(websocket)
    try:
        # Send initial welcome message
        await websocket.send_json({"type": "CONNECTION_ESTABLISHED", "message": "Scam Guardian live feed active."})
        
        while True:
            # We don't expect client messages in this demo, but we keep the loop open
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception:
        manager.disconnect(websocket)
