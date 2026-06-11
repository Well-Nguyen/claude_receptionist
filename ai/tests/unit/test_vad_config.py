"""Unit tests for US-P1-6: VAD & echo tuning — /config/vad endpoint reads env vars."""
from __future__ import annotations

import os

from starlette.testclient import TestClient

from main import app


def test_vad_config_returns_defaults():
    """/config/vad returns hard-coded defaults when no env vars are set."""
    env_keys = ["VAD_SILENCE_MS", "VAD_MIN_SPEECH_MS", "VAD_THRESHOLD", "BARGE_IN_MIN_MS"]
    clean = {k: os.environ.pop(k) for k in env_keys if k in os.environ}
    try:
        with TestClient(app) as client:
            resp = client.get("/config/vad")
        assert resp.status_code == 200
        body = resp.json()
        assert body["silence_ms"] == 800
        assert body["min_speech_ms"] == 250
        assert body["threshold"] == 0.5
        assert body["barge_in_min_ms"] == 300
    finally:
        os.environ.update(clean)


def test_vad_config_respects_env_vars(monkeypatch):
    """/config/vad returns values from env vars without code changes."""
    monkeypatch.setenv("VAD_SILENCE_MS", "600")
    monkeypatch.setenv("VAD_MIN_SPEECH_MS", "150")
    monkeypatch.setenv("VAD_THRESHOLD", "0.35")
    monkeypatch.setenv("BARGE_IN_MIN_MS", "450")

    with TestClient(app) as client:
        resp = client.get("/config/vad")

    assert resp.status_code == 200
    body = resp.json()
    assert body["silence_ms"] == 600
    assert body["min_speech_ms"] == 150
    assert body["threshold"] == 0.35
    assert body["barge_in_min_ms"] == 450


def test_vad_config_has_all_required_fields():
    """/config/vad response contains all four VAD fields."""
    with TestClient(app) as client:
        resp = client.get("/config/vad")
    body = resp.json()
    assert {"silence_ms", "min_speech_ms", "threshold", "barge_in_min_ms"} <= body.keys()
