"""Integration tests for US-P0-4: Stub STT Round-Trip.

AC: utterance_end → transcript{role:user} event returned to FE.
AC: transcript text matches the stub STT fixed string.
"""
from __future__ import annotations

from starlette.testclient import TestClient

from main import app
from orchestrator.stub_stt import STUB_TRANSCRIPT


def _reach_listening(ws) -> str:
    session_id = ws.receive_json()["session_id"]
    ws.send_json({"event": "language_select", "session_id": session_id, "language": "en"})
    for _ in range(10):
        frame = ws.receive_json()
        if frame.get("event") == "state_change" and frame.get("state") == "LISTENING":
            return session_id
    raise AssertionError("Did not reach LISTENING state")


def test_utterance_end_returns_user_transcript():
    with TestClient(app) as client:
        with client.websocket_connect("/ws") as ws:
            session_id = _reach_listening(ws)

            ws.send_json({"event": "utterance_end", "session_id": session_id})

            thinking = ws.receive_json()
            transcript = ws.receive_json()

    assert thinking["event"] == "state_change"
    assert thinking["state"] == "THINKING"
    assert transcript["event"] == "transcript"
    assert transcript["role"] == "user"
    assert transcript["text"] == STUB_TRANSCRIPT
    assert transcript["session_id"] == session_id


def test_utterance_end_transcript_renders_fixed_text():
    """Stub always returns the same text regardless of session language."""
    with TestClient(app) as client:
        with client.websocket_connect("/ws") as ws:
            session_id = ws.receive_json()["session_id"]
            ws.send_json({"event": "language_select", "session_id": session_id, "language": "vi"})
            for _ in range(10):
                frame = ws.receive_json()
                if frame.get("event") == "state_change" and frame.get("state") == "LISTENING":
                    break

            ws.send_json({"event": "utterance_end", "session_id": session_id})
            ws.receive_json()  # state_change THINKING
            transcript = ws.receive_json()

    assert transcript["event"] == "transcript"
    assert transcript["role"] == "user"
    assert transcript["text"] == STUB_TRANSCRIPT
