# US-P0-4 — Stub STT Round-Trip

## Status

implemented

## Lane

normal

## Product Contract

On `utterance_end`, the stub STT returns a fixed transcript, fires a
`transcript{role:user}` event to FE, and forwards the text to the LLM/stub stage.
The transcript renders in the chatbox.

## Relevant Product Docs

- `docs/product/voice-loop.md` — Real-Time Turn Lifecycle

## Acceptance Criteria

- Given `utterance_end`, when the stub STT runs, then a `transcript{role:user}` event returns and renders in the chatbox.
- Given a transcript, then the same text is forwarded into the LLM/stub stage.

## Design Notes

- Stub STT: returns a hardcoded string (e.g. "Hello, I need help.") regardless of audio input.
- Commands: `transcript` WS event `{role: "user", text: "...", session_id: "..."}`.
- The stub must accept the accumulated PCM buffer and return synchronously (no async delay required).

## Validation

| Layer | Expected proof |
|-------|--------------|
| Unit | Stub STT function returns fixed string from PCM input |
| Integration | `utterance_end` → `transcript(user)` event received by FE; chatbox renders text |
| E2E | — (covered by US-P0-5) |
| Platform | — |
