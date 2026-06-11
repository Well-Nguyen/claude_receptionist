"""Integration tests for US-P1-3: Natural TTS voices.

OmniVoiceTTS tests require:
  - omnivoice installed
  - TTS_VI_MODEL set (e.g. "kjanh/KhanhTTS-OmniVoice")

ChatterBoxTTS tests require:
  - chatterbox-tts + torch + torchaudio installed
  - TTS_EN_ENGINE set (e.g. "chatterbox-turbo")

All tests skip automatically when the relevant library is missing.
"""
from __future__ import annotations

import os
import struct

import pytest

_SAMPLE_RATE = 24000
_BYTES_PER_SAMPLE = 2


def _is_non_silent(pcm: bytes, threshold: int = 100) -> bool:
    """Return True if any Int16 sample exceeds the threshold."""
    n = len(pcm) // 2
    samples = struct.unpack(f"<{n}h", pcm[: n * 2])
    return any(abs(s) > threshold for s in samples)


# ===========================================================================
# OmniVoiceTTS
# ===========================================================================

omnivoice = pytest.importorskip("omnivoice", reason="omnivoice not installed")


@pytest.mark.skipif(
    not os.getenv("TTS_VI_MODEL"),
    reason="TTS_VI_MODEL not set — skipping real-model integration test",
)
def test_omnivoice_loads_without_crashing():
    from services.tts import OmniVoiceTTS
    device = os.getenv("TTS_DEVICE", "cpu")
    svc = OmniVoiceTTS(model_name=os.environ["TTS_VI_MODEL"], device=device)
    assert svc._model is not None
    svc.close()


@pytest.mark.skipif(
    not os.getenv("TTS_VI_MODEL"),
    reason="TTS_VI_MODEL not set — skipping real-model integration test",
)
def test_omnivoice_synthesize_returns_non_empty_bytes():
    from services.tts import OmniVoiceTTS
    device = os.getenv("TTS_DEVICE", "cpu")
    svc = OmniVoiceTTS(model_name=os.environ["TTS_VI_MODEL"], device=device)
    result = svc.synthesize("Xin chào")
    assert isinstance(result, bytes)
    assert len(result) > 0
    svc.close()


@pytest.mark.skipif(
    not os.getenv("TTS_VI_MODEL"),
    reason="TTS_VI_MODEL not set — skipping real-model integration test",
)
def test_omnivoice_output_is_non_silent():
    from services.tts import OmniVoiceTTS
    device = os.getenv("TTS_DEVICE", "cpu")
    svc = OmniVoiceTTS(model_name=os.environ["TTS_VI_MODEL"], device=device)
    result = svc.synthesize("Xin chào, tôi có thể giúp gì cho bạn?")
    assert _is_non_silent(result), "Expected non-silent audio for Vietnamese speech"
    svc.close()


@pytest.mark.skipif(
    not os.getenv("TTS_VI_MODEL"),
    reason="TTS_VI_MODEL not set — skipping real-model integration test",
)
def test_registry_loads_omnivoice_for_vi(monkeypatch):
    monkeypatch.setenv("TTS_VI_MODEL", os.environ["TTS_VI_MODEL"])
    monkeypatch.setenv("TTS_DEVICE", os.getenv("TTS_DEVICE", "cpu"))
    monkeypatch.setenv("STT_PRELOAD", "0")
    from services.model_registry import ModelRegistry
    from services.tts import OmniVoiceTTS
    reg = ModelRegistry()
    svc = reg.tts_for("vi")
    assert isinstance(svc, OmniVoiceTTS)
    reg.close()


# ===========================================================================
# ChatterBoxTTS
# ===========================================================================

chatterbox_tts = pytest.importorskip("chatterbox.tts", reason="chatterbox not installed")


@pytest.mark.skipif(
    not os.getenv("TTS_EN_ENGINE"),
    reason="TTS_EN_ENGINE not set — skipping real-model integration test",
)
def test_chatterbox_loads_without_crashing():
    from services.tts import ChatterBoxTTS
    device = os.getenv("TTS_DEVICE", "cpu")
    svc = ChatterBoxTTS(device=device)
    assert svc._model is not None
    svc.close()


@pytest.mark.skipif(
    not os.getenv("TTS_EN_ENGINE"),
    reason="TTS_EN_ENGINE not set — skipping real-model integration test",
)
def test_chatterbox_synthesize_returns_non_empty_bytes():
    from services.tts import ChatterBoxTTS
    device = os.getenv("TTS_DEVICE", "cpu")
    svc = ChatterBoxTTS(device=device)
    result = svc.synthesize("Hello, how can I help you?")
    assert isinstance(result, bytes)
    assert len(result) > 0
    svc.close()


@pytest.mark.skipif(
    not os.getenv("TTS_EN_ENGINE"),
    reason="TTS_EN_ENGINE not set — skipping real-model integration test",
)
def test_chatterbox_output_is_non_silent():
    from services.tts import ChatterBoxTTS
    device = os.getenv("TTS_DEVICE", "cpu")
    svc = ChatterBoxTTS(device=device)
    result = svc.synthesize("Welcome to the front desk.")
    assert _is_non_silent(result), "Expected non-silent audio for English speech"
    svc.close()


@pytest.mark.skipif(
    not os.getenv("TTS_EN_ENGINE"),
    reason="TTS_EN_ENGINE not set — skipping real-model integration test",
)
def test_registry_loads_chatterbox_for_en(monkeypatch):
    monkeypatch.setenv("TTS_EN_ENGINE", os.environ["TTS_EN_ENGINE"])
    monkeypatch.setenv("TTS_DEVICE", os.getenv("TTS_DEVICE", "cpu"))
    monkeypatch.setenv("STT_PRELOAD", "0")
    from services.model_registry import ModelRegistry
    from services.tts import ChatterBoxTTS
    reg = ModelRegistry()
    svc = reg.tts_for("en")
    assert isinstance(svc, ChatterBoxTTS)
    reg.close()
