# US-P0-6 — Barge-In

## Status

planned

## Lane

normal

## Product Contract

While SPEAKING, sustained VAD ≥ `BARGE_IN_MIN_MS` (default 300 ms) causes FE to
stop playback, clear queue, and send `interrupt{gen_id}`. AI cancels LLM stream and
TTS jobs for that gen_id, drops stale chunks, and returns to LISTENING.
No self-interruption from agent audio bleed.

## Relevant Product Docs

- `docs/product/voice-loop.md` — Barge-In section

## Acceptance Criteria

- Given SPEAKING, when I speak ≥ `BARGE_IN_MIN_MS` (default 300 ms), then FE stops playback and clears its queue within 200 ms.
- Given an interrupt, then FE sends `interrupt{gen_id}` and AI cancels that `gen_id`'s LLM + TTS work, dropping all stale chunks.
- Given the interrupt completed, then state returns to LISTENING and a new utterance is accepted.
- Given the agent's own audio bleeds into the mic, then no self-interruption occurs (AEC/threshold verified).

## Design Notes

- FE: while state=SPEAKING, run VAD at raised threshold; if speech ≥ barge_in_min_ms → stop audio, clear queue, send interrupt event.
- AI: on `interrupt{gen_id}`, cancel asyncio tasks for that gen_id; drain TTS queue for that gen_id; ignore incoming audio_chunk events with that gen_id.
- AEC guard: browser `echoCancellation` + raised VAD threshold while SPEAKING.

## Validation

| Layer | Expected proof |
|-------|--------------|
| Unit | AI gen_id task cancellation: stale chunks dropped after interrupt |
| Integration | FE sends interrupt during playback → AI acknowledges and stops sending chunks for that gen_id |
| E2E | Speak mid-playback → playback stops < 200 ms → new utterance accepted |
| Platform | — |
