# US-P0-1 — WebSocket Transport

## Status

planned

## Lane

normal

## Product Contract

A binary WebSocket channel connects FE (:8000) and AI service (:7700).
Audio frames (binary PCM) and JSON control events flow both ways.
The AI service issues a `session_id` on connect and garbage-collects dropped sessions within 5 s.

## Relevant Product Docs

- `docs/product/voice-loop.md` — WebSocket Protocol section
- `docs/product/deployment.md` — Ports table

## Acceptance Criteria

- Given FE loads on `:8000`, when it connects to AI `:7700`, then a WS session opens and a `session_id` is issued.
- Given the channel is open, when FE sends binary PCM frames and JSON events, then AI receives both without loss for a 60-second session.
- Given the network drops, when reconnect occurs, then a new session is created and the old one is garbage-collected within 5 s.

## Design Notes

- Commands: WS `connect`, JSON events (`session_start`, `utterance_end`, `interrupt`, `session_end`)
- API: `ws://ai:7700/ws`
- Domain rules: each connection gets a unique `session_id`; sessions not cleaned up within 5 s of disconnect are an error.

## Validation

| Layer | Expected proof |
|-------|--------------|
| Unit | Session map add/remove; garbage-collect timeout logic |
| Integration | WS connect → `session_start` event received by FE stub; 60 s stability test |
| E2E | — (covered by US-P0-4+) |
| Platform | — |
