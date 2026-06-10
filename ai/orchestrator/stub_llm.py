from __future__ import annotations

_REPLIES: dict[str, str] = {
    "en": (
        "I can help you with that. "
        "Please follow me to the reception area. "
        "Someone will assist you shortly."
    ),
    "vi": (
        "Tôi có thể giúp bạn với điều đó. "
        "Vui lòng theo tôi đến khu vực lễ tân. "
        "Ai đó sẽ hỗ trợ bạn ngay."
    ),
}


def stub_llm(transcript: str, language: str = "en") -> str:
    """Return a fixed 3-sentence reply. Real LLM replaces this in P1."""
    return _REPLIES.get(language, _REPLIES["en"])
