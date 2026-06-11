"""Unit tests for US-P1-1: Vietnamese STT (SherpaOnnxSTT).

Mocks sherpa_onnx so the tests run without the library or model files.
"""
from __future__ import annotations

import struct
import sys
import types
from unittest.mock import MagicMock, patch, call

import pytest


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_pcm(n_samples: int = 4096, value: int = 1000) -> bytes:
    return struct.pack(f"<{n_samples}h", *([value] * n_samples))


def _make_sherpa_mock() -> types.ModuleType:
    """Return a minimal mock of the sherpa_onnx module."""
    mod = types.ModuleType("sherpa_onnx")

    stream = MagicMock()
    stream.result.text = "xin chào"

    recognizer = MagicMock()
    recognizer.create_stream.return_value = stream
    recognizer.decode_streams = MagicMock()

    mod.OfflineRecognizer = MagicMock()
    mod.OfflineRecognizer.from_transducer = MagicMock(return_value=recognizer)

    return mod


# ---------------------------------------------------------------------------
# Protocol conformance
# ---------------------------------------------------------------------------

def test_sherpa_onnx_stt_implements_protocol(monkeypatch):
    sherpa_mock = _make_sherpa_mock()
    monkeypatch.setitem(sys.modules, "sherpa_onnx", sherpa_mock)
    monkeypatch.setenv("STT_VI_MODEL_PATH", "/fake/path")

    from services.stt import STTService, SherpaOnnxSTT
    svc = SherpaOnnxSTT(model_path="/fake/path")
    assert isinstance(svc, STTService)


# ---------------------------------------------------------------------------
# Loader — local path
# ---------------------------------------------------------------------------

def test_load_uses_model_path_files(monkeypatch):
    sherpa_mock = _make_sherpa_mock()
    monkeypatch.setitem(sys.modules, "sherpa_onnx", sherpa_mock)

    from services.stt import SherpaOnnxSTT
    SherpaOnnxSTT(model_path="/models/vi", quantize="int8")

    sherpa_mock.OfflineRecognizer.from_transducer.assert_called_once_with(
        encoder="/models/vi/encoder-epoch-35-avg-6.int8.onnx",
        decoder="/models/vi/decoder-epoch-35-avg-6.int8.onnx",
        joiner="/models/vi/joiner-epoch-35-avg-6.int8.onnx",
        tokens="/models/vi/tokens.txt",
        num_threads=4,
        sample_rate=16000,
        feature_dim=80,
        decoding_method="greedy_search",
    )


def test_load_fp32_variant(monkeypatch):
    sherpa_mock = _make_sherpa_mock()
    monkeypatch.setitem(sys.modules, "sherpa_onnx", sherpa_mock)

    from services.stt import SherpaOnnxSTT
    SherpaOnnxSTT(model_path="/models/vi", quantize="fp32")

    _, kwargs = sherpa_mock.OfflineRecognizer.from_transducer.call_args
    assert kwargs["encoder"] == "/models/vi/encoder-epoch-35-avg-6.onnx"
    assert kwargs["decoder"] == "/models/vi/decoder-epoch-35-avg-6.onnx"
    assert kwargs["joiner"] == "/models/vi/joiner-epoch-35-avg-6.onnx"


# ---------------------------------------------------------------------------
# Loader — HuggingFace auto-download
# ---------------------------------------------------------------------------

def test_load_downloads_from_hf_when_no_path(monkeypatch):
    sherpa_mock = _make_sherpa_mock()
    monkeypatch.setitem(sys.modules, "sherpa_onnx", sherpa_mock)

    hf_mock = types.ModuleType("huggingface_hub")
    hf_mock.hf_hub_download = MagicMock(side_effect=lambda repo_id, filename: f"/cache/{filename}")
    monkeypatch.setitem(sys.modules, "huggingface_hub", hf_mock)

    from services.stt import SherpaOnnxSTT
    SherpaOnnxSTT(model_path="", quantize="int8")

    assert hf_mock.hf_hub_download.call_count == 4  # encoder, decoder, joiner, tokens
    calls_filenames = {c.kwargs["filename"] for c in hf_mock.hf_hub_download.call_args_list}
    assert "encoder-epoch-35-avg-6.int8.onnx" in calls_filenames
    assert "decoder-epoch-35-avg-6.int8.onnx" in calls_filenames
    assert "joiner-epoch-35-avg-6.int8.onnx" in calls_filenames
    assert "tokens.txt" in calls_filenames
    for c in hf_mock.hf_hub_download.call_args_list:
        assert c.kwargs["repo_id"] == "g-group-ai-lab/gipformer-65M-rnnt"


# ---------------------------------------------------------------------------
# transcribe() — correct PCM handling
# ---------------------------------------------------------------------------

def test_transcribe_passes_float32_waveform(monkeypatch):
    np = pytest.importorskip("numpy")

    sherpa_mock = _make_sherpa_mock()
    monkeypatch.setitem(sys.modules, "sherpa_onnx", sherpa_mock)

    from services.stt import SherpaOnnxSTT
    svc = SherpaOnnxSTT(model_path="/models/vi")
    pcm = _make_pcm(4096, value=16384)
    svc.transcribe(pcm)

    stream = sherpa_mock.OfflineRecognizer.from_transducer.return_value.create_stream.return_value
    accept_call = stream.accept_waveform.call_args
    samples = accept_call[0][1] if accept_call[0] else accept_call[1]["samples"]

    # Should be float32 and normalised
    assert samples.dtype == np.float32
    assert samples.max() <= 1.0
    assert len(samples) == 4096


def test_transcribe_calls_decode_and_returns_text(monkeypatch):
    sherpa_mock = _make_sherpa_mock()
    monkeypatch.setitem(sys.modules, "sherpa_onnx", sherpa_mock)

    from services.stt import SherpaOnnxSTT
    svc = SherpaOnnxSTT(model_path="/models/vi")
    result = svc.transcribe(_make_pcm())

    recognizer = sherpa_mock.OfflineRecognizer.from_transducer.return_value
    recognizer.decode_streams.assert_called_once()
    assert result == "xin chào"


def test_transcribe_strips_whitespace(monkeypatch):
    sherpa_mock = _make_sherpa_mock()
    stream = sherpa_mock.OfflineRecognizer.from_transducer.return_value.create_stream.return_value
    stream.result.text = "  xin chào  "
    monkeypatch.setitem(sys.modules, "sherpa_onnx", sherpa_mock)

    from services.stt import SherpaOnnxSTT
    svc = SherpaOnnxSTT(model_path="/models/vi")
    assert svc.transcribe(_make_pcm()) == "xin chào"


def test_transcribe_sample_rate_forwarded(monkeypatch):
    sherpa_mock = _make_sherpa_mock()
    monkeypatch.setitem(sys.modules, "sherpa_onnx", sherpa_mock)

    from services.stt import SherpaOnnxSTT
    svc = SherpaOnnxSTT(model_path="/models/vi")
    svc.transcribe(_make_pcm(), sample_rate=8000)

    stream = sherpa_mock.OfflineRecognizer.from_transducer.return_value.create_stream.return_value
    accept_call = stream.accept_waveform.call_args
    sr_arg = accept_call[0][0] if accept_call[0] else accept_call[1].get("sample_rate", accept_call[0][0])
    assert sr_arg == 8000


# ---------------------------------------------------------------------------
# Graceful degradation
# ---------------------------------------------------------------------------

def test_transcribe_returns_empty_when_not_loaded(monkeypatch):
    # Remove sherpa_onnx so _load() silently fails
    monkeypatch.setitem(sys.modules, "sherpa_onnx", None)

    from services.stt import SherpaOnnxSTT
    svc = SherpaOnnxSTT.__new__(SherpaOnnxSTT)
    svc._recognizer = None
    result = svc.transcribe(_make_pcm())
    assert result == ""


def test_load_graceful_when_sherpa_not_installed(monkeypatch):
    """SherpaOnnxSTT must not raise if sherpa_onnx is missing."""
    monkeypatch.setitem(sys.modules, "sherpa_onnx", None)

    from services.stt import SherpaOnnxSTT
    svc = SherpaOnnxSTT(model_path="/models/vi")
    assert svc._recognizer is None
    assert svc.transcribe(_make_pcm()) == ""


def test_transcribe_returns_empty_on_exception(monkeypatch):
    sherpa_mock = _make_sherpa_mock()
    recognizer = sherpa_mock.OfflineRecognizer.from_transducer.return_value
    recognizer.decode_streams.side_effect = RuntimeError("GPU OOM")
    monkeypatch.setitem(sys.modules, "sherpa_onnx", sherpa_mock)

    from services.stt import SherpaOnnxSTT
    svc = SherpaOnnxSTT(model_path="/models/vi")
    result = svc.transcribe(_make_pcm())
    assert result == ""


# ---------------------------------------------------------------------------
# close()
# ---------------------------------------------------------------------------

def test_close_releases_recognizer(monkeypatch):
    sherpa_mock = _make_sherpa_mock()
    monkeypatch.setitem(sys.modules, "sherpa_onnx", sherpa_mock)

    from services.stt import SherpaOnnxSTT
    svc = SherpaOnnxSTT(model_path="/models/vi")
    assert svc._recognizer is not None
    svc.close()
    assert svc._recognizer is None
