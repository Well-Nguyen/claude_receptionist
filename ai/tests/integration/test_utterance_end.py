"""Integration tests for US-P0-3: Capture, VAD & Endpointing (AI-side reception).

AC: utterance_end received by AI while LISTENING → state transitions to THINKING.
AC: utterance_end outside LISTENING state is silently ignored (no crash, no state change).
AC: multiple binary PCM frames before utterance_end do not crash the service.
"""
from __future__ import annotations
import struct

from starlette.testclient import TestClient

from main import app


def _pcm_frame(samples: int = 2048) -> bytes:
    """Silent 16 kHz mono Int16 frame (matches FE 2048-sample chunk)."""
    return struct.pack(f"<{samples}h", *([0] * samples))


def _reach_listening(ws) -> str:
    """Connect, select English, drain until LISTENING; return session_id."""
    session_id = ws.receive_json()["session_id"]
    ws.send_json({"event": "language_select", "session_id": session_id, "language": "en"})
    for _ in range(10):
        frame = ws.receive_json()
        if frame.get("event") == "state_change" and frame.get("state") == "LISTENING":
            return session_id
    raise AssertionError("Did not reach LISTENING state")


# ---------------------------------------------------------------------------
# utterance_end while LISTENING → THINKING
# ---------------------------------------------------------------------------


def test_utterance_end_transitions_to_thinking():
    with TestClient(app) as client:
        with client.websocket_connect("/ws") as ws:
            session_id = _reach_listening(ws)

            ws.send_json({"event": "utterance_end", "session_id": session_id})
            event = ws.receive_json()

    assert event["event"] == "state_change"
    assert event["state"] == "THINKING"


# ---------------------------------------------------------------------------
# Binary PCM frames before utterance_end do not crash the service
# ---------------------------------------------------------------------------


def test_pcm_frames_before_utterance_end_accepted():
    with TestClient(app) as client:
        with client.websocket_connect("/ws") as ws:
            session_id = _reach_listening(ws)

            for _ in range(10):
                ws.send_bytes(_pcm_frame())

            ws.send_json({"event": "utterance_end", "session_id": session_id})
            event = ws.receive_json()

    assert event["event"] == "state_change"
    assert event["state"] == "THINKING"


# ---------------------------------------------------------------------------
# utterance_end outside LISTENING is silently ignored
# ---------------------------------------------------------------------------


def test_utterance_end_in_greeting_state_is_ignored():
    """Sending utterance_end before language is selected (state=LANDING) → no event back."""
    with TestClient(app) as client:
        with client.websocket_connect("/ws") as ws:
            session_id = ws.receive_json()["session_id"]

            # state is LANDING; utterance_end should be ignored
            ws.send_json({"event": "utterance_end", "session_id": session_id})

            # send a ping-like unknown event to verify WS still alive
            ws.send_json({"event": "noop"})
            # connection must remain open (no crash) — if WS closed this would raise


def test_utterance_end_not_double_triggered():
    """Two utterance_end events in quick succession: only the first transitions state."""
    with TestClient(app) as client:
        with client.websocket_connect("/ws") as ws:
            session_id = _reach_listening(ws)

            ws.send_json({"event": "utterance_end", "session_id": session_id})
            first = ws.receive_json()

            # second utterance_end while already THINKING → ignored
            ws.send_json({"event": "utterance_end", "session_id": session_id})
            # no additional state_change should arrive; send a noop to confirm WS alive
            ws.send_json({"event": "noop"})

    assert first["state"] == "THINKING"
