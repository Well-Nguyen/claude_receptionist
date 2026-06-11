"""Unit tests for US-P1-4: audio fidelity / PCM buffering."""
from __future__ import annotations

import base64
import struct
import sys
import types

import pytest


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_pcm(n_samples: int = 2048, value: int = 0) -> bytes:
    return struct.pack(f"<{n_samples}h", *([value] * n_samples))


# ---------------------------------------------------------------------------
# Session PCM buffer
# ---------------------------------------------------------------------------

def test_session_has_pcm_buffer():
    from orchestrator.state import Session
    s = Session(session_id="test-1")
    assert hasattr(s, "pcm_buffer")
    assert s.pcm_buffer == []


def test_pcm_buffer_accumulates():
    from orchestrator.state import Session
    s = Session(session_id="test-2")
    chunk1 = _make_pcm(2048)
    chunk2 = _make_pcm(2048)
    s.pcm_buffer.append(chunk1)
    s.pcm_buffer.append(chunk2)
    combined = b"".join(s.pcm_buffer)
    assert len(combined) == 2 * 2048 * 2  # 2 chunks × 2048 samples × 2 bytes


def test_pcm_buffer_clears():
    from orchestrator.state import Session
    s = Session(session_id="test-3")
    s.pcm_buffer.append(_make_pcm())
    s.pcm_buffer.clear()
    assert s.pcm_buffer == []


# ---------------------------------------------------------------------------
# STTService Protocol
# ---------------------------------------------------------------------------

def test_stub_stt_implements_protocol():
    from services.stt import STTService
    from services.model_registry import _StubSTT
    stub = _StubSTT()
    assert isinstance(stub, STTService)


def test_stub_stt_returns_string():
    from services.model_registry import _StubSTT
    stub = _StubSTT()
    result = stub.transcribe(_make_pcm())
    assert isinstance(result, str)
    assert len(result) > 0


def test_stub_stt_accepts_non_empty_pcm():
    from services.model_registry import _StubSTT
    stub = _StubSTT()
    pcm = _make_pcm(4096, value=100)
    result = stub.transcribe(pcm)
    assert isinstance(result, str)


# ---------------------------------------------------------------------------
# TTSService Protocol
# ---------------------------------------------------------------------------

def test_stub_tts_implements_protocol():
    from services.tts import TTSService
    from services.model_registry import _StubTTS
    stub = _StubTTS()
    assert isinstance(stub, TTSService)


def test_stub_tts_returns_bytes():
    from services.model_registry import _StubTTS
    stub = _StubTTS()
    result = stub.synthesize("hello")
    assert isinstance(result, bytes)
    assert len(result) > 0


def test_stub_tts_is_24khz_int16():
    """Stub TTS output length must correspond to 24 kHz Int16 PCM."""
    from services.model_registry import _StubTTS
    stub = _StubTTS()
    result = stub.synthesize("test")
    # 0.5 s × 24000 samples/s × 2 bytes/sample = 24000 bytes
    assert len(result) == 24000


# ---------------------------------------------------------------------------
# ModelRegistry stub fallback
# ---------------------------------------------------------------------------

def test_registry_uses_stub_when_no_env(monkeypatch):
    monkeypatch.delenv("STT_VI_MODEL_PATH", raising=False)
    monkeypatch.delenv("STT_EN_MODEL_PATH", raising=False)
    monkeypatch.delenv("TTS_VI_MODEL", raising=False)
    monkeypatch.delenv("TTS_EN_ENGINE", raising=False)

    from services.model_registry import ModelRegistry, _StubSTT, _StubTTS
    reg = ModelRegistry()
    reg.load()

    assert isinstance(reg.stt_for("vi"), _StubSTT)
    assert isinstance(reg.stt_for("en"), _StubSTT)
    assert isinstance(reg.tts_for("vi"), _StubTTS)
    assert isinstance(reg.tts_for("en"), _StubTTS)
    reg.close()


# ---------------------------------------------------------------------------
# VadConfigEvent schema
# ---------------------------------------------------------------------------

def test_vad_config_event_fields():
    from shared.schemas.events import VadConfigEvent
    evt = VadConfigEvent(
        silence_ms=800,
        min_speech_ms=250,
        threshold=0.5,
        barge_in_min_ms=300,
    )
    assert evt.event == "vad_config"
    assert evt.silence_ms == 800
    assert evt.threshold == 0.5
