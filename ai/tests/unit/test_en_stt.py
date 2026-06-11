"""Unit tests for US-P1-2: English STT (NeMoSTT).

Mocks nemo so the tests run without the library or model files.
"""
from __future__ import annotations

import struct
import sys
import types
import wave
from unittest.mock import MagicMock, call, patch

import pytest


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_pcm(n_samples: int = 4096, value: int = 1000) -> bytes:
    return struct.pack(f"<{n_samples}h", *([value] * n_samples))


def _make_nemo_mock(transcript: str = "hello world") -> tuple[types.ModuleType, MagicMock]:
    """Return (nemo module mock, ASRModel mock instance)."""
    model_instance = MagicMock()
    model_instance.to.return_value = model_instance
    model_instance.eval.return_value = None
    model_instance.transcribe.return_value = [transcript]

    asr_models = MagicMock()
    asr_models.ASRModel.restore_from.return_value = model_instance

    nemo_asr_mod = types.ModuleType("nemo.collections.asr")
    nemo_asr_mod.models = asr_models

    nemo_collections = types.ModuleType("nemo.collections")
    nemo_collections.asr = nemo_asr_mod

    nemo_mod = types.ModuleType("nemo")
    nemo_mod.collections = nemo_collections

    return nemo_mod, model_instance


def _inject_nemo(monkeypatch, transcript: str = "hello world"):
    nemo_mod, model_instance = _make_nemo_mock(transcript)
    monkeypatch.setitem(sys.modules, "nemo", nemo_mod)
    monkeypatch.setitem(sys.modules, "nemo.collections", nemo_mod.collections)
    monkeypatch.setitem(sys.modules, "nemo.collections.asr", nemo_mod.collections.asr)
    return model_instance


# ---------------------------------------------------------------------------
# Protocol conformance
# ---------------------------------------------------------------------------

def test_nemo_stt_implements_protocol(monkeypatch):
    _inject_nemo(monkeypatch)
    from services.stt import STTService, NeMoSTT
    svc = NeMoSTT(model_path="/models/en/parakeet.nemo", device="cpu")
    assert isinstance(svc, STTService)
    svc.close()


# ---------------------------------------------------------------------------
# Loader
# ---------------------------------------------------------------------------

def test_load_calls_restore_from_with_path(monkeypatch):
    model_instance = _inject_nemo(monkeypatch)
    from services.stt import NeMoSTT
    NeMoSTT(model_path="/models/en/parakeet.nemo", device="cpu")

    import nemo.collections.asr as nemo_asr
    nemo_asr.models.ASRModel.restore_from.assert_called_once_with(
        restore_path="/models/en/parakeet.nemo"
    )


def test_load_moves_model_to_device(monkeypatch):
    model_instance = _inject_nemo(monkeypatch)
    from services.stt import NeMoSTT
    NeMoSTT(model_path="/models/en/parakeet.nemo", device="cuda")

    model_instance.to.assert_called_once_with("cuda")


def test_load_calls_eval(monkeypatch):
    model_instance = _inject_nemo(monkeypatch)
    from services.stt import NeMoSTT
    NeMoSTT(model_path="/models/en/parakeet.nemo", device="cpu")
    model_instance.eval.assert_called_once()


def test_load_graceful_when_nemo_not_installed(monkeypatch):
    monkeypatch.setitem(sys.modules, "nemo", None)
    monkeypatch.setitem(sys.modules, "nemo.collections", None)
    monkeypatch.setitem(sys.modules, "nemo.collections.asr", None)

    from services.stt import NeMoSTT
    svc = NeMoSTT(model_path="/models/en/parakeet.nemo", device="cpu")
    assert svc._model is None
    svc.close()


def test_load_cuda_failure_retries_on_cpu(monkeypatch):
    """When CUDA load fails NeMoSTT must retry with device='cpu'."""
    nemo_mod, model_instance = _make_nemo_mock()
    call_count = {"n": 0}

    original_restore = nemo_mod.collections.asr.models.ASRModel.restore_from

    def restore_side_effect(restore_path):
        call_count["n"] += 1
        if call_count["n"] == 1:
            raise RuntimeError("CUDA out of memory")
        return model_instance

    nemo_mod.collections.asr.models.ASRModel.restore_from = MagicMock(
        side_effect=restore_side_effect
    )
    monkeypatch.setitem(sys.modules, "nemo", nemo_mod)
    monkeypatch.setitem(sys.modules, "nemo.collections", nemo_mod.collections)
    monkeypatch.setitem(sys.modules, "nemo.collections.asr", nemo_mod.collections.asr)

    from services.stt import NeMoSTT
    svc = NeMoSTT(model_path="/models/en/parakeet.nemo", device="cuda")

    assert svc._device == "cpu"
    assert svc._model is model_instance
    svc.close()


def test_load_cpu_failure_does_not_retry(monkeypatch):
    """CPU failures must not trigger infinite retry."""
    nemo_mod, _ = _make_nemo_mock()
    nemo_mod.collections.asr.models.ASRModel.restore_from = MagicMock(
        side_effect=RuntimeError("bad model file")
    )
    monkeypatch.setitem(sys.modules, "nemo", nemo_mod)
    monkeypatch.setitem(sys.modules, "nemo.collections", nemo_mod.collections)
    monkeypatch.setitem(sys.modules, "nemo.collections.asr", nemo_mod.collections.asr)

    from services.stt import NeMoSTT
    svc = NeMoSTT(model_path="/models/en/parakeet.nemo", device="cpu")
    assert svc._model is None
    # restore_from called exactly once (no retry when already on cpu)
    assert nemo_mod.collections.asr.models.ASRModel.restore_from.call_count == 1
    svc.close()


# ---------------------------------------------------------------------------
# transcribe() — WAV writing and model call
# ---------------------------------------------------------------------------

def test_transcribe_writes_wav_and_calls_model(monkeypatch, tmp_path):
    model_instance = _inject_nemo(monkeypatch, transcript="welcome")
    from services.stt import NeMoSTT
    svc = NeMoSTT(model_path="/models/en/parakeet.nemo", device="cpu")
    svc._tmpdir = str(tmp_path)

    result = svc.transcribe(_make_pcm(4096), sample_rate=16000)

    wav_path = str(tmp_path / "utterance.wav")
    model_instance.transcribe.assert_called_once_with([wav_path])
    assert result == "welcome"
    svc.close()


def test_transcribe_wav_has_correct_params(monkeypatch, tmp_path):
    _inject_nemo(monkeypatch)
    from services.stt import NeMoSTT
    svc = NeMoSTT(model_path="/models/en/parakeet.nemo", device="cpu")
    svc._tmpdir = str(tmp_path)

    svc.transcribe(_make_pcm(4096), sample_rate=16000)

    wav_path = str(tmp_path / "utterance.wav")
    with wave.open(wav_path, "rb") as wf:
        assert wf.getnchannels() == 1
        assert wf.getsampwidth() == 2
        assert wf.getframerate() == 16000
        assert wf.getnframes() == 4096
    svc.close()


def test_transcribe_strips_whitespace(monkeypatch, tmp_path):
    _inject_nemo(monkeypatch, transcript="  hello world  ")
    from services.stt import NeMoSTT
    svc = NeMoSTT(model_path="/models/en/parakeet.nemo", device="cpu")
    svc._tmpdir = str(tmp_path)

    result = svc.transcribe(_make_pcm())
    assert result == "hello world"
    svc.close()


def test_transcribe_returns_empty_when_model_returns_empty_list(monkeypatch, tmp_path):
    model_instance = _inject_nemo(monkeypatch)
    model_instance.transcribe.return_value = []
    from services.stt import NeMoSTT
    svc = NeMoSTT(model_path="/models/en/parakeet.nemo", device="cpu")
    svc._tmpdir = str(tmp_path)

    result = svc.transcribe(_make_pcm())
    assert result == ""
    svc.close()


def test_transcribe_returns_empty_when_not_loaded(monkeypatch):
    from services.stt import NeMoSTT
    svc = NeMoSTT.__new__(NeMoSTT)
    svc._model = None
    svc._tmpdir = ""
    result = svc.transcribe(_make_pcm())
    assert result == ""


def test_transcribe_returns_empty_on_exception(monkeypatch, tmp_path):
    model_instance = _inject_nemo(monkeypatch)
    model_instance.transcribe.side_effect = RuntimeError("inference failure")
    from services.stt import NeMoSTT
    svc = NeMoSTT(model_path="/models/en/parakeet.nemo", device="cpu")
    svc._tmpdir = str(tmp_path)

    result = svc.transcribe(_make_pcm())
    assert result == ""
    svc.close()


# ---------------------------------------------------------------------------
# close()
# ---------------------------------------------------------------------------

def test_close_releases_model(monkeypatch):
    _inject_nemo(monkeypatch)
    from services.stt import NeMoSTT
    svc = NeMoSTT(model_path="/models/en/parakeet.nemo", device="cpu")
    assert svc._model is not None
    svc.close()
    assert svc._model is None


# ---------------------------------------------------------------------------
# ModelRegistry — EN path
# ---------------------------------------------------------------------------

def test_registry_returns_stub_when_no_env(monkeypatch):
    monkeypatch.delenv("STT_EN_MODEL_PATH", raising=False)
    from services.model_registry import ModelRegistry, _StubSTT
    reg = ModelRegistry()
    reg.load()
    assert isinstance(reg.stt_for("en"), _StubSTT)
    reg.close()


def test_registry_returns_nemo_stt_when_env_set(monkeypatch):
    _inject_nemo(monkeypatch)
    monkeypatch.setenv("STT_EN_MODEL_PATH", "/models/en/parakeet.nemo")
    monkeypatch.setenv("STT_DEVICE", "cpu")
    monkeypatch.setenv("STT_PRELOAD", "0")

    from services.model_registry import ModelRegistry
    from services.stt import NeMoSTT
    reg = ModelRegistry()
    svc = reg.stt_for("en")
    assert isinstance(svc, NeMoSTT)
    reg.close()
