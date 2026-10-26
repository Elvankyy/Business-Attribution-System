import asyncio
from typing import Any, Protocol

from fastapi import WebSocket
from starlette.websockets import WebSocketDisconnect


class EventPublisher(Protocol):
    async def publish(self, conversation_id: str, event: dict[str, Any]) -> None: ...


class ConnectionManager:
    def __init__(self) -> None:
        self._connections: dict[str, set[WebSocket]] = {}
        self._lock = asyncio.Lock()

    async def connect(self, conversation_id: str, websocket: WebSocket) -> None:
        async with self._lock:
            self._connections.setdefault(conversation_id, set()).add(websocket)

    async def disconnect(self, conversation_id: str, websocket: WebSocket) -> None:
        async with self._lock:
            connections = self._connections.get(conversation_id)
            if connections is None:
                return
            connections.discard(websocket)
            if not connections:
                self._connections.pop(conversation_id, None)

    async def broadcast(self, conversation_id: str, event: dict[str, Any]) -> None:
        async with self._lock:
            connections = list(self._connections.get(conversation_id, set()))

        stale: list[WebSocket] = []
        for websocket in connections:
            try:
                await websocket.send_json(event)
            except (OSError, RuntimeError, WebSocketDisconnect):
                stale.append(websocket)

        for websocket in stale:
            await self.disconnect(conversation_id, websocket)

    def connection_count(self, conversation_id: str) -> int:
        return len(self._connections.get(conversation_id, set()))


class WebSocketPublisher:
    def __init__(self, manager: ConnectionManager) -> None:
        self.manager = manager

    async def publish(self, conversation_id: str, event: dict[str, Any]) -> None:
        await self.manager.broadcast(conversation_id, event)


connection_manager = ConnectionManager()
event_publisher: EventPublisher = WebSocketPublisher(connection_manager)
