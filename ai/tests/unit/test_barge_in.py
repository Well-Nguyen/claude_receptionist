"""Unit tests for US-P0-6: Barge-In.

AC: interrupt{gen_id} cancels the active generation task and drops stale chunks.
AC: interrupt with a stale gen_id is ignored.
AC: interrupt while not SPEAKING is ignored.
"""
from __future__ import annotations

import asyncio
import uuid

import pytest

from orchestrator.state import Session, SessionState
from main import _on_interrupt, _run_generation
from shared.schemas.events import AudioChunkEvent, StateChangeEvent
from orchestrator.sentence_splitter import split_sentences


# ---------------------------------------------------------------------------
# Minimal fake websocket that records sent text frames.
# ---------------------------------------------------------------------------

class FakeWs:
    def __init__(self):
        self.sent: list[str] = []

    async def send_text(self, text: str) -> None:
        self.sent.append(text)

    def events(self):
        import json
        return [json.loads(s) for s in self.sent]


# ---------------------------------------------------------------------------
# _on_interrupt: guard conditions
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_interrupt_ignored_when_not_speaking():
    session = Session(session_id="s1")
    session.state = SessionState.LISTENING
    gen_id = session.gen_id

    # Should be a no-op — no task to cancel, state unchanged.
    await _on_interrupt("s1", {"gen_id": gen_id})
    assert session.state == SessionState.LISTENING


@pytest.mark.asyncio
async def test_interrupt_ignored_for_stale_gen_id():
    session = Session(session_id="s1")
    session.state = SessionState.SPEAKING
    session.gen_id = "current-gen"

    from orchestrator.state import SessionRegistry
    from main import registry

    registry._sessions["s1"] = session

    await _on_interrupt("s1", {"gen_id": "old-gen"})
    # State unchanged — stale interrupt ignored.
    assert session.state == SessionState.SPEAKING

    del registry._sessions["s1"]


# ---------------------------------------------------------------------------
# _run_generation: cancellation sends LISTENING and drops remaining chunks.
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_cancellation_sends_listening_state():
    from orchestrator.sentence_splitter import split_sentences
    from orchestrator.stub_llm import stub_llm

    session = Session(session_id="s1")
    session.state = SessionState.SPEAKING
    gen_id = str(uuid.uuid4())
    session.gen_id = gen_id

    reply = stub_llm("", "en")
    segments = split_sentences(reply, gen_id)

    ws = FakeWs()

    task = asyncio.create_task(
        _run_generation(session, "s1", ws, gen_id, segments, reply)
    )

    # Let the task start (reach its first asyncio.sleep(0)) before cancelling.
    # Cancelling before the coroutine body starts throws CancelledError into an
    # unstarted coroutine, which bypasses the try/except inside _run_generation.
    await asyncio.sleep(0)
    task.cancel()
    await asyncio.gather(task, return_exceptions=True)

    events = ws.events()
    state_events = [e for e in events if e.get("event") == "state_change"]
    assert state_events, "Expected at least one state_change after cancellation"
    assert state_events[-1]["state"] == "LISTENING"


@pytest.mark.asyncio
async def test_cancellation_drops_remaining_chunks():
    from orchestrator.stub_llm import stub_llm

    session = Session(session_id="s1")
    session.state = SessionState.SPEAKING
    gen_id = str(uuid.uuid4())
    session.gen_id = gen_id

    reply = stub_llm("", "en")
    segments = split_sentences(reply, gen_id)
    assert len(segments) >= 3

    ws = FakeWs()

    task = asyncio.create_task(
        _run_generation(session, "s1", ws, gen_id, segments, reply)
    )

    # Let exactly one chunk through, then cancel.
    await asyncio.sleep(0)   # lets the task reach its first asyncio.sleep(0)
    await asyncio.sleep(0)   # lets the task send chunk 0
    task.cancel()
    await asyncio.gather(task, return_exceptions=True)

    events = ws.events()
    chunks = [e for e in events if e.get("event") == "audio_chunk"]
    # Fewer than all segments should have been sent.
    assert len(chunks) < len(segments)


@pytest.mark.asyncio
async def test_stale_gen_id_check_stops_generation():
    """If gen_id rotates (new turn) while task runs, remaining chunks are skipped."""
    from orchestrator.stub_llm import stub_llm

    session = Session(session_id="s1")
    session.state = SessionState.SPEAKING
    gen_id = str(uuid.uuid4())
    session.gen_id = gen_id

    reply = stub_llm("", "en")
    segments = split_sentences(reply, gen_id)

    ws = FakeWs()

    async def rotate_gen_id():
        await asyncio.sleep(0)
        session.gen_id = str(uuid.uuid4())  # rotate mid-generation

    task = asyncio.create_task(
        _run_generation(session, "s1", ws, gen_id, segments, reply)
    )
    await asyncio.gather(task, rotate_gen_id())

    events = ws.events()
    chunks = [e for e in events if e.get("event") == "audio_chunk"]
    # Only chunks sent before the gen_id rotated should appear.
    assert len(chunks) < len(segments)
