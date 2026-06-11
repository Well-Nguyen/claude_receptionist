"""Integration tests for US-P0-8: Latency Harness.

AC: Single turn produces structured log line with all stage timestamps.
AC: Per-turn latency summary retrievable via GET /sessions/{session_id}/latency.
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


def _do_turn(ws, session_id: str) -> None:
    ws.send_json({"event": "utterance_end", "session_id": session_id})
    for _ in range(20):
        frame = ws.receive_json()
        if frame.get("event") == "state_change" and frame.get("state") == "LISTENING":
            return
    raise AssertionError("Did not return to LISTENING after turn")


def test_single_turn_latency_record_has_be_timestamps():
    """After one turn, latency log has a record with utterance_end, stt, llm, tts fields set."""
    with TestClient(app) as client:
        with client.websocket_connect("/ws") as ws:
            session_id = _reach_listening(ws)
            _do_turn(ws, session_id)

        resp = client.get(f"/sessions/{session_id}/latency")
        assert resp.status_code == 200
        body = resp.json()
        assert body["session_id"] == session_id
        assert len(body["turns"]) == 1

        turn = body["turns"][0]
        assert turn["turn_id"] is not None
        assert turn["utterance_end_ms"] is not None
        assert turn["stt_done_ms"] is not None
        assert turn["llm_first_token_ms"] is not None
        assert turn["tts_first_audio_ms"] is not None
        # fe_first_play_ms is None until FE sends latency_report
        assert turn["fe_first_play_ms"] is None


def test_latency_report_event_fills_fe_timestamp():
    """FE latency_report event fills fe_first_play_ms on the matching turn record."""
    with TestClient(app) as client:
        with client.websocket_connect("/ws") as ws:
            session_id = _reach_listening(ws)
            _do_turn(ws, session_id)

            # Get turn_id from latency endpoint
            resp = client.get(f"/sessions/{session_id}/latency")
            turn_id = resp.json()["turns"][0]["turn_id"]

            # FE sends latency_report with fe_first_play_ms
            ws.send_json({
                "event": "latency_report",
                "session_id": session_id,
                "turn_id": turn_id,
                "fe_first_play_ms": 1234567.89,
            })

        resp = client.get(f"/sessions/{session_id}/latency")
        assert resp.status_code == 200
        turn = resp.json()["turns"][0]
        assert turn["fe_first_play_ms"] == 1234567.89


def test_three_turns_produce_three_latency_records():
    """3-turn session → per-turn latency summary shows all 3 turns."""
    with TestClient(app) as client:
        with client.websocket_connect("/ws") as ws:
            session_id = _reach_listening(ws)
            _do_turn(ws, session_id)
            _do_turn(ws, session_id)
            _do_turn(ws, session_id)

        resp = client.get(f"/sessions/{session_id}/latency")
        assert resp.status_code == 200
        body = resp.json()
        assert len(body["turns"]) == 3
        for turn in body["turns"]:
            assert turn["utterance_end_ms"] is not None
            assert turn["stt_done_ms"] is not None
            assert turn["llm_first_token_ms"] is not None
            assert turn["tts_first_audio_ms"] is not None


def test_latency_endpoint_404_for_unknown_session():
    """GET /sessions/{unknown}/latency returns 404."""
    with TestClient(app) as client:
        resp = client.get("/sessions/nonexistent-session/latency")
        assert resp.status_code == 404


def test_durations_are_ordered():
    """Timestamps must be monotonically ordered: utterance_end ≤ stt ≤ llm ≤ tts."""
    with TestClient(app) as client:
        with client.websocket_connect("/ws") as ws:
            session_id = _reach_listening(ws)
            _do_turn(ws, session_id)

        resp = client.get(f"/sessions/{session_id}/latency")
        turn = resp.json()["turns"][0]
        assert turn["utterance_end_ms"] <= turn["stt_done_ms"]
        assert turn["stt_done_ms"] <= turn["llm_first_token_ms"]
        assert turn["llm_first_token_ms"] <= turn["tts_first_audio_ms"]
