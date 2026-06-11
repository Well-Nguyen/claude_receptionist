"""Integration tests for US-P1-5: GB10 latency targets.

Structural tests run always (stub models). Target-gate tests require
RUN_PLATFORM=gb10 — skip otherwise and document gap in the story.

Targets (SPEC §14):
  STT < 400 ms · LLM first token < 700 ms · TTS first audio < 500 ms · E2E < 1500 ms
"""
from __future__ import annotations

import os
import statistics

import pytest
from starlette.testclient import TestClient

from main import app

_ON_GB10 = os.getenv("RUN_PLATFORM") == "gb10"

_STT_TARGET_MS = 400
_LLM_TARGET_MS = 700
_TTS_TARGET_MS = 500
_E2E_TARGET_MS = 1500


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _run_turns(n: int) -> tuple[str, list[dict]]:
    """Return (session_id, latency turns) after running n utterance_end turns."""
    with TestClient(app) as client:
        with client.websocket_connect("/ws") as ws:
            session_id = ws.receive_json()["session_id"]
            ws.send_json({"event": "language_select", "session_id": session_id, "language": "en"})
            for _ in range(15):
                frame = ws.receive_json()
                if frame.get("event") == "state_change" and frame.get("state") == "LISTENING":
                    break

            for _ in range(n):
                ws.send_json({"event": "utterance_end", "session_id": session_id})
                for _ in range(30):
                    frame = ws.receive_json()
                    if frame.get("event") == "state_change" and frame.get("state") == "LISTENING":
                        break

        resp = client.get(f"/sessions/{session_id}/latency")
        assert resp.status_code == 200
        return session_id, resp.json()["turns"]


def _compute_durations(turns: list[dict]) -> dict[str, list[float]]:
    """Return per-stage duration lists from raw latency records."""
    stt, llm, tts, e2e = [], [], [], []
    for t in turns:
        ue = t.get("utterance_end_ms")
        sd = t.get("stt_done_ms")
        lf = t.get("llm_first_token_ms")
        ta = t.get("tts_first_audio_ms")
        if None not in (ue, sd, lf, ta):
            stt.append(sd - ue)
            llm.append(lf - sd)
            tts.append(ta - lf)
            e2e.append(ta - ue)
    return {"stt": stt, "llm": llm, "tts": tts, "e2e": e2e}


# ---------------------------------------------------------------------------
# Structural tests (always run, stub models OK)
# ---------------------------------------------------------------------------

def test_latency_endpoint_covers_all_turns():
    """All N turns appear in /sessions/{id}/latency with complete stage timestamps."""
    _, turns = _run_turns(3)
    assert len(turns) == 3
    for turn in turns:
        assert turn["utterance_end_ms"] is not None
        assert turn["stt_done_ms"] is not None
        assert turn["llm_first_token_ms"] is not None
        assert turn["tts_first_audio_ms"] is not None


def test_per_stage_durations_are_positive():
    """Each stage duration (stt, llm, tts) is strictly positive across all turns."""
    _, turns = _run_turns(3)
    d = _compute_durations(turns)
    for stage, vals in d.items():
        assert len(vals) == 3, f"Expected 3 records for {stage}, got {len(vals)}"
        assert all(v > 0 for v in vals), f"{stage} has non-positive duration: {vals}"


def test_latency_stages_are_ordered():
    """utterance_end ≤ stt_done ≤ llm_first_token ≤ tts_first_audio for every turn."""
    _, turns = _run_turns(3)
    for t in turns:
        assert t["utterance_end_ms"] <= t["stt_done_ms"]
        assert t["stt_done_ms"] <= t["llm_first_token_ms"]
        assert t["llm_first_token_ms"] <= t["tts_first_audio_ms"]


# ---------------------------------------------------------------------------
# GB10 target tests (require RUN_PLATFORM=gb10 + real models)
# ---------------------------------------------------------------------------

@pytest.mark.skipif(not _ON_GB10, reason="GB10 CUDA hardware required — see US-P1-5 gap/tuning plan")
def test_gb10_median_stt_under_400ms():
    _, turns = _run_turns(10)
    d = _compute_durations(turns)
    median = statistics.median(d["stt"])
    assert median < _STT_TARGET_MS, f"STT median {median:.0f} ms ≥ {_STT_TARGET_MS} ms target"


@pytest.mark.skipif(not _ON_GB10, reason="GB10 CUDA hardware required — see US-P1-5 gap/tuning plan")
def test_gb10_median_llm_first_token_under_700ms():
    _, turns = _run_turns(10)
    d = _compute_durations(turns)
    median = statistics.median(d["llm"])
    assert median < _LLM_TARGET_MS, f"LLM median {median:.0f} ms ≥ {_LLM_TARGET_MS} ms target"


@pytest.mark.skipif(not _ON_GB10, reason="GB10 CUDA hardware required — see US-P1-5 gap/tuning plan")
def test_gb10_median_tts_first_audio_under_500ms():
    _, turns = _run_turns(10)
    d = _compute_durations(turns)
    median = statistics.median(d["tts"])
    assert median < _TTS_TARGET_MS, f"TTS median {median:.0f} ms ≥ {_TTS_TARGET_MS} ms target"


@pytest.mark.skipif(not _ON_GB10, reason="GB10 CUDA hardware required — see US-P1-5 gap/tuning plan")
def test_gb10_median_e2e_under_1500ms():
    _, turns = _run_turns(10)
    d = _compute_durations(turns)
    median = statistics.median(d["e2e"])
    assert median < _E2E_TARGET_MS, f"E2E median {median:.0f} ms ≥ {_E2E_TARGET_MS} ms target"
