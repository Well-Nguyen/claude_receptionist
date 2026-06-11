"""Unit tests for US-P0-8: Latency Harness.

AC: Log record contains all 5 timestamp fields; durations computable.
"""
from __future__ import annotations

from orchestrator.state import LatencyRecord


def test_latency_record_has_all_fields():
    rec = LatencyRecord(session_id="s1", turn_id="t1")
    assert hasattr(rec, "utterance_end_ms")
    assert hasattr(rec, "stt_done_ms")
    assert hasattr(rec, "llm_first_token_ms")
    assert hasattr(rec, "tts_first_audio_ms")
    assert hasattr(rec, "fe_first_play_ms")


def test_latency_record_defaults_none():
    rec = LatencyRecord(session_id="s1", turn_id="t1")
    assert rec.utterance_end_ms is None
    assert rec.stt_done_ms is None
    assert rec.llm_first_token_ms is None
    assert rec.tts_first_audio_ms is None
    assert rec.fe_first_play_ms is None


def test_latency_record_durations_computable():
    rec = LatencyRecord(
        session_id="s1",
        turn_id="t1",
        utterance_end_ms=1000.0,
        stt_done_ms=1050.0,
        llm_first_token_ms=1200.0,
        tts_first_audio_ms=1350.0,
        fe_first_play_ms=1400.0,
    )
    assert rec.stt_done_ms - rec.utterance_end_ms == 50.0
    assert rec.llm_first_token_ms - rec.stt_done_ms == 150.0
    assert rec.tts_first_audio_ms - rec.llm_first_token_ms == 150.0
    assert rec.fe_first_play_ms - rec.utterance_end_ms == 400.0


def test_session_latency_log_starts_empty():
    from orchestrator.state import Session
    s = Session(session_id="s1")
    assert s.latency_log == []


def test_session_latency_log_stores_records():
    from orchestrator.state import Session
    s = Session(session_id="s1")
    rec = LatencyRecord(session_id="s1", turn_id="t1", utterance_end_ms=1000.0)
    s.latency_log.append(rec)
    assert len(s.latency_log) == 1
    assert s.latency_log[0].turn_id == "t1"
