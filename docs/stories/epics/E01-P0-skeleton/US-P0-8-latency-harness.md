# US-P0-8 — Latency Harness

## Status

planned

## Lane

normal

## Product Contract

Every turn logs timestamps for: utterance_end received, STT done, LLM first token,
first TTS audio ready, first FE playback start. A per-turn latency summary is
retrievable after the session.

## Relevant Product Docs

- `docs/product/voice-loop.md` — Latency Harness section
- `docs/product/overview.md` — Non-Functional Requirements

## Acceptance Criteria

- Given any turn, then logs record timestamps for: utterance_end, STT done, LLM first token, first TTS audio, first FE playback.
- Given a completed session, then a per-turn latency summary is retrievable.

## Design Notes

- AI service: structured JSON log line per turn with stage timestamps and durations.
- FE: logs `first_playback_at` and sends it back in a `latency_report` event (or BE `/sessions/log`).
- Format: `{session_id, turn_id, utterance_end_ms, stt_done_ms, llm_first_token_ms, tts_first_audio_ms, fe_first_play_ms}`.
- Summary: query by `session_id` from log output or BE `/sessions/log`.

## Validation

| Layer | Expected proof |
|-------|--------------|
| Unit | Log record contains all 5 timestamp fields; durations computable |
| Integration | Single turn produces structured log line with all stage timestamps |
| E2E | 3-turn session → per-turn latency summary retrievable and shows all stages |
| Platform | — |
