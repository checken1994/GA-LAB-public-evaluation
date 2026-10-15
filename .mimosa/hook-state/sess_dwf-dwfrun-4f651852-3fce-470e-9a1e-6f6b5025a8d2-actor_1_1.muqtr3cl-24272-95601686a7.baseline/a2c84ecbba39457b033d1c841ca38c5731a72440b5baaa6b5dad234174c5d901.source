# SCP CIRCUIT: M05 — STATUS: CLOSED_WITH_KNOWN_GAP (closure: docs/evidence-summary/M05-closure.json)
"""Bounded in-memory WebRTC signaling relay for local SCP calls.

This module only relays signaling messages. It never stores audio/video frames,
never calls an LLM, and expires sessions automatically.
"""
from __future__ import annotations

import asyncio
import json
import logging
import secrets
import time
import uuid

logger = logging.getLogger(__name__)
from dataclasses import dataclass, field
from typing import Any

from fastapi import WebSocket, WebSocketDisconnect

_ALLOWED_TYPES = {"offer", "answer", "ice", "hangup", "ping"}
_MAX_MESSAGE_BYTES = 64 * 1024
_SESSION_TTL_SECONDS = 10 * 60
_MAX_SESSIONS = 32
_MAX_PEERS = 2


@dataclass
class _Peer:
    websocket: WebSocket
    peer_id: str
    queue: asyncio.Queue[dict[str, Any]] = field(default_factory=asyncio.Queue)


@dataclass
class _Session:
    call_id: str
    token: str
    created_at: float
    peers: dict[str, _Peer] = field(default_factory=dict)


class CallSessionHub:
    def __init__(self) -> None:
        self._sessions: dict[str, _Session] = {}
        self._lock = asyncio.Lock()

    async def create(self) -> dict[str, Any]:
        async with self._lock:
            self._prune_locked()
            if len(self._sessions) >= _MAX_SESSIONS:
                raise RuntimeError("call session capacity reached")
            call_id = uuid.uuid4().hex[:16]
            token = secrets.token_urlsafe(24)
            self._sessions[call_id] = _Session(call_id, token, time.time())
            return {
                "call_id": call_id,
                "token": token,
                "expires_in": _SESSION_TTL_SECONDS,
                "max_peers": _MAX_PEERS,
                "signaling": f"/v3/call/sessions/{call_id}/signal",
            }

    async def connect(self, call_id: str, token: str, websocket: WebSocket) -> None:
        await websocket.accept()
        async with self._lock:
            self._prune_locked()
            session = self._sessions.get(call_id)
            if not session or not secrets.compare_digest(session.token, token):
                await websocket.send_json({"type": "error", "code": "CALL_NOT_FOUND"})
                await websocket.close(code=1008)
                return
            if len(session.peers) >= _MAX_PEERS:
                await websocket.send_json({"type": "error", "code": "CALL_FULL"})
                await websocket.close(code=1008)
                return
            peer_id = secrets.token_hex(6)
            peer = _Peer(websocket, peer_id)
            session.peers[peer_id] = peer
            peer_count = len(session.peers)

        await websocket.send_json({"type": "joined", "peer_id": peer_id, "peer_count": peer_count, "expires_in": _SESSION_TTL_SECONDS})
        if peer_count == 2:
            async with self._lock:
                session = self._sessions.get(call_id)
                if session:
                    await self._broadcast_locked(session, peer_id, {"type": "peer_joined", "peer_count": peer_count})
        sender = asyncio.create_task(self._sender(peer))
        try:
            while True:
                raw = await websocket.receive_text()
                if len(raw.encode("utf-8")) > _MAX_MESSAGE_BYTES:
                    await websocket.send_json({"type": "error", "code": "SIGNAL_TOO_LARGE"})
                    continue
                try:
                    message = json.loads(raw)
                except json.JSONDecodeError as exc:
                    # silent-by-design: the peer is notified via an error frame; connection continues.
                    logger.debug("call_session_hub: invalid signaling JSON rejected: %s", exc, exc_info=True)
                    await websocket.send_json({"type": "error", "code": "SIGNAL_INVALID_JSON"})
                    continue
                if not isinstance(message, dict) or message.get("type") not in _ALLOWED_TYPES:
                    await websocket.send_json({"type": "error", "code": "SIGNAL_TYPE_NOT_ALLOWED"})
                    continue
                payload = message.get("payload")
                if payload is not None and len(json.dumps(payload, ensure_ascii=False).encode("utf-8")) > _MAX_MESSAGE_BYTES:
                    await websocket.send_json({"type": "error", "code": "SIGNAL_PAYLOAD_TOO_LARGE"})
                    continue
                if message["type"] == "ping":
                    await websocket.send_json({"type": "pong"})
                    continue
                outgoing = {"type": message["type"], "payload": payload, "from_peer": peer_id}
                await self._broadcast(call_id, peer_id, outgoing)
                if message["type"] == "hangup":
                    break
        except WebSocketDisconnect as exc:
            # silent-by-design: peer disconnect is the expected end of the receive loop.
            logger.debug("call_session_hub: peer disconnected: %s", exc, exc_info=True)
        finally:
            sender.cancel()
            async with self._lock:
                session = self._sessions.get(call_id)
                if session:
                    session.peers.pop(peer_id, None)
                    if not session.peers:
                        self._sessions.pop(call_id, None)
                    else:
                        await self._broadcast_locked(session, peer_id, {"type": "peer_left", "from_peer": peer_id})

    async def _sender(self, peer: _Peer) -> None:
        try:
            while True:
                await peer.websocket.send_json(await peer.queue.get())
        except Exception as exc:
            # silent-by-design: sender task ends when the peer socket breaks; cleanup runs in caller.
            logger.debug("call_session_hub: sender loop ended: %s", exc, exc_info=True)
            return

    async def _broadcast(self, call_id: str, sender_id: str, message: dict[str, Any]) -> None:
        async with self._lock:
            session = self._sessions.get(call_id)
            if session:
                await self._broadcast_locked(session, sender_id, message)

    @staticmethod
    async def _broadcast_locked(session: _Session, sender_id: str, message: dict[str, Any]) -> None:
        for peer_id, peer in session.peers.items():
            if peer_id != sender_id:
                try:
                    peer.queue.put_nowait(message)
                except asyncio.QueueFull as exc:
                    logger.warning("call_session_hub: signal message dropped for slow peer %s: %s", peer_id, exc, exc_info=True)
                    continue

    def _prune_locked(self) -> None:
        cutoff = time.time() - _SESSION_TTL_SECONDS
        expired = [call_id for call_id, session in self._sessions.items() if session.created_at < cutoff]
        for call_id in expired:
            self._sessions.pop(call_id, None)

    def stats(self) -> dict[str, int]:
        self._prune_locked()
        return {"active_sessions": len(self._sessions), "max_sessions": _MAX_SESSIONS, "max_peers": _MAX_PEERS}


__all__ = ["CallSessionHub"]
