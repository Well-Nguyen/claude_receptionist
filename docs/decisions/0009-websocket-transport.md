# 0009 WebSocket Transport (No WebRTC)

Date: 2026-06-10

## Status

Accepted

## Context

The kiosk requires real-time bidirectional audio streaming between browser FE and AI
service, with control events (utterance_end, interrupt, state_change, transcript)
flowing alongside audio. Low latency is critical (first sound < 1.5 s on GB10).

## Decision

Use **WebSocket** as the sole transport:
- Binary frames carry 16 kHz mono PCM from FE → AI.
- JSON text frames carry all control events in both directions.
- Audio chunks (24 kHz TTS output) flow AI → FE as JSON with base64 payload
  (or binary framing with a header prefix — implementation detail).
- Browser AEC handles echo (`echoCancellation`, `noiseSuppression`, `autoGainControl`).

No WebRTC. No TURN/STUN. No SDP negotiation.

## Alternatives Considered

1. **WebRTC** — better echo cancellation hardware path, but adds TURN/STUN
   infrastructure, SDP complexity, and deployment overhead for a single-device kiosk
   on the same LAN. Rejected.
2. **HTTP chunked streaming** — no bidirectionality for control events. Rejected.
3. **gRPC streaming** — requires browser polyfill; adds schema compilation step.
   Rejected.

## Consequences

Positive:
- Simple browser WebSocket API; no extra browser permissions or TURN servers.
- Same connection carries audio and events; easy to reason about ordering.
- Works reliably on local LAN with no firewall/NAT concerns.

Tradeoffs:
- Echo cancellation relies on browser AEC + VAD threshold during SPEAKING; hardware
  AEC (reference-signal) deferred to P3+ if needed.
- No built-in jitter buffer; FE player orders strictly by `seq` number.

## Follow-Up

- Implement reference-signal AEC if hardware noise testing in P1 shows self-interruption
  above accepted threshold.
- Revisit WebRTC for multi-user or remote kiosk deployments (out of current scope).
