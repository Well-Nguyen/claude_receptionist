from __future__ import annotations

import base64
import struct

_SAMPLE_RATE = 24000
_DURATION_S = 0.5  # half-second of silence per sentence


def stub_tts(text: str) -> bytes:
    """Return silent 24 kHz mono Int16 PCM. Real TTS replaces this in P1."""
    n = int(_SAMPLE_RATE * _DURATION_S)
    return struct.pack(f"<{n}h", *([0] * n))


def stub_tts_b64(text: str) -> str:
    return base64.b64encode(stub_tts(text)).decode()
