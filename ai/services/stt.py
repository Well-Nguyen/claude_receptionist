"""STT service layer for P1.

Protocol + two concrete implementations:
  - SherpaOnnxSTT  — Vietnamese (gipformer-65M-rnnt via sherpa-onnx)
  - NeMoSTT        — English   (parakeet-tdt-0.6b-v3 via NeMo)

Both accept 16 kHz mono Int16 PCM bytes and return a transcript string.
"""
from __future__ import annotations

import logging
import struct
from typing import Protocol, runtime_checkable

logger = logging.getLogger(__name__)

_STT_SAMPLE_RATE = 16000
_GIPFORMER_REPO_ID = "g-group-ai-lab/gipformer-65M-rnnt"
_GIPFORMER_FEATURE_DIM = 80


@runtime_checkable
class STTService(Protocol):
    def transcribe(self, pcm: bytes, sample_rate: int = _STT_SAMPLE_RATE) -> str: ...
    def close(self) -> None: ...


def _int16_bytes_to_float32(pcm: bytes) -> "np.ndarray":  # type: ignore[name-defined]
    """Convert raw Int16 LE PCM bytes to a float32 numpy array normalised to [-1, 1]."""
    try:
        import numpy as np
        n = len(pcm) // 2
        arr = np.frombuffer(pcm[:n * 2], dtype=np.int16).astype(np.float32)
        arr /= 32768.0
        return arr
    except ImportError:
        n = len(pcm) // 2
        raw = struct.unpack(f"<{n}h", pcm[:n * 2])
        import array as _array
        out = _array.array("f", (s / 32768.0 for s in raw))
        return out


class SherpaOnnxSTT:
    """Vietnamese STT using gipformer-65M-rnnt via sherpa-onnx OfflineRecognizer.

    Loads ONNX files from a local path (STT_VI_MODEL_PATH) or auto-downloads
    them from HuggingFace on first use when the path is not set.

    File layout expected at model_path (or downloaded):
        encoder-epoch-35-avg-6.int8.onnx  (or fp32 variant)
        decoder-epoch-35-avg-6.int8.onnx
        joiner-epoch-35-avg-6.int8.onnx
        tokens.txt

    Audio input: 16 kHz mono Int16 PCM bytes.
    """

    # File names published on HuggingFace (int8 quantised by default)
    _ONNX_FILES = {
        "fp32": {
            "encoder": "encoder-epoch-35-avg-6.onnx",
            "decoder": "decoder-epoch-35-avg-6.onnx",
            "joiner": "joiner-epoch-35-avg-6.onnx",
        },
        "int8": {
            "encoder": "encoder-epoch-35-avg-6.int8.onnx",
            "decoder": "decoder-epoch-35-avg-6.int8.onnx",
            "joiner": "joiner-epoch-35-avg-6.int8.onnx",
        },
    }

    def __init__(
        self,
        model_path: str = "",
        quantize: str = "int8",
        num_threads: int = 4,
    ) -> None:
        self._model_path = model_path
        self._quantize = quantize
        self._num_threads = num_threads
        self._recognizer = None
        self._load()

    def _resolve_model_files(self) -> dict[str, str]:
        """Return local file paths, downloading from HF if model_path is empty."""
        files = self._ONNX_FILES[self._quantize]
        if self._model_path:
            return {
                "encoder": f"{self._model_path}/{files['encoder']}",
                "decoder": f"{self._model_path}/{files['decoder']}",
                "joiner": f"{self._model_path}/{files['joiner']}",
                "tokens": f"{self._model_path}/tokens.txt",
            }
        # Auto-download from HuggingFace
        from huggingface_hub import hf_hub_download  # type: ignore[import]
        logger.info("Downloading gipformer model from HuggingFace (%s)", _GIPFORMER_REPO_ID)
        return {
            key: hf_hub_download(repo_id=_GIPFORMER_REPO_ID, filename=fname)
            for key, fname in {**files, "tokens": "tokens.txt"}.items()
        }

    def _load(self) -> None:
        try:
            import sherpa_onnx  # type: ignore[import]

            paths = self._resolve_model_files()
            self._recognizer = sherpa_onnx.OfflineRecognizer.from_transducer(
                encoder=paths["encoder"],
                decoder=paths["decoder"],
                joiner=paths["joiner"],
                tokens=paths["tokens"],
                num_threads=self._num_threads,
                sample_rate=_STT_SAMPLE_RATE,
                feature_dim=_GIPFORMER_FEATURE_DIM,
                decoding_method="greedy_search",
            )
            logger.info("SherpaOnnxSTT ready (quantize=%s)", self._quantize)
        except ImportError:
            logger.warning("sherpa_onnx not installed; SherpaOnnxSTT unavailable")
        except Exception as exc:
            logger.error("SherpaOnnxSTT load failed: %s", exc)

    def transcribe(self, pcm: bytes, sample_rate: int = _STT_SAMPLE_RATE) -> str:
        if self._recognizer is None:
            logger.warning("SherpaOnnxSTT not loaded; returning empty transcript")
            return ""
        try:
            samples = _int16_bytes_to_float32(pcm)
            stream = self._recognizer.create_stream()
            stream.accept_waveform(sample_rate, samples)
            self._recognizer.decode_streams([stream])
            return stream.result.text.strip()
        except Exception as exc:
            logger.error("SherpaOnnxSTT.transcribe error: %s", exc)
            return ""

    def close(self) -> None:
        self._recognizer = None


class NeMoSTT:
    """English STT using parakeet-tdt-0.6b-v3 via NeMo."""

    def __init__(self, model_path: str, device: str = "cuda") -> None:
        self._model_path = model_path
        self._device = device
        self._model = None
        self._tmpdir = ""
        self._load()

    def _load(self) -> None:
        try:
            import tempfile
            import nemo.collections.asr as nemo_asr  # type: ignore[import]

            self._model = nemo_asr.models.ASRModel.restore_from(
                restore_path=self._model_path
            )
            self._model = self._model.to(self._device)
            self._model.eval()
            self._tmpdir = tempfile.mkdtemp(prefix="nemo_stt_")
            logger.info("NeMoSTT loaded from %s on %s", self._model_path, self._device)
        except ImportError:
            logger.warning("nemo not installed; NeMoSTT unavailable")
        except Exception as exc:
            logger.error("NeMoSTT load failed (device=%s): %s", self._device, exc)
            if self._device not in ("cpu", "mps"):
                logger.info("NeMoSTT retrying on cpu")
                self._device = "cpu"
                self._load()

    def transcribe(self, pcm: bytes, sample_rate: int = _STT_SAMPLE_RATE) -> str:
        if self._model is None:
            logger.warning("NeMoSTT not loaded; returning empty transcript")
            return ""
        try:
            import os
            import wave
            wav_path = os.path.join(self._tmpdir, "utterance.wav")
            with wave.open(wav_path, "wb") as wf:
                wf.setnchannels(1)
                wf.setsampwidth(2)
                wf.setframerate(sample_rate)
                wf.writeframes(pcm)
            results = self._model.transcribe([wav_path])
            return results[0].strip() if results else ""
        except Exception as exc:
            logger.error("NeMoSTT.transcribe error: %s", exc)
            return ""

    def close(self) -> None:
        self._model = None
