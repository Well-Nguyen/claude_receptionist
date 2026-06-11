"""Unit tests for US-P1-3: Natural TTS voices (OmniVoiceTTS and ChatterBoxTTS).

All heavy dependencies (omnivoice, chatterbox, torch, torchaudio) are mocked.
"""
from __future__ import annotations

import struct
import sys
import types
from unittest.mock import MagicMock

import pytest

_SAMPLE_RATE = 24000
_SILENCE_HALF_S = int(_SAMPLE_RATE * 0.5)  # 12000 samples


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------

def _float32_list(n: int = 1024, value: float = 0.5) -> list:
    return [value] * n


def _silence_bytes(n_samples: int = _SILENCE_HALF_S) -> bytes:
    return struct.pack(f"<{n_samples}h", *([0] * n_samples))


# ---------------------------------------------------------------------------
# OmniVoiceTTS helpers
# ---------------------------------------------------------------------------

def _make_omnivoice_mock(audio_samples: list | None = None):
    if audio_samples is None:
        audio_samples = _float32_list(2400)

    model_instance = MagicMock()
    model_instance.to.return_value = model_instance
    model_instance.eval.return_value = None
    model_instance.synthesize.return_value = audio_samples

    omnivoice_mod = types.ModuleType("omnivoice")
    omnivoice_mod.OmniVoice = MagicMock()
    omnivoice_mod.OmniVoice.from_pretrained.return_value = model_instance

    return omnivoice_mod, model_instance


def _inject_omnivoice(monkeypatch, audio_samples=None):
    mod, instance = _make_omnivoice_mock(audio_samples)
    monkeypatch.setitem(sys.modules, "omnivoice", mod)
    return instance


# ---------------------------------------------------------------------------
# ChatterBoxTTS helpers
# ---------------------------------------------------------------------------

def _make_wav_tensor(n_samples: int = _SAMPLE_RATE):
    """Mock torch tensor with shape [1, n_samples] and numpy() returning floats."""
    wav = MagicMock()
    wav.shape = [1, n_samples]
    squeezed = MagicMock()
    squeezed.cpu.return_value = squeezed
    squeezed.numpy.return_value = _float32_list(n_samples, 0.3)
    wav.squeeze.return_value = squeezed
    return wav


def _inject_chatterbox(monkeypatch, n_samples: int = _SAMPLE_RATE):
    wav = _make_wav_tensor(n_samples)

    model_instance = MagicMock()
    model_instance.generate.return_value = wav

    chatterbox_tts_mod = types.ModuleType("chatterbox.tts")
    chatterbox_tts_mod.ChatterboxTTS = MagicMock()
    chatterbox_tts_mod.ChatterboxTTS.from_pretrained.return_value = model_instance

    chatterbox_mod = types.ModuleType("chatterbox")
    chatterbox_mod.tts = chatterbox_tts_mod

    torch_mod = types.ModuleType("torch")
    torchaudio_mod = types.ModuleType("torchaudio")
    torchaudio_functional = types.ModuleType("torchaudio.functional")
    resampled_wav = _make_wav_tensor(_SAMPLE_RATE)
    torchaudio_functional.resample = MagicMock(return_value=resampled_wav)
    torchaudio_mod.functional = torchaudio_functional

    monkeypatch.setitem(sys.modules, "chatterbox", chatterbox_mod)
    monkeypatch.setitem(sys.modules, "chatterbox.tts", chatterbox_tts_mod)
    monkeypatch.setitem(sys.modules, "torch", torch_mod)
    monkeypatch.setitem(sys.modules, "torchaudio", torchaudio_mod)
    monkeypatch.setitem(sys.modules, "torchaudio.functional", torchaudio_functional)

    return model_instance, torchaudio_functional


# ===========================================================================
# OmniVoiceTTS
# ===========================================================================

class TestOmniVoiceTTSProtocol:
    def test_implements_tts_service(self, monkeypatch):
        _inject_omnivoice(monkeypatch)
        from services.tts import TTSService, OmniVoiceTTS
        svc = OmniVoiceTTS(model_name="kjanh/KhanhTTS-OmniVoice", device="cpu")
        assert isinstance(svc, TTSService)
        svc.close()


class TestOmniVoiceTTSLoader:
    def test_from_pretrained_called_with_model_name(self, monkeypatch):
        _inject_omnivoice(monkeypatch)
        from services.tts import OmniVoiceTTS
        OmniVoiceTTS(model_name="kjanh/KhanhTTS-OmniVoice", device="cpu")

        import omnivoice
        omnivoice.OmniVoice.from_pretrained.assert_called_once_with("kjanh/KhanhTTS-OmniVoice")

    def test_model_moved_to_device(self, monkeypatch):
        instance = _inject_omnivoice(monkeypatch)
        from services.tts import OmniVoiceTTS
        OmniVoiceTTS(model_name="kjanh/KhanhTTS-OmniVoice", device="cuda")
        instance.to.assert_called_once_with("cuda")

    def test_eval_called(self, monkeypatch):
        instance = _inject_omnivoice(monkeypatch)
        from services.tts import OmniVoiceTTS
        OmniVoiceTTS(model_name="kjanh/KhanhTTS-OmniVoice", device="cpu")
        instance.eval.assert_called_once()

    def test_graceful_when_omnivoice_not_installed(self, monkeypatch):
        monkeypatch.setitem(sys.modules, "omnivoice", None)
        from services.tts import OmniVoiceTTS
        svc = OmniVoiceTTS(model_name="kjanh/KhanhTTS-OmniVoice", device="cpu")
        assert svc._model is None
        svc.close()


class TestOmniVoiceTTSSynthesize:
    def test_synthesize_calls_model_with_text_and_sample_rate(self, monkeypatch):
        instance = _inject_omnivoice(monkeypatch)
        from services.tts import OmniVoiceTTS
        svc = OmniVoiceTTS(model_name="kjanh/KhanhTTS-OmniVoice", device="cpu")
        svc.synthesize("Xin chào")
        instance.synthesize.assert_called_once_with("Xin chào", sample_rate=_SAMPLE_RATE)
        svc.close()

    def test_synthesize_returns_non_empty_bytes(self, monkeypatch):
        _inject_omnivoice(monkeypatch, audio_samples=_float32_list(2400, 0.5))
        from services.tts import OmniVoiceTTS
        svc = OmniVoiceTTS(model_name="kjanh/KhanhTTS-OmniVoice", device="cpu")
        result = svc.synthesize("Xin chào")
        assert isinstance(result, bytes)
        assert len(result) > 0
        svc.close()

    def test_synthesize_output_is_24khz_int16(self, monkeypatch):
        n = 2400
        _inject_omnivoice(monkeypatch, audio_samples=_float32_list(n))
        from services.tts import OmniVoiceTTS
        svc = OmniVoiceTTS(model_name="kjanh/KhanhTTS-OmniVoice", device="cpu")
        result = svc.synthesize("test")
        # n samples × 2 bytes/sample
        assert len(result) == n * 2
        svc.close()

    def test_synthesize_returns_silence_when_not_loaded(self, monkeypatch):
        monkeypatch.setitem(sys.modules, "omnivoice", None)
        from services.tts import OmniVoiceTTS
        svc = OmniVoiceTTS(model_name="kjanh/KhanhTTS-OmniVoice", device="cpu")
        result = svc.synthesize("hello")
        assert isinstance(result, bytes)
        assert len(result) == _SILENCE_HALF_S * 2

    def test_synthesize_returns_silence_on_exception(self, monkeypatch):
        instance = _inject_omnivoice(monkeypatch)
        instance.synthesize.side_effect = RuntimeError("GPU error")
        from services.tts import OmniVoiceTTS
        svc = OmniVoiceTTS(model_name="kjanh/KhanhTTS-OmniVoice", device="cpu")
        result = svc.synthesize("hello")
        assert len(result) == _SILENCE_HALF_S * 2
        svc.close()

    def test_close_releases_model(self, monkeypatch):
        _inject_omnivoice(monkeypatch)
        from services.tts import OmniVoiceTTS
        svc = OmniVoiceTTS(model_name="kjanh/KhanhTTS-OmniVoice", device="cpu")
        assert svc._model is not None
        svc.close()
        assert svc._model is None


# ===========================================================================
# ChatterBoxTTS
# ===========================================================================

class TestChatterBoxTTSProtocol:
    def test_implements_tts_service(self, monkeypatch):
        _inject_chatterbox(monkeypatch)
        from services.tts import TTSService, ChatterBoxTTS
        svc = ChatterBoxTTS(device="cpu")
        assert isinstance(svc, TTSService)
        svc.close()


class TestChatterBoxTTSLoader:
    def test_from_pretrained_called_with_device(self, monkeypatch):
        _inject_chatterbox(monkeypatch)
        from services.tts import ChatterBoxTTS
        ChatterBoxTTS(device="cuda")

        import chatterbox.tts
        chatterbox.tts.ChatterboxTTS.from_pretrained.assert_called_once_with(device="cuda")

    def test_graceful_when_chatterbox_not_installed(self, monkeypatch):
        monkeypatch.setitem(sys.modules, "chatterbox", None)
        monkeypatch.setitem(sys.modules, "chatterbox.tts", None)
        from services.tts import ChatterBoxTTS
        svc = ChatterBoxTTS(device="cpu")
        assert svc._model is None
        svc.close()


class TestChatterBoxTTSSynthesize:
    def test_synthesize_calls_generate_with_text(self, monkeypatch):
        model_instance, _ = _inject_chatterbox(monkeypatch)
        from services.tts import ChatterBoxTTS
        svc = ChatterBoxTTS(device="cpu")
        svc.synthesize("Hello there")
        model_instance.generate.assert_called_once_with("Hello there")
        svc.close()

    def test_synthesize_returns_non_empty_bytes(self, monkeypatch):
        _inject_chatterbox(monkeypatch, n_samples=_SAMPLE_RATE)
        from services.tts import ChatterBoxTTS
        svc = ChatterBoxTTS(device="cpu")
        result = svc.synthesize("Hello")
        assert isinstance(result, bytes)
        assert len(result) > 0
        svc.close()

    def test_synthesize_output_length_matches_samples(self, monkeypatch):
        n = _SAMPLE_RATE  # 1 second
        _inject_chatterbox(monkeypatch, n_samples=n)
        from services.tts import ChatterBoxTTS
        svc = ChatterBoxTTS(device="cpu")
        result = svc.synthesize("test")
        assert len(result) == n * 2
        svc.close()

    def test_no_resample_when_output_matches_24khz(self, monkeypatch):
        _, torchaudio_functional = _inject_chatterbox(monkeypatch, n_samples=_SAMPLE_RATE)
        from services.tts import ChatterBoxTTS
        svc = ChatterBoxTTS(device="cpu")
        svc.synthesize("test")
        torchaudio_functional.resample.assert_not_called()
        svc.close()

    def test_resample_triggered_when_output_differs_from_24khz(self, monkeypatch):
        _, torchaudio_functional = _inject_chatterbox(monkeypatch, n_samples=22050)
        from services.tts import ChatterBoxTTS
        svc = ChatterBoxTTS(device="cpu")
        svc.synthesize("test")
        torchaudio_functional.resample.assert_called_once()
        _, kwargs = torchaudio_functional.resample.call_args
        assert kwargs.get("new_freq") == _SAMPLE_RATE or \
            torchaudio_functional.resample.call_args[0][2] == _SAMPLE_RATE
        svc.close()

    def test_synthesize_returns_silence_when_not_loaded(self, monkeypatch):
        monkeypatch.setitem(sys.modules, "chatterbox", None)
        monkeypatch.setitem(sys.modules, "chatterbox.tts", None)
        from services.tts import ChatterBoxTTS
        svc = ChatterBoxTTS(device="cpu")
        result = svc.synthesize("hello")
        assert isinstance(result, bytes)
        assert len(result) == _SILENCE_HALF_S * 2

    def test_synthesize_returns_silence_on_exception(self, monkeypatch):
        model_instance, _ = _inject_chatterbox(monkeypatch)
        model_instance.generate.side_effect = RuntimeError("VRAM OOM")
        from services.tts import ChatterBoxTTS
        svc = ChatterBoxTTS(device="cpu")
        result = svc.synthesize("hello")
        assert len(result) == _SILENCE_HALF_S * 2
        svc.close()

    def test_close_releases_model(self, monkeypatch):
        _inject_chatterbox(monkeypatch)
        from services.tts import ChatterBoxTTS
        svc = ChatterBoxTTS(device="cpu")
        assert svc._model is not None
        svc.close()
        assert svc._model is None


# ===========================================================================
# ModelRegistry — TTS paths
# ===========================================================================

class TestModelRegistryTTS:
    def test_registry_returns_stub_vi_when_no_env(self, monkeypatch):
        monkeypatch.delenv("TTS_VI_MODEL", raising=False)
        from services.model_registry import ModelRegistry, _StubTTS
        reg = ModelRegistry()
        reg.load()
        assert isinstance(reg.tts_for("vi"), _StubTTS)
        reg.close()

    def test_registry_returns_stub_en_when_no_env(self, monkeypatch):
        monkeypatch.delenv("TTS_EN_ENGINE", raising=False)
        from services.model_registry import ModelRegistry, _StubTTS
        reg = ModelRegistry()
        reg.load()
        assert isinstance(reg.tts_for("en"), _StubTTS)
        reg.close()

    def test_registry_returns_omnivoice_when_vi_model_set(self, monkeypatch):
        _inject_omnivoice(monkeypatch)
        monkeypatch.setenv("TTS_VI_MODEL", "kjanh/KhanhTTS-OmniVoice")
        monkeypatch.setenv("TTS_DEVICE", "cpu")
        monkeypatch.setenv("STT_PRELOAD", "0")
        from services.model_registry import ModelRegistry
        from services.tts import OmniVoiceTTS
        reg = ModelRegistry()
        svc = reg.tts_for("vi")
        assert isinstance(svc, OmniVoiceTTS)
        reg.close()

    def test_registry_returns_chatterbox_when_en_engine_set(self, monkeypatch):
        _inject_chatterbox(monkeypatch)
        monkeypatch.setenv("TTS_EN_ENGINE", "chatterbox-turbo")
        monkeypatch.setenv("TTS_DEVICE", "cpu")
        monkeypatch.setenv("STT_PRELOAD", "0")
        from services.model_registry import ModelRegistry
        from services.tts import ChatterBoxTTS
        reg = ModelRegistry()
        svc = reg.tts_for("en")
        assert isinstance(svc, ChatterBoxTTS)
        reg.close()
