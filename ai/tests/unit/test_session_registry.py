"""Unit tests for SessionRegistry: add/remove, GC timeout logic."""
from __future__ import annotations
import asyncio
import time

import pytest

from orchestrator.state import Session, SessionRegistry, SESSION_GC_TIMEOUT


def test_add_creates_session():
    reg = SessionRegistry()
    session = reg.add("s1")
    assert isinstance(session, Session)
    assert session.session_id == "s1"
    assert "s1" in reg
    assert len(reg) == 1


def test_get_returns_session():
    reg = SessionRegistry()
    reg.add("s1")
    assert reg.get("s1") is not None
    assert reg.get("missing") is None


def test_mark_disconnected_sets_timestamp():
    reg = SessionRegistry()
    reg.add("s1")
    before = time.monotonic()
    reg.mark_disconnected("s1")
    after = time.monotonic()

    session = reg.get("s1")
    assert session is not None
    assert session.disconnected_at is not None
    assert before <= session.disconnected_at <= after


def test_mark_disconnected_idempotent():
    reg = SessionRegistry()
    reg.add("s1")
    reg.mark_disconnected("s1")
    first_ts = reg.get("s1").disconnected_at
    reg.mark_disconnected("s1")
    assert reg.get("s1").disconnected_at == first_ts


def test_mark_disconnected_unknown_session_is_noop():
    reg = SessionRegistry()
    reg.mark_disconnected("ghost")  # must not raise


def test_remove_deletes_session():
    reg = SessionRegistry()
    reg.add("s1")
    reg.remove("s1")
    assert "s1" not in reg
    assert len(reg) == 0


def test_remove_unknown_is_noop():
    reg = SessionRegistry()
    reg.remove("ghost")  # must not raise


def test_evict_stale_removes_timed_out_sessions():
    reg = SessionRegistry()
    reg.add("s1")
    session = reg.get("s1")
    # simulate disconnect that happened SESSION_GC_TIMEOUT + 1 seconds ago
    session.disconnected_at = time.monotonic() - SESSION_GC_TIMEOUT - 1.0

    evicted = reg._evict_stale()
    assert "s1" in evicted
    assert "s1" not in reg


def test_evict_stale_keeps_recently_disconnected_sessions():
    reg = SessionRegistry()
    reg.add("s1")
    # just disconnected — not yet expired
    reg.mark_disconnected("s1")

    evicted = reg._evict_stale()
    assert evicted == []
    assert "s1" in reg


def test_evict_stale_keeps_connected_sessions():
    reg = SessionRegistry()
    reg.add("s1")
    # disconnected_at is None → still connected

    evicted = reg._evict_stale()
    assert evicted == []
    assert "s1" in reg


@pytest.mark.asyncio
async def test_gc_loop_evicts_after_timeout():
    reg = SessionRegistry()
    reg.add("s1")
    session = reg.get("s1")
    session.disconnected_at = time.monotonic() - SESSION_GC_TIMEOUT - 1.0

    gc_task = asyncio.create_task(reg.gc_loop())
    await asyncio.sleep(1.1)  # one GC tick
    gc_task.cancel()
    try:
        await gc_task
    except asyncio.CancelledError:
        pass

    assert "s1" not in reg


@pytest.mark.asyncio
async def test_gc_loop_does_not_evict_live_sessions():
    reg = SessionRegistry()
    reg.add("s1")  # connected; disconnected_at = None

    gc_task = asyncio.create_task(reg.gc_loop())
    await asyncio.sleep(1.1)
    gc_task.cancel()
    try:
        await gc_task
    except asyncio.CancelledError:
        pass

    assert "s1" in reg
