import asyncio
import json
import logging
from collections import defaultdict

from fastapi import WebSocket
from redis.asyncio import Redis

from app.database.config import settings


logger = logging.getLogger(__name__)


class ConnectionManager:
    """Broadcast room events locally and, when configured, across Redis-backed instances."""

    def __init__(self) -> None:
        self.active_connections: dict[int, set[WebSocket]] = defaultdict(set)
        self.redis: Redis | None = None
        self.pubsub = None
        self.listener_task: asyncio.Task | None = None

    async def start(self) -> None:
        if not settings.redis_url:
            return
        try:
            self.redis = Redis.from_url(settings.redis_url, decode_responses=True)
            await self.redis.ping()
            self.pubsub = self.redis.pubsub()
            await self.pubsub.psubscribe("havruta:room:*")
            self.listener_task = asyncio.create_task(self._listen())
            logger.info("Redis room-chat broadcasting is enabled.")
        except Exception:
            logger.exception("Redis is unavailable; room chat will use this server instance only.")
            await self._close_redis()

    async def stop(self) -> None:
        if self.listener_task:
            self.listener_task.cancel()
            try:
                await self.listener_task
            except asyncio.CancelledError:
                pass
            self.listener_task = None
        await self._close_redis()

    async def _close_redis(self) -> None:
        if self.pubsub:
            await self.pubsub.aclose()
            self.pubsub = None
        if self.redis:
            await self.redis.aclose()
            self.redis = None

    def connect(self, room_id: int, websocket: WebSocket) -> None:
        self.active_connections[room_id].add(websocket)

    def disconnect(self, room_id: int, websocket: WebSocket) -> None:
        connections = self.active_connections.get(room_id)
        if not connections:
            return
        connections.discard(websocket)
        if not connections:
            self.active_connections.pop(room_id, None)

    async def broadcast(self, room_id: int, payload: dict) -> None:
        serialized = json.dumps(payload, ensure_ascii=False, default=str)
        if self.redis:
            try:
                await self.redis.publish(f"havruta:room:{room_id}", serialized)
                return
            except Exception:
                logger.exception("Redis publish failed; sending the room event locally.")
        await self._send_local(room_id, serialized)

    async def _listen(self) -> None:
        if not self.pubsub:
            return
        try:
            async for event in self.pubsub.listen():
                if event.get("type") != "pmessage":
                    continue
                channel = str(event.get("channel", ""))
                try:
                    room_id = int(channel.rsplit(":", 1)[-1])
                except ValueError:
                    continue
                await self._send_local(room_id, event["data"])
        except asyncio.CancelledError:
            raise
        except Exception:
            logger.exception("Redis room-chat listener stopped unexpectedly.")

    async def _send_local(self, room_id: int, serialized: str) -> None:
        stale: list[WebSocket] = []
        for connection in list(self.active_connections.get(room_id, set())):
            try:
                await connection.send_text(serialized)
            except Exception:
                stale.append(connection)
        for connection in stale:
            self.disconnect(room_id, connection)


manager = ConnectionManager()
