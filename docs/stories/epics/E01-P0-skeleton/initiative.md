# E01 — P0: Real-Time Skeleton

## Goal

Prove the full voice loop end-to-end using stubs. No real ML models.
Demonstrates: WebSocket transport, VAD endpointing, domino TTS playback,
barge-in, session reset, and per-turn latency logging.

## Exit Criteria (DoD P0)

- Full loop runs end-to-end with stubs on M4 and GB10.
- Domino, barge-in, idle/End reset, and latency logging all demonstrable.
- CI builds all three Docker images (`Dockerfile.ai`, `Dockerfile.be`, `Dockerfile.fe`).

## Affected Product Docs

- `docs/product/overview.md`
- `docs/product/voice-loop.md`
- `docs/product/ui.md`
- `docs/product/deployment.md`

## Candidate Stories

| ID | Title | Lane |
|----|-------|------|
| US-P0-1 | WebSocket transport | normal |
| US-P0-2 | Language landing | normal |
| US-P0-3 | Capture, VAD & endpointing | normal |
| US-P0-4 | Stub STT round-trip | normal |
| US-P0-5 | Domino playback with stub TTS | normal |
| US-P0-6 | Barge-in | normal |
| US-P0-7 | Session reset | normal |
| US-P0-8 | Latency harness | normal |

## Architecture Decisions In Scope

- `docs/decisions/0008-runtime-stack.md`
- `docs/decisions/0009-websocket-transport.md`
- `docs/decisions/0010-llm-openai-compatible-api.md`

## Validation Shape

| Layer | Expected proof |
|-------|--------------|
| Unit | Sentence splitter, seq ordering, session state machine transitions |
| Integration | WS session open/close, utterance round-trip with stubs |
| E2E | Full loop: speak → stub STT → stub LLM → domino TTS → playback; barge-in |
| Platform | Docker cpu profile builds and stack starts; loop runs on M4 |
| Release | — (P3) |

## Open Questions

- Stub greeting audio: generated text-to-silence or a static wav file?
- Confirm WER / false-barge-in thresholds before P1 AC (non-blocking for P0).
