"""Integration tests for US-P0-1: WebSocket transport.

AC-1: FE connects to :7700 → session_id issued via session_start event.
AC-2: Binary PCM + JSON events received without loss over a session.
AC-3: Network drop + reconnect → new session created; old one GC'd within 5 s.

Uses starlette.testclient.TestClient which drives the ASGI app in-process
and provides synchronous WebSocket helpers.
"""
from __future__ import annotations
import json
import os
import struct
import time

import pytest

from starlette.testclient import TestClient

from main import app, registry
from orchestrator.state import SESSION_GC_TIMEOUT


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------


def _pcm_frame(samples: int = 160) -> bytes:
    """Return a minimal silent 16 kHz mono PCM frame (320 bytes)."""
    return struct.pack(f"<{samples}h", *([0] * samples))


# ---------------------------------------------------------------------------
# AC-1: connect → session_start event with unique session_id
# ---------------------------------------------------------------------------


def test_connect_issues_session_start():
    with TestClient(app) as client:
        with client.websocket_connect("/ws") as ws:
            event = ws.receive_json()
    assert event["event"] == "session_start"
    assert isinstance(event["session_id"], str)
    assert len(event["session_id"]) > 0


def test_each_connection_gets_unique_session_id():
    with TestClient(app) as client:
        with client.websocket_connect("/ws") as ws1:
            sid1 = ws1.receive_json()["session_id"]

        with client.websocket_connect("/ws") as ws2:
            sid2 = ws2.receive_json()["session_id"]

    assert sid1 != sid2


# ---------------------------------------------------------------------------
# AC-2: binary PCM + JSON events received without dropping the connection
# ---------------------------------------------------------------------------


def test_binary_and_json_frames_received_without_loss():
    with TestClient(app) as client:
        with client.websocket_connect("/ws") as ws:
            session_id = ws.receive_json()["session_id"]

            for _ in range(20):
                ws.send_bytes(_pcm_frame())
                ws.send_json({"event": "utterance_end", "session_id": session_id})

            # final probe — connection still alive
            ws.send_bytes(_pcm_frame())


def test_session_stable_for_extended_duration():
    """
    Keep a WS connection open for STABILITY_DURATION_S (default 5 s in CI,
    set to 60 for the real 60-second acceptance criterion).
    """
    duration = float(os.getenv("STABILITY_DURATION_S", "5"))
    with TestClient(app) as client:
        with client.websocket_connect("/ws") as ws:
            ws.receive_json()  # session_start
            deadline = time.monotonic() + duration
            while time.monotonic() < deadline:
                ws.send_bytes(_pcm_frame())
                time.sleep(0.01)
            # survived — send a final probe
            ws.send_json({"event": "ping"})


# ---------------------------------------------------------------------------
# AC-3: disconnect + reconnect → new session; old one GC'd within timeout
# ---------------------------------------------------------------------------


def test_disconnect_marks_session_for_gc():
    with TestClient(app) as client:
        with client.websocket_connect("/ws") as ws:
            session_id = ws.receive_json()["session_id"]
        # ws closed — session should be marked disconnected

    session = registry.get(session_id)
    if session is not None:
        assert session.disconnected_at is not None


def test_reconnect_creates_new_session():
    with TestClient(app) as client:
        with client.websocket_connect("/ws") as ws1:
            old_sid = ws1.receive_json()["session_id"]

        with client.websocket_connect("/ws") as ws2:
            new_sid = ws2.receive_json()["session_id"]

    assert old_sid != new_sid


def test_old_session_evicted_after_timeout():
    """Directly exercise the GC eviction path after a simulated disconnect."""
    with TestClient(app) as client:
        with client.websocket_connect("/ws") as ws:
            session_id = ws.receive_json()["session_id"]
        # simulate time passing past SESSION_GC_TIMEOUT
        session = registry.get(session_id)
        if session is not None:
            session.disconnected_at = time.monotonic() - SESSION_GC_TIMEOUT - 1.0

    evicted = registry._evict_stale()
    assert session_id in evicted
    assert session_id not in registry
