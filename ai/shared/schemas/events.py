from __future__ import annotations
from typing import Literal, Optional
from pydantic import BaseModel


class SessionStartEvent(BaseModel):
    event: Literal["session_start"] = "session_start"
    session_id: str
    language: Optional[str] = None


class SessionEndEvent(BaseModel):
    event: Literal["session_end"] = "session_end"
    session_id: str
    reason: Optional[str] = None


class UtteranceEndEvent(BaseModel):
    event: Literal["utterance_end"] = "utterance_end"
    session_id: str


class TranscriptEvent(BaseModel):
    event: Literal["transcript"] = "transcript"
    role: Literal["user", "assistant"]
    text: str
    session_id: str


class AudioChunkEvent(BaseModel):
    event: Literal["audio_chunk"] = "audio_chunk"
    seq: int
    gen_id: str
    data: str  # base64 PCM 24 kHz


class InterruptEvent(BaseModel):
    event: Literal["interrupt"] = "interrupt"
    gen_id: str


class StateChangeEvent(BaseModel):
    event: Literal["state_change"] = "state_change"
    state: str


class LanguageSelectEvent(BaseModel):
    event: Literal["language_select"] = "language_select"
    session_id: str
    language: Literal["en", "vi"]


class VadConfigEvent(BaseModel):
    event: Literal["vad_config"] = "vad_config"
    silence_ms: int
    min_speech_ms: int
    threshold: float
    barge_in_min_ms: int
