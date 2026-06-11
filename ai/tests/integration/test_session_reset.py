"""Integration tests for US-P0-7: Session Reset.

AC: End button tap → session_end event → LANDING state change sent to FE.
AC: After reset, session object is cleared (language None); re-selecting language works.
"""
from __future__ import annotations

from starlette.testclient import TestClient

from main import app


def _reach_listening(ws) -> str:
    session_id = ws.receive_json()["session_id"]
    ws.send_json({"event": "language_select", "session_id": session_id, "language": "en"})
    for _ in range(10):
        frame = ws.receive_json()
        if frame.get("event") == "state_change" and frame.get("state") == "LISTENING":
            return session_id
    raise AssertionError("Did not reach LISTENING")


def test_session_end_sends_landing():
    """End button tap → session_end → FE receives state_change{LANDING}."""
    with TestClient(app) as client:
        with client.websocket_connect("/ws") as ws:
            session_id = _reach_listening(ws)

            ws.send_json({"event": "session_end", "session_id": session_id, "reason": "user_end"})

            found_landing = False
            for _ in range(5):
                frame = ws.receive_json()
                if frame.get("event") == "state_change" and frame.get("state") == "LANDING":
                    found_landing = True
                    break

    assert found_landing, "Expected state_change{LANDING} after session_end"


def test_session_cleared_after_reset():
    """After session_end the session is back to LANDING; language re-select works."""
    with TestClient(app) as client:
        with client.websocket_connect("/ws") as ws:
            session_id = _reach_listening(ws)

            ws.send_json({"event": "session_end", "session_id": session_id, "reason": "user_end"})
            for _ in range(5):
                frame = ws.receive_json()
                if frame.get("event") == "state_change" and frame.get("state") == "LANDING":
                    break

            # Re-select language — should succeed because language was cleared
            ws.send_json({"event": "language_select", "session_id": session_id, "language": "vi"})
            found_listening = False
            for _ in range(10):
                frame = ws.receive_json()
                if frame.get("event") == "state_change" and frame.get("state") == "LISTENING":
                    found_listening = True
                    break

    assert found_listening, "Expected LISTENING after re-selecting language post-reset"
