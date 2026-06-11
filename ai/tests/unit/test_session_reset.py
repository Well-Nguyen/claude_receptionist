"""Unit tests for US-P0-7: Session Reset.

AC: Idle timer fires after SESSION_IDLE_TIMEOUT_S of no events and resets session to LANDING.
AC: _reset_session clears language, state, gen_id, and cancels active tasks.
AC: Idle timer is a no-op when the session no longer exists.
"""
from __future__ import annotations

import asyncio
import json
import uuid

import pytest

from orchestrator.state import Session, SessionState
from main import _reset_session, _idle_timer, registry


class FakeWs:
    def __init__(self):
        self.sent: list[str] = []

    async def send_text(self, text: str) -> None:
        self.sent.append(text)

    def events(self):
        return [json.loads(s) for s in self.sent]


# ---------------------------------------------------------------------------
# _reset_session
# ---------------------------------------------------------------------------

def test_reset_session_clears_language_and_state():
    session = Session(session_id="s1")
    session.language = "en"
    session.state = SessionState.LISTENING
    old_gen_id = session.gen_id

    _reset_session(session)

    assert session.state == SessionState.LANDING
    assert session.language is None
    assert session.gen_id != old_gen_id
    assert session.active_gen_task is None
    assert session.idle_timer_task is None


@pytest.mark.asyncio
async def test_reset_session_cancels_active_gen_task():
    session = Session(session_id="s1")
    session.state = SessionState.SPEAKING

    cancelled = False

    async def long_task():
        nonlocal cancelled
        try:
            await asyncio.sleep(100)
        except asyncio.CancelledError:
            cancelled = True
            raise

    task = asyncio.create_task(long_task())
    await asyncio.sleep(0)  # let task start and reach asyncio.sleep(100)
    session.active_gen_task = task

    _reset_session(session)
    await asyncio.gather(task, return_exceptions=True)

    assert cancelled
    assert session.active_gen_task is None


# ---------------------------------------------------------------------------
# _idle_timer
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_idle_timer_fires_resets_session_and_sends_landing():
    session = registry.add("timer-s1")
    session.language = "en"
    session.state = SessionState.LISTENING

    ws = FakeWs()
    await _idle_timer("timer-s1", ws, timeout=0.05)

    assert session.state == SessionState.LANDING
    assert session.language is None

    state_events = [e for e in ws.events() if e.get("event") == "state_change"]
    assert state_events and state_events[-1]["state"] == "LANDING"

    registry.remove("timer-s1")


@pytest.mark.asyncio
async def test_idle_timer_noop_for_missing_session():
    ws = FakeWs()
    await _idle_timer("nonexistent", ws, timeout=0.01)

    assert ws.sent == []


@pytest.mark.asyncio
async def test_idle_timer_rotates_gen_id():
    session = registry.add("timer-s2")
    session.state = SessionState.LISTENING
    old_gen_id = session.gen_id

    ws = FakeWs()
    await _idle_timer("timer-s2", ws, timeout=0.05)

    assert session.gen_id != old_gen_id

    registry.remove("timer-s2")
