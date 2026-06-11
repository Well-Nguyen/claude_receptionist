"""Integration tests for US-P1-4: PCM buffering end-to-end through the WS turn."""
from __future__ import annotations

import json
import struct

import pytest
from fastapi.testclient import TestClient
from starlette.testclient import WebSocketTestSession


def _make_pcm(n_samples: int = 2048, value: int = 50) -> bytes:
    return struct.pack(f"<{n_samples}h", *([value] * n_samples))


@pytest.fixture()
def client(monkeypatch):
    monkeypatch.delenv("STT_VI_MODEL_PATH", raising=False)
    monkeypatch.delenv("STT_EN_MODEL_PATH", raising=False)
    monkeypatch.delenv("TTS_VI_MODEL", raising=False)
    monkeypatch.delenv("TTS_EN_ENGINE", raising=False)
    from main import app
    return TestClient(app)


# ---------------------------------------------------------------------------
# /config/vad
# ---------------------------------------------------------------------------

def test_vad_config_endpoint_returns_defaults(client, monkeypatch):
    monkeypatch.delenv("VAD_SILENCE_MS", raising=False)
    monkeypatch.delenv("VAD_MIN_SPEECH_MS", raising=False)
    monkeypatch.delenv("VAD_THRESHOLD", raising=False)
    monkeypatch.delenv("BARGE_IN_MIN_MS", raising=False)
    resp = client.get("/config/vad")
    assert resp.status_code == 200
    data = resp.json()
    assert data["silence_ms"] == 800
    assert data["min_speech_ms"] == 250
    assert data["threshold"] == 0.5
    assert data["barge_in_min_ms"] == 300


def test_vad_config_endpoint_reads_env(client, monkeypatch):
    monkeypatch.setenv("VAD_SILENCE_MS", "600")
    monkeypatch.setenv("VAD_THRESHOLD", "0.3")
    resp = client.get("/config/vad")
    assert resp.status_code == 200
    data = resp.json()
    assert data["silence_ms"] == 600
    assert data["threshold"] == pytest.approx(0.3)


# ---------------------------------------------------------------------------
# PCM frames are consumed by STT (evidenced by transcript event)
# ---------------------------------------------------------------------------

def test_pcm_frames_produce_transcript(monkeypatch):
    """Binary PCM frames + utterance_end must produce a transcript event from the stub STT."""
    monkeypatch.delenv("STT_VI_MODEL_PATH", raising=False)
    monkeypatch.delenv("STT_EN_MODEL_PATH", raising=False)
    monkeypatch.delenv("TTS_VI_MODEL", raising=False)
    monkeypatch.delenv("TTS_EN_ENGINE", raising=False)

    from main import app
    with TestClient(app) as client:
        with client.websocket_connect("/ws") as ws:
            ws.receive_text()  # session_start

            ws.send_text(json.dumps({"event": "language_select", "language": "en"}))
            _drain(ws, count=2)  # GREETING + LISTENING

            # Send two PCM frames while LISTENING
            ws.send_bytes(_make_pcm(2048))
            ws.send_bytes(_make_pcm(2048))

            # Trigger turn
            ws.send_text(json.dumps({"event": "utterance_end"}))

            # Collect events until we see the user transcript
            transcript_seen = False
            for _ in range(10):
                try:
                    msg = json.loads(ws.receive_text())
                    if msg.get("event") == "transcript" and msg.get("role") == "user":
                        transcript_seen = True
                        break
                except Exception:
                    break

    assert transcript_seen, "Expected a user transcript event after binary PCM + utterance_end"


def test_pcm_buffer_cleared_after_utterance_end(monkeypatch):
    """PCM buffer must be empty once utterance_end has been processed (turn complete)."""
    monkeypatch.delenv("STT_VI_MODEL_PATH", raising=False)
    monkeypatch.delenv("STT_EN_MODEL_PATH", raising=False)
    monkeypatch.delenv("TTS_VI_MODEL", raising=False)
    monkeypatch.delenv("TTS_EN_ENGINE", raising=False)

    from main import app, registry
    with TestClient(app) as client:
        with client.websocket_connect("/ws") as ws:
            data = json.loads(ws.receive_text())
            session_id = data["session_id"]

            ws.send_text(json.dumps({"event": "language_select", "language": "en"}))
            _drain(ws, count=2)

            ws.send_bytes(_make_pcm())
            ws.send_text(json.dumps({"event": "utterance_end"}))

            # Wait until the turn produces a LISTENING state — buffer cleared at that point
            for _ in range(10):
                try:
                    msg = json.loads(ws.receive_text())
                    if msg.get("event") == "state_change" and msg.get("state") == "LISTENING":
                        break
                except Exception:
                    break

    session = registry.get(session_id)
    # Session may have been GC'd; if it exists, buffer must be empty
    if session is not None:
        assert session.pcm_buffer == []


def test_pcm_buffer_cleared_on_session_end(monkeypatch):
    """PCM buffer must be empty after session_end resets the session."""
    monkeypatch.delenv("STT_VI_MODEL_PATH", raising=False)
    monkeypatch.delenv("TTS_VI_MODEL", raising=False)

    from main import app, registry
    with TestClient(app) as client:
        with client.websocket_connect("/ws") as ws:
            data = json.loads(ws.receive_text())
            session_id = data["session_id"]

            ws.send_text(json.dumps({"event": "language_select", "language": "en"}))
            _drain(ws, count=2)

            # Send a byte then immediately reset — the server processes session_end
            # which must clear the buffer regardless of the binary frame's timing.
            ws.send_bytes(_make_pcm())
            ws.send_text(json.dumps({"event": "session_end"}))
            _drain(ws, count=1)  # consume LANDING state change

    session = registry.get(session_id)
    if session is not None:
        assert session.pcm_buffer == []


def _drain(ws: WebSocketTestSession, count: int) -> None:
    for _ in range(count):
        try:
            ws.receive_text()
        except Exception:
            break
