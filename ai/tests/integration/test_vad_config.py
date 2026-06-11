"""Integration tests for US-P1-6: VAD & echo tuning.

AC: AI service sends vad_config event over WS after session_start.
AC: FE receives VAD config so no hardcoded defaults override it.
"""
from __future__ import annotations

import os

from starlette.testclient import TestClient

from main import app


def _collect_frames(ws, count: int) -> list[dict]:
    frames = []
    import json
    for _ in range(count):
        try:
            frames.append(ws.receive_json())
        except Exception:
            break
    return frames


def test_ws_sends_vad_config_after_session_start():
    """WS emits vad_config event immediately after session_start on connect."""
    with TestClient(app) as client:
        with client.websocket_connect("/ws") as ws:
            frames = _collect_frames(ws, 2)

    events = [f.get("event") for f in frames]
    assert "session_start" in events
    assert "vad_config" in events
    # vad_config must come right after session_start
    assert events.index("vad_config") == events.index("session_start") + 1


def test_vad_config_event_has_all_fields():
    """vad_config WS event contains silence_ms, min_speech_ms, threshold, barge_in_min_ms."""
    with TestClient(app) as client:
        with client.websocket_connect("/ws") as ws:
            frames = _collect_frames(ws, 2)

    vad_frame = next(f for f in frames if f.get("event") == "vad_config")
    assert {"silence_ms", "min_speech_ms", "threshold", "barge_in_min_ms"} <= vad_frame.keys()


def test_vad_config_event_reflects_env_vars(monkeypatch):
    """vad_config WS event values match env vars set before the session."""
    monkeypatch.setenv("VAD_SILENCE_MS", "500")
    monkeypatch.setenv("VAD_MIN_SPEECH_MS", "100")
    monkeypatch.setenv("VAD_THRESHOLD", "0.25")
    monkeypatch.setenv("BARGE_IN_MIN_MS", "200")

    with TestClient(app) as client:
        with client.websocket_connect("/ws") as ws:
            frames = _collect_frames(ws, 2)

    vad_frame = next(f for f in frames if f.get("event") == "vad_config")
    assert vad_frame["silence_ms"] == 500
    assert vad_frame["min_speech_ms"] == 100
    assert vad_frame["threshold"] == 0.25
    assert vad_frame["barge_in_min_ms"] == 200
