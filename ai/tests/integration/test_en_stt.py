"""Integration tests for US-P1-2: English STT.

Requires:
  - nemo_toolkit[asr] installed
  - STT_EN_MODEL_PATH set to a local .nemo checkpoint for parakeet-tdt-0.6b-v3

All tests skip automatically when nemo is not installed.
Model-dependent tests additionally skip when STT_EN_MODEL_PATH is unset.
"""
from __future__ import annotations

import math
import os
import struct

import pytest

nemo_asr = pytest.importorskip("nemo.collections.asr", reason="nemo not installed")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_silent_pcm(duration_s: float = 0.5, sample_rate: int = 16000) -> bytes:
    n = int(sample_rate * duration_s)
    return struct.pack(f"<{n}h", *([0] * n))


def _make_speech_like_pcm(duration_s: float = 1.0, sample_rate: int = 16000) -> bytes:
    n = int(sample_rate * duration_s)
    freq = 440
    samples = [int(16000 * math.sin(2 * math.pi * freq * i / sample_rate)) for i in range(n)]
    return struct.pack(f"<{n}h", *samples)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

@pytest.mark.skipif(
    not os.getenv("STT_EN_MODEL_PATH"),
    reason="STT_EN_MODEL_PATH not set — skipping real-model integration test",
)
def test_nemo_stt_loads_without_crashing():
    from services.stt import NeMoSTT
    device = os.getenv("STT_DEVICE", "cpu")
    svc = NeMoSTT(model_path=os.environ["STT_EN_MODEL_PATH"], device=device)
    assert svc._model is not None
    svc.close()


@pytest.mark.skipif(
    not os.getenv("STT_EN_MODEL_PATH"),
    reason="STT_EN_MODEL_PATH not set — skipping real-model integration test",
)
def test_transcribe_returns_string_for_silent_input():
    from services.stt import NeMoSTT
    device = os.getenv("STT_DEVICE", "cpu")
    svc = NeMoSTT(model_path=os.environ["STT_EN_MODEL_PATH"], device=device)
    result = svc.transcribe(_make_silent_pcm())
    assert isinstance(result, str)
    svc.close()


@pytest.mark.skipif(
    not os.getenv("STT_EN_MODEL_PATH"),
    reason="STT_EN_MODEL_PATH not set — skipping real-model integration test",
)
def test_transcribe_returns_string_for_speech_like_pcm():
    from services.stt import NeMoSTT
    device = os.getenv("STT_DEVICE", "cpu")
    svc = NeMoSTT(model_path=os.environ["STT_EN_MODEL_PATH"], device=device)
    result = svc.transcribe(_make_speech_like_pcm(duration_s=1.0))
    assert isinstance(result, str)
    svc.close()


@pytest.mark.skipif(
    not os.getenv("STT_EN_MODEL_PATH"),
    reason="STT_EN_MODEL_PATH not set — skipping real-model integration test",
)
def test_model_registry_loads_nemo_stt_for_en(monkeypatch):
    """ModelRegistry.stt_for('en') returns NeMoSTT when STT_EN_MODEL_PATH is set."""
    monkeypatch.setenv("STT_EN_MODEL_PATH", os.environ["STT_EN_MODEL_PATH"])
    monkeypatch.setenv("STT_DEVICE", os.getenv("STT_DEVICE", "cpu"))
    monkeypatch.setenv("STT_PRELOAD", "0")

    from services.model_registry import ModelRegistry
    from services.stt import NeMoSTT
    reg = ModelRegistry()
    reg.load()
    svc = reg.stt_for("en")
    assert isinstance(svc, NeMoSTT)
    reg.close()


@pytest.mark.skipif(
    not os.getenv("STT_EN_MODEL_PATH"),
    reason="STT_EN_MODEL_PATH not set — skipping real-model integration test",
)
def test_mps_fallback_does_not_crash(monkeypatch):
    """NeMoSTT on MPS (Apple Silicon) must not crash even if MPS unsupported."""
    from services.stt import NeMoSTT
    svc = NeMoSTT(model_path=os.environ["STT_EN_MODEL_PATH"], device="mps")
    assert isinstance(svc.transcribe(_make_silent_pcm()), str)
    svc.close()
