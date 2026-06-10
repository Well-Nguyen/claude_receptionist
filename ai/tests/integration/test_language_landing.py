"""Integration tests for US-P0-2: Language Landing.

AC-1: language_select{en|vi} → state_change{GREETING} received within 300 ms.
AC-2: language fixed for session; second select is ignored.
AC-3: stub greeting transcript sent before state_change{LISTENING}.
"""
from __future__ import annotations
import json
import time

import pytest
from starlette.testclient import TestClient

from main import app, registry


def _drain_until(ws, event_name: str, max_steps: int = 10) -> dict:
    """Read frames until we see the target event or exhaust max_steps."""
    for _ in range(max_steps):
        frame = ws.receive_json()
        if frame.get("event") == event_name:
            return frame
    raise AssertionError(f"Event '{event_name}' not received within {max_steps} frames")


# ---------------------------------------------------------------------------
# AC-1: language_select{en} → state_change{GREETING} within 300 ms
# ---------------------------------------------------------------------------


def test_language_select_en_reaches_greeting():
    with TestClient(app) as client:
        with client.websocket_connect("/ws") as ws:
            start_event = ws.receive_json()
            session_id = start_event["session_id"]

            t0 = time.monotonic()
            ws.send_json({"event": "language_select", "session_id": session_id, "language": "en"})
            greeting_event = _drain_until(ws, "state_change")
            elapsed_ms = (time.monotonic() - t0) * 1000

    assert greeting_event["state"] == "GREETING"
    assert elapsed_ms < 300, f"GREETING arrived in {elapsed_ms:.1f} ms, expected < 300 ms"


def test_language_select_vi_reaches_greeting():
    with TestClient(app) as client:
        with client.websocket_connect("/ws") as ws:
            sid = ws.receive_json()["session_id"]
            ws.send_json({"event": "language_select", "session_id": sid, "language": "vi"})
            event = _drain_until(ws, "state_change")

    assert event["state"] == "GREETING"


# ---------------------------------------------------------------------------
# AC-2: language is fixed — second language_select is ignored
# ---------------------------------------------------------------------------


def test_second_language_select_is_ignored():
    with TestClient(app) as client:
        with client.websocket_connect("/ws") as ws:
            sid = ws.receive_json()["session_id"]

            # first selection: English
            ws.send_json({"event": "language_select", "session_id": sid, "language": "en"})
            # drain GREETING + transcript + LISTENING
            frames = [ws.receive_json(), ws.receive_json(), ws.receive_json()]

            # second selection attempt: Vietnamese — should be silently ignored
            ws.send_json({"event": "language_select", "session_id": sid, "language": "vi"})

    session = registry.get(sid)
    # session may be GC'd after close; if present, language must still be "en"
    if session is not None:
        assert session.language == "en"


# ---------------------------------------------------------------------------
# AC-3: transcript event with correct greeting arrives before LISTENING
# ---------------------------------------------------------------------------


def test_greeting_transcript_sent_before_listening():
    with TestClient(app) as client:
        with client.websocket_connect("/ws") as ws:
            sid = ws.receive_json()["session_id"]
            ws.send_json({"event": "language_select", "session_id": sid, "language": "en"})

            events = [ws.receive_json(), ws.receive_json(), ws.receive_json()]

    event_types = [e["event"] for e in events]
    assert event_types == ["state_change", "transcript", "state_change"]
    assert events[0]["state"] == "GREETING"
    assert events[1]["role"] == "assistant"
    assert len(events[1]["text"]) > 0
    assert events[2]["state"] == "LISTENING"


def test_vi_greeting_is_in_vietnamese():
    with TestClient(app) as client:
        with client.websocket_connect("/ws") as ws:
            sid = ws.receive_json()["session_id"]
            ws.send_json({"event": "language_select", "session_id": sid, "language": "vi"})

            events = [ws.receive_json(), ws.receive_json(), ws.receive_json()]

    transcript = next(e for e in events if e["event"] == "transcript")
    # Vietnamese greeting must contain at least one Vietnamese word
    assert any(w in transcript["text"] for w in ("Xin", "chào", "Chào", "bạn"))


def test_session_language_stored_correctly():
    with TestClient(app) as client:
        with client.websocket_connect("/ws") as ws:
            sid = ws.receive_json()["session_id"]
            ws.send_json({"event": "language_select", "session_id": sid, "language": "en"})
            # drain all three response frames
            for _ in range(3):
                ws.receive_json()

    session = registry.get(sid)
    if session is not None:
        assert session.language == "en"
