from __future__ import annotations
import asyncio
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


SESSION_GC_TIMEOUT = 5.0   # seconds after disconnect before eviction
SESSION_GC_INTERVAL = 1.0  # polling interval for the GC loop


class SessionState(str, Enum):
    LANDING = "LANDING"
    GREETING = "GREETING"
    LISTENING = "LISTENING"
    THINKING = "THINKING"
    SPEAKING = "SPEAKING"


@dataclass
class Session:
    session_id: str
    language: Optional[str] = None
    state: SessionState = SessionState.LANDING
    gen_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    disconnected_at: Optional[float] = None  # monotonic timestamp, None = connected


class SessionRegistry:
    def __init__(self) -> None:
        self._sessions: dict[str, Session] = {}

    # --- public API ---

    def add(self, session_id: str) -> Session:
        session = Session(session_id=session_id)
        self._sessions[session_id] = session
        return session

    def get(self, session_id: str) -> Session | None:
        return self._sessions.get(session_id)

    def mark_disconnected(self, session_id: str) -> None:
        session = self._sessions.get(session_id)
        if session and session.disconnected_at is None:
            session.disconnected_at = time.monotonic()

    def remove(self, session_id: str) -> None:
        self._sessions.pop(session_id, None)

    def __len__(self) -> int:
        return len(self._sessions)

    def __contains__(self, session_id: str) -> bool:
        return session_id in self._sessions

    # --- GC loop ---

    async def gc_loop(self) -> None:
        """Background task: evict sessions that have been disconnected > SESSION_GC_TIMEOUT."""
        while True:
            await asyncio.sleep(SESSION_GC_INTERVAL)
            self._evict_stale()

    def _evict_stale(self) -> list[str]:
        now = time.monotonic()
        stale = [
            sid
            for sid, s in self._sessions.items()
            if s.disconnected_at is not None
            and (now - s.disconnected_at) >= SESSION_GC_TIMEOUT
        ]
        for sid in stale:
            del self._sessions[sid]
        return stale
