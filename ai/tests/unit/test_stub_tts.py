"""Unit tests for US-P0-5: stub TTS."""
from __future__ import annotations

import base64
import struct

from orchestrator.stub_tts import stub_tts, stub_tts_b64


def test_stub_tts_returns_bytes():
    result = stub_tts("hello")
    assert isinstance(result, bytes) and len(result) > 0


def test_stub_tts_is_valid_int16_pcm():
    pcm = stub_tts("hello")
    # Must be even-length (16-bit samples)
    assert len(pcm) % 2 == 0
    # Unpack without error
    n = len(pcm) // 2
    struct.unpack(f"<{n}h", pcm)


def test_stub_tts_same_output_for_different_text():
    assert stub_tts("hello") == stub_tts("goodbye")


def test_stub_tts_b64_is_valid_base64():
    b64 = stub_tts_b64("hello")
    decoded = base64.b64decode(b64)
    assert len(decoded) > 0


def test_stub_tts_b64_decodes_to_same_pcm():
    pcm = stub_tts("hello")
    b64 = stub_tts_b64("hello")
    assert base64.b64decode(b64) == pcm
