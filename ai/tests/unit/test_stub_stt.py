"""Unit tests for US-P0-4: Stub STT."""
from __future__ import annotations

from orchestrator.stub_stt import stub_stt, STUB_TRANSCRIPT


def test_stub_stt_returns_fixed_string():
    assert stub_stt(b"") == STUB_TRANSCRIPT


def test_stub_stt_ignores_pcm_content():
    import struct
    silent = struct.pack("<2048h", *([0] * 2048))
    noisy = struct.pack("<2048h", *([32767] * 2048))
    assert stub_stt(silent) == stub_stt(noisy)


def test_stub_stt_returns_non_empty_string():
    result = stub_stt(b"anything")
    assert isinstance(result, str) and len(result) > 0
