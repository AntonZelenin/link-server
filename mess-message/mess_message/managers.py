import asyncio

from fastapi import WebSocket


class ConnectionManager:
    def __init__(self):
        self.active_connections = {}
        self.lock = asyncio.Lock()

    async def connect(self, key: str, websocket: WebSocket):
        await websocket.accept()
        await self._add(key, websocket)

    async def disconnect(self, key: str, websocket: WebSocket):
        async with self.lock:
            if key in self.active_connections:
                self.active_connections[key].remove(websocket)

    async def send_personal_message(self, recipient_username: str, message: str):
        async with self.lock:
            if recipient_username in self.active_connections:
                for connection in self.active_connections[recipient_username]:
                    await connection.send_text(message)

    async def _add(self, key: str, websocket: WebSocket):
        async with self.lock:
            if key not in self.active_connections:
                self.active_connections[key] = []

            self.active_connections[key].append(websocket)
