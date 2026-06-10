# Product Overview — AI Voice E2E Receptionist

## What We Are Building

A low-latency, end-to-end voice conversational kiosk acting as a virtual receptionist
in a building lobby. Visitors speak to the kiosk; it responds with voice in their
chosen language. Runs entirely on a single device; packaged with Docker/Compose.

## Goals

- Sub-1.5 s first-audio latency on production hardware (GB10).
- Vietnamese and English in a single session (one language chosen at landing).
- Visitor can find info, look up a directory, and book a visit appointment by voice.
- Employee can book a meeting room by voice after identity verification.
- Building operator deploys with one `docker compose` command.

## Design Principles

| # | Principle |
|---|-----------|
| 1 | **One language per session** — only the chosen STT + TTS are exercised. |
| 2 | **AI service is a swappable unit** — absorbs GB10 (CUDA) vs M4 (MPS/CPU) differences. |
| 3 | **System prompt + DB + tool schemas in English; voice I/O in user language.** |
| 4 | **Domino TTS** — stream LLM → split sentences → synthesize each as it completes → play in order. |
| 5 | **OpenAI-compatible LLM endpoint** — future vLLM is a config swap only. |

## Personas

| Persona | Description | Primary needs |
|---------|-------------|---------------|
| **Visitor** | Walk-in guest, may not be tech-savvy. | Quick info, directory, book appointment — all by voice. |
| **Employee** | Building staff member. | Book meeting room after identity verification. |
| **Building Operator** | Runs/maintains the kiosk on-site. | Reliable kiosk, easy reset, graceful failure, Docker deploy on GB10. |
| **Developer** | Builds and maintains the system. | Clear contracts, swappable engines, observable latency, mockable BE. |
| **(Later) Admin** | Manages content and data. | *Out of scope this release.* |

## Scope

**In scope:** Voice Agent FE (`:8000`), AI service (`:7700` WS), BE (`:9000` stubs + mock),
PostgreSQL seeded with mock data, Docker/Compose with GPU profile for GB10.

**Out of scope:** Admin web, face recognition, multi-user concurrency, self-hosted vLLM
(design-ready only), avatar animation/lip-sync.

## Phase Plan

| Phase | Theme | Exit criteria |
|-------|-------|--------------|
| **P0** | Real-time skeleton (stubs) | Voice loop + domino + barge-in proven; latency harness. |
| **P1** | Real models | 4 models integrated; GB10 latency targets met; VAD/echo tuned. |
| **P2** | Business functions | 4 tools working via tool-calling on mock BE; read-back confirms. |
| **P3** | Hardening | Goodbye/idle/End, logging, fallbacks, GB10 packaging. |
| **P4** | Later | Admin web, avatar animation, vLLM, face recognition. |

## Non-Functional Requirements

- **Latency (GB10):** STT < 400 ms · LLM first token < 700 ms · TTS first audio < 500 ms/sentence · first sound < ~1.5 s.
- **Privacy:** no raw-audio persistence by default; transient PII wiped on reset/idle; only booking record persists.
- **Observability:** per-turn stage latencies, tool calls, errors → `/sessions/log`.
- **Resilience:** LLM/network failure → polite fallback; engine error → session does not crash.
- **Concurrency:** one active session per device.

## Locked Decisions

| Area | Decision |
|------|----------|
| Hardware | GB10 = production target; M4 = dev/demo. |
| Transport | WebSocket binary (PCM up, audio chunks down) + JSON events. No WebRTC. |
| STT mode | Endpoint-then-transcribe. |
| TTS | Default model voices only; no cloning. Domino sentence pipelining. |
| LLM | OpenAI API now; OpenAI-compatible base URL → vLLM later (config swap). |
| Business APIs | BE stubs + mock data; pre-built request functions; integrate later. |
| Knowledge base | Mock data; full-text search; move to real DB later. |
| Session end | 30 s idle + End button + "goodbye" intent. |
| Database | PostgreSQL in Compose, seeded with mock data. |
