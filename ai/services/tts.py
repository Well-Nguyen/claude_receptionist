"""TTS service layer for P1.

Protocol + two concrete implementations:
  - OmniVoiceTTS  — Vietnamese (kjanh/KhanhTTS-OmniVoice via PyTorch)
  - ChatterBoxTTS — English   (chatterbox-turbo via PyTorch)

Both return 24 kHz mono Int16 PCM bytes.
"""
from __future__ import annotations

import logging
import struct
from typing import Protocol, runtime_checkable

logger = logging.getLogger(__name__)

_TTS_SAMPLE_RATE = 24000


@runtime_checkable
class TTSService(Protocol):
    def synthesize(self, text: str) -> bytes: ...
    def close(self) -> None: ...


def _float32_to_int16_bytes(samples: list[float] | "np.ndarray") -> bytes:  # type: ignore[name-defined]
    try:
        import numpy as np  # type: ignore[import]
        arr = np.asarray(samples, dtype=np.float32)
        arr = np.clip(arr, -1.0, 1.0)
        int16 = (arr * 32767).astype(np.int16)
        return int16.tobytes()
    except ImportError:
        clipped = [max(-1.0, min(1.0, s)) for s in samples]
        ints = [int(s * 32767) for s in clipped]
        return struct.pack(f"<{len(ints)}h", *ints)


class OmniVoiceTTS:
    """Vietnamese TTS using kjanh/KhanhTTS-OmniVoice."""

    def __init__(self, model_name: str = "kjanh/KhanhTTS-OmniVoice", device: str = "cuda") -> None:
        self._model_name = model_name
        self._device = device
        self._model = None
        self._load()

    def _load(self) -> None:
        try:
            # OmniVoice uses a HuggingFace-style model card; actual import path
            # depends on the published package. Adjust when the package is pinned.
            from omnivoice import OmniVoice  # type: ignore[import]

            self._model = OmniVoice.from_pretrained(self._model_name)
            self._model = self._model.to(self._device)
            self._model.eval()
            logger.info("OmniVoiceTTS loaded: %s on %s", self._model_name, self._device)
        except ImportError:
            logger.warning("omnivoice not installed; OmniVoiceTTS unavailable")
        except Exception as exc:
            logger.error("OmniVoiceTTS load failed: %s", exc)

    def synthesize(self, text: str) -> bytes:
        if self._model is None:
            logger.warning("OmniVoiceTTS not loaded; returning silence")
            return _silence(_TTS_SAMPLE_RATE, 0.5)
        try:
            audio = self._model.synthesize(text, sample_rate=_TTS_SAMPLE_RATE)
            return _float32_to_int16_bytes(audio)
        except Exception as exc:
            logger.error("OmniVoiceTTS.synthesize error: %s", exc)
            return _silence(_TTS_SAMPLE_RATE, 0.5)

    def close(self) -> None:
        self._model = None


class ChatterBoxTTS:
    """English TTS using ChatterBox Turbo."""

    def __init__(self, device: str = "cuda") -> None:
        self._device = device
        self._model = None
        self._load()

    def _load(self) -> None:
        try:
            from chatterbox.tts import ChatterboxTTS  # type: ignore[import]

            self._model = ChatterboxTTS.from_pretrained(device=self._device)
            logger.info("ChatterBoxTTS loaded on %s", self._device)
        except ImportError:
            logger.warning("chatterbox not installed; ChatterBoxTTS unavailable")
        except Exception as exc:
            logger.error("ChatterBoxTTS load failed: %s", exc)

    def synthesize(self, text: str) -> bytes:
        if self._model is None:
            logger.warning("ChatterBoxTTS not loaded; returning silence")
            return _silence(_TTS_SAMPLE_RATE, 0.5)
        try:
            wav = self._model.generate(text)
            import torchaudio  # type: ignore[import]
            import torch  # type: ignore[import]
            if wav.shape[-1] != _TTS_SAMPLE_RATE:
                wav = torchaudio.functional.resample(
                    wav, orig_freq=wav.shape[-1], new_freq=_TTS_SAMPLE_RATE
                )
            samples = wav.squeeze().cpu().numpy()
            return _float32_to_int16_bytes(samples)
        except Exception as exc:
            logger.error("ChatterBoxTTS.synthesize error: %s", exc)
            return _silence(_TTS_SAMPLE_RATE, 0.5)

    def close(self) -> None:
        self._model = None


def _silence(sample_rate: int, duration_s: float) -> bytes:
    n = int(sample_rate * duration_s)
    return struct.pack(f"<{n}h", *([0] * n))
