"""Integration tests for US-P0-5: Domino Playback with Stub TTS.

AC: utterance_end → SPEAKING state → ≥3 audio_chunk events with incremental seq
    → transcript(assistant) → LISTENING.
AC: audio_chunk events arrive with strictly incremental seq (domino order).
AC: audio_chunk data is non-empty valid base64.
"""
from __future__ import annotations

import base64

from starlette.testclient import TestClient

from main import app
from orchestrator.stub_llm import stub_llm
from orchestrator.sentence_splitter import split_sentences


def _reach_listening(ws) -> str:
    session_id = ws.receive_json()["session_id"]
    ws.send_json({"event": "language_select", "session_id": session_id, "language": "en"})
    for _ in range(10):
        frame = ws.receive_json()
        if frame.get("event") == "state_change" and frame.get("state") == "LISTENING":
            return session_id
    raise AssertionError("Did not reach LISTENING state")


def _drain_until_listening(ws) -> list[dict]:
    """Collect all events after utterance_end until state_change(LISTENING)."""
    events = []
    for _ in range(30):
        frame = ws.receive_json()
        events.append(frame)
        if frame.get("event") == "state_change" and frame.get("state") == "LISTENING":
            break
    return events


def test_utterance_end_produces_speaking_state():
    with TestClient(app) as client:
        with client.websocket_connect("/ws") as ws:
            session_id = _reach_listening(ws)
            ws.send_json({"event": "utterance_end", "session_id": session_id})

            # Drain until LISTENING
            events = _drain_until_listening(ws)

    state_events = [e for e in events if e.get("event") == "state_change"]
    states = [e["state"] for e in state_events]
    assert "SPEAKING" in states
    assert states[-1] == "LISTENING"


def test_utterance_end_produces_three_or_more_audio_chunks():
    expected_chunks = len(split_sentences(stub_llm("", "en")))
    assert expected_chunks >= 3

    with TestClient(app) as client:
        with client.websocket_connect("/ws") as ws:
            session_id = _reach_listening(ws)
            ws.send_json({"event": "utterance_end", "session_id": session_id})
            events = _drain_until_listening(ws)

    chunks = [e for e in events if e.get("event") == "audio_chunk"]
    assert len(chunks) >= 3


def test_audio_chunks_have_incremental_seq():
    with TestClient(app) as client:
        with client.websocket_connect("/ws") as ws:
            session_id = _reach_listening(ws)
            ws.send_json({"event": "utterance_end", "session_id": session_id})
            events = _drain_until_listening(ws)

    chunks = [e for e in events if e.get("event") == "audio_chunk"]
    seqs = [c["seq"] for c in chunks]
    assert seqs == list(range(len(seqs)))


def test_audio_chunks_share_gen_id():
    with TestClient(app) as client:
        with client.websocket_connect("/ws") as ws:
            session_id = _reach_listening(ws)
            ws.send_json({"event": "utterance_end", "session_id": session_id})
            events = _drain_until_listening(ws)

    chunks = [e for e in events if e.get("event") == "audio_chunk"]
    gen_ids = {c["gen_id"] for c in chunks}
    assert len(gen_ids) == 1


def test_audio_chunk_data_is_valid_base64():
    with TestClient(app) as client:
        with client.websocket_connect("/ws") as ws:
            session_id = _reach_listening(ws)
            ws.send_json({"event": "utterance_end", "session_id": session_id})
            events = _drain_until_listening(ws)

    chunks = [e for e in events if e.get("event") == "audio_chunk"]
    for chunk in chunks:
        decoded = base64.b64decode(chunk["data"])
        assert len(decoded) > 0


def test_assistant_transcript_sent_after_chunks():
    with TestClient(app) as client:
        with client.websocket_connect("/ws") as ws:
            session_id = _reach_listening(ws)
            ws.send_json({"event": "utterance_end", "session_id": session_id})
            events = _drain_until_listening(ws)

    chunk_indices = [i for i, e in enumerate(events) if e.get("event") == "audio_chunk"]
    assistant_indices = [
        i for i, e in enumerate(events)
        if e.get("event") == "transcript" and e.get("role") == "assistant"
    ]
    assert assistant_indices, "No assistant transcript received"
    assert max(chunk_indices) < min(assistant_indices), (
        "Assistant transcript must arrive after all audio chunks"
    )


def test_full_turn_event_order():
    """THINKING → user transcript → SPEAKING → audio chunks → assistant transcript → LISTENING."""
    with TestClient(app) as client:
        with client.websocket_connect("/ws") as ws:
            session_id = _reach_listening(ws)
            ws.send_json({"event": "utterance_end", "session_id": session_id})

            # First event after utterance_end
            thinking = ws.receive_json()
            assert thinking == {"event": "state_change", "state": "THINKING"}

            user_tx = ws.receive_json()
            assert user_tx["event"] == "transcript"
            assert user_tx["role"] == "user"

            speaking = ws.receive_json()
            assert speaking == {"event": "state_change", "state": "SPEAKING"}

            # Collect chunks
            chunks = []
            for _ in range(20):
                frame = ws.receive_json()
                if frame.get("event") == "audio_chunk":
                    chunks.append(frame)
                elif frame.get("event") == "transcript" and frame.get("role") == "assistant":
                    assistant_tx = frame
                    break

            listening = ws.receive_json()
            assert listening == {"event": "state_change", "state": "LISTENING"}

    assert len(chunks) >= 3
    assert [c["seq"] for c in chunks] == list(range(len(chunks)))
