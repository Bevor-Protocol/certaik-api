import asyncio
import hashlib
import hmac
import json
import os
from collections import defaultdict
from datetime import datetime
from typing import List

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, WebSocketException

from app.config import redis_client
from app.prometheus import prom_logger
from app.utils.logger import get_logger

secret = os.getenv("SHARED_SECRET")
logger = get_logger("websocket")


class WebsocketRouter(APIRouter):
    HEARTBEAT_INTERVAL = 5

    def __init__(self):
        super().__init__(include_in_schema=False)
        self.active_connections: list[WebSocket] = []
        self.pending_jobs: dict[str, WebSocket] = {}
        self.inverse_jobs: defaultdict[WebSocket, List[str]] = defaultdict(list)
        self.heartbeat_check = {}
        self.pubsub_task = None

        self.add_websocket_route("/ws", self.websocket)

    async def websocket(self, websocket: WebSocket):
        try:
            # await self.require_auth(websocket)
            await self.connect(websocket)

            while True:
                raw_message = await websocket.receive_text()
                logger.info(f"raw message from ws: {raw_message}")
                message = str(raw_message).strip()
                if message.startswith("subscribe:"):
                    job_id = message.split(":")[1]
                    logger.info(f"WS subscribed to job {job_id}")
                    self.assign_job(job_id, websocket)
                elif message == "PONG":
                    self.heartbeat_check[websocket] = False
        except WebSocketDisconnect:
            await self.disconnect(websocket)
        except WebSocketException as e:
            logger.error(f"WebSocket error: {e}")
            await websocket.close(code=4001)

    async def listen_to_pubsub(self):
        """
        Continuously listen to Redis pub/sub and send messages to WebSocket clients.
        """
        pubsub = redis_client.pubsub()
        await pubsub.subscribe("evals")
        try:
            while True:
                message = await pubsub.get_message(
                    ignore_subscribe_messages=True, timeout=1
                )
                if message and message["type"] == "message":
                    data = json.loads(message["data"])
                    job_id = data["job_id"]
                    logger.info(f"event received for job {job_id}")

                    websocket = self.pending_jobs.get(job_id)
                    if websocket:
                        await self.send_personal_message(data, websocket)
        except asyncio.CancelledError:
            await pubsub.unsubscribe("evals")
            await pubsub.close()
        except Exception as e:
            logger.error(f"Error in Pub/Sub listener: {e}")

    def stop_pubsub_task(self):
        """Stop the background Pub/Sub listener."""
        if self.pubsub_task:
            self.pubsub_task.cancel()

    async def require_auth(self, websocket: WebSocket):
        signature = websocket.query_params.get("signature")
        timestamp = websocket.query_params.get("timestamp")

        current_time = int(datetime.now().timestamp() * 1000)
        timestamp_int = int(timestamp)
        if abs(current_time - timestamp_int) <= 300:  # Allow a 5-minute window
            payload = f"{timestamp}:{websocket.url.path}"
            expected_signature = hmac.new(
                secret.encode(), payload.encode(), hashlib.sha256
            ).hexdigest()
            if hmac.compare_digest(signature, expected_signature):
                return
        raise WebSocketException("invalid auth")

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
        logger.info(
            "New WS connection, current connection count:"
            f" {len(self.active_connections)}"
        )
        self.heartbeat_check[websocket] = False
        asyncio.create_task(self.heartbeat(websocket))
        if len(self.active_connections) == 1:
            self.pubsub_task = asyncio.create_task(self.listen_to_pubsub())
        prom_logger.websockets.set(len(self.active_connections))

    def assign_job(self, job_id: str, websocket: WebSocket):
        self.pending_jobs[job_id] = websocket
        self.inverse_jobs[websocket].append(job_id)

    async def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
        for job_id in self.inverse_jobs[websocket]:
            self.pending_jobs.pop(job_id, None)
        self.inverse_jobs.pop(websocket, None)
        self.heartbeat_check.pop(websocket, None)
        if not self.active_connections:
            self.stop_pubsub_task()
        if websocket.client_state.name != "DISCONNECTED":
            await websocket.close()
        prom_logger.websockets.set(len(self.active_connections))

    async def send_personal_message(self, data: str, websocket: WebSocket):
        await websocket.send_json(data)

    async def heartbeat(self, websocket: WebSocket):
        while websocket in self.active_connections:
            await asyncio.sleep(self.HEARTBEAT_INTERVAL)
            try:
                if websocket.client_state.name == "DISCONNECTED":
                    return
                await self.send_personal_message({"type": "heartbeat"}, websocket)
                self.heartbeat_check[websocket] = True

                await asyncio.sleep(1)
                if self.heartbeat_check.get(websocket, False):
                    await self.disconnect(websocket)
                    break
            except Exception:
                await self.disconnect(websocket)
                break
