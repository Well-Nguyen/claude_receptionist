# US-P0-5 — Domino Playback with Stub TTS

## Status

implemented

## Lane

normal

## Product Contract

A stub LLM reply of ≥ 3 sentences is split into segments by the sentence splitter.
Each segment is tagged with an incremental `seq` and a shared `gen_id`. Stub TTS
synthesizes each; FE plays strictly in `seq` order with no audible gap > 150 ms.
While sentence N plays, sentence N+1 is already generated (overlap in logs).

## Relevant Product Docs

- `docs/product/voice-loop.md` — Real-Time Turn Lifecycle (Domino TTS section)

## Acceptance Criteria

- Given a stub LLM reply of ≥ 3 sentences, when processed, then the sentence splitter yields ≥ 3 segments each tagged with incremental `seq` and a shared `gen_id`.
- Given segments synthesized by stub TTS, then FE plays them strictly in `seq` order with no audible gaps > 150 ms.
- Given chunks arrive out of order, then playback order remains correct by `seq`.
- Given playback, then while sentence N plays, sentence N+1 is already generated (overlap observable in logs).

## Design Notes

- Sentence splitter: split on `.`, `?`, `!` followed by whitespace; min length threshold to avoid micro-segments.
- Stub TTS: returns a small silent PCM buffer for each sentence (or a fixed beep wav).
- FE player: priority queue ordered by `seq`; holds until next expected `seq` is ready; gap ≤ 150 ms between chunks.
- gen_id: UUID per LLM generation; used for barge-in cancellation.

## Validation

| Layer | Expected proof |
|-------|--------------|
| Unit | Sentence splitter: "A. B. C." → 3 segments with seq 0,1,2; out-of-order arrival → correct playback order |
| Integration | Stub LLM 3-sentence reply → 3 audio chunks → played in order; overlap logged |
| E2E | Full loop: speak → stub STT → stub LLM 3 sentences → domino plays in order |
| Platform | — |
