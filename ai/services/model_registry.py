"""Model registry — loads and vends STT/TTS services at runtime.

GB10: preloads all four models at boot (STT_PRELOAD=1 or default).
M4:  lazy-loads on first use (STT_PRELOAD=0).

Falls back to stub implementations when a model path is unset or the library
is not installed, so the service stays runnable without checkpoints.
"""
from __future__ import annotations

import base64
import logging
import os
import struct

from services.stt import STTService, SherpaOnnxSTT, NeMoSTT
from services.tts import TTSService, OmniVoiceTTS, ChatterBoxTTS

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Stub fallbacks
# ---------------------------------------------------------------------------

class _StubSTT:
    def transcribe(self, pcm: bytes, sample_rate: int = 16000) -> str:
        logger.warning("Using stub STT — real model not loaded")
        return "Hello, I need help."

    def close(self) -> None:
        pass


class _StubTTS:
    _DURATION_S = 0.5
    _SAMPLE_RATE = 24000

    def synthesize(self, text: str) -> bytes:
        logger.warning("Using stub TTS — real model not loaded")
        n = int(self._SAMPLE_RATE * self._DURATION_S)
        return struct.pack(f"<{n}h", *([0] * n))

    def close(self) -> None:
        pass


# ---------------------------------------------------------------------------
# Registry
# ---------------------------------------------------------------------------

class ModelRegistry:
    def __init__(self) -> None:
        self._stt: dict[str, STTService] = {}
        self._tts: dict[str, TTSService] = {}

    def load(self) -> None:
        device = os.getenv("STT_DEVICE", "auto")
        tts_device = os.getenv("TTS_DEVICE", "auto")
        preload = os.getenv("STT_PRELOAD", "1") == "1"

        if preload:
            self._stt["vi"] = self._load_stt_vi(device)
            self._stt["en"] = self._load_stt_en(device)
            self._tts["vi"] = self._load_tts_vi(tts_device)
            self._tts["en"] = self._load_tts_en(tts_device)
        else:
            logger.info("ModelRegistry: lazy-load mode (STT_PRELOAD=0)")

    def stt_for(self, language: str) -> STTService:
        if language not in self._stt:
            self._stt[language] = self._load_stt_vi(os.getenv("STT_DEVICE", "auto")) \
                if language == "vi" else self._load_stt_en(os.getenv("STT_DEVICE", "auto"))
        return self._stt[language]

    def tts_for(self, language: str) -> TTSService:
        if language not in self._tts:
            self._tts[language] = self._load_tts_vi(os.getenv("TTS_DEVICE", "auto")) \
                if language == "vi" else self._load_tts_en(os.getenv("TTS_DEVICE", "auto"))
        return self._tts[language]

    def close(self) -> None:
        for svc in self._stt.values():
            svc.close()
        for svc in self._tts.values():
            svc.close()
        self._stt.clear()
        self._tts.clear()

    # --- loaders ---

    def _load_stt_vi(self, device: str) -> STTService:
        path = os.getenv("STT_VI_MODEL_PATH", "")
        quantize = os.getenv("STT_VI_QUANTIZE", "int8")
        num_threads = int(os.getenv("STT_NUM_THREADS", "4"))
        # SherpaOnnxSTT uses ONNX runtime (CPU/ONNX RT); device not used directly.
        # When path is empty it auto-downloads from HuggingFace.
        try:
            svc = SherpaOnnxSTT(model_path=path, quantize=quantize, num_threads=num_threads)
            if svc._recognizer is None:
                raise RuntimeError("recognizer not initialised")
            return svc
        except Exception as exc:
            logger.error("SherpaOnnxSTT init failed: %s; using stub", exc)
            return _StubSTT()

    def _load_stt_en(self, device: str) -> STTService:
        path = os.getenv("STT_EN_MODEL_PATH", "")
        if not path:
            logger.warning("STT_EN_MODEL_PATH not set; using stub STT for EN")
            return _StubSTT()
        resolved = _resolve_device(device)
        try:
            return NeMoSTT(model_path=path, device=resolved)
        except Exception as exc:
            logger.error("NeMoSTT init failed: %s; using stub", exc)
            return _StubSTT()

    def _load_tts_vi(self, device: str) -> TTSService:
        model_name = os.getenv("TTS_VI_MODEL", "")
        if not model_name:
            logger.warning("TTS_VI_MODEL not set; using stub TTS for VI")
            return _StubTTS()
        resolved = _resolve_device(device)
        try:
            return OmniVoiceTTS(model_name=model_name, device=resolved)
        except Exception as exc:
            logger.error("OmniVoiceTTS init failed: %s; using stub", exc)
            return _StubTTS()

    def _load_tts_en(self, device: str) -> TTSService:
        engine = os.getenv("TTS_EN_ENGINE", "")
        if not engine:
            logger.warning("TTS_EN_ENGINE not set; using stub TTS for EN")
            return _StubTTS()
        resolved = _resolve_device(device)
        try:
            return ChatterBoxTTS(device=resolved)
        except Exception as exc:
            logger.error("ChatterBoxTTS init failed: %s; using stub", exc)
            return _StubTTS()


def _resolve_device(device: str) -> str:
    if device != "auto":
        return device
    try:
        import torch  # type: ignore[import]
        if torch.cuda.is_available():
            return "cuda"
        if torch.backends.mps.is_available():
            return "mps"
    except ImportError:
        pass
    return "cpu"


# Module-level singleton used by main.py
registry = ModelRegistry()
