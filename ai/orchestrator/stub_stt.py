from __future__ import annotations


STUB_TRANSCRIPT = "Hello, I need help."


def stub_stt(pcm: bytes) -> str:
    """Return a fixed transcript regardless of audio content.

    Real STT (sherpa-onnx / NeMo) replaces this in P1.
    """
    return STUB_TRANSCRIPT
