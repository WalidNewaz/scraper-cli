from typing import Dict, Set
from fastapi import WebSocket
from asyncio import Lock
import json

class WSManager:
    def __init__(self):
        self._connections: Dict[int, Set[WebSocket]] = {}
        self._lock = Lock()

    async def connect(self, job_id: int, ws: WebSocket):
        await ws.accept()
        async with self._lock:
            self._connections.setdefault(job_id, set()).add(ws)

    async def disconnect(self, job_id: int, ws: WebSocket):
        async with self._lock:
            if job_id in self._connections and ws in self._connections[job_id]:
                self._connections[job_id].remove(ws)

    async def broadcast(self, job_id: int, message: dict):
        data = json.dumps(message)
        async with self._lock:
            conns = list(self._connections.get(job_id, set()))
        for ws in conns:
            try:
                await ws.send_text(data)
            except Exception:
                # best-effort cleanup
                await self.disconnect(job_id, ws)
