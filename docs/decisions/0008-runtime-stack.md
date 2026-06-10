# 0008 Runtime Stack Selection

Date: 2026-06-10

## Status

Accepted

## Context

SPEC.md v2.0 defines three services: an AI orchestration service, a business-logic
BE, and a browser-based FE kiosk. The stack must run on NVIDIA GB10 (ARM + CUDA,
production) and Apple M4 (dev/demo), packaged with Docker/Compose. The AI service
handles real-time WebSocket audio and ML model inference.

## Decision

| Service | Stack |
|---------|-------|
| AI service | Python (asyncio), FastAPI/Starlette WebSocket, sherpa-onnx, NeMo, ChatterBox, PyTorch |
| Backend (BE) | Python, FastAPI, SQLAlchemy, PostgreSQL |
| Frontend (FE) | Next.js (TypeScript), React, browser Web Audio API |
| Database | PostgreSQL (Docker service) seeded with mock data |
| Container | Docker / Compose, `linux/arm64` images |

## Alternatives Considered

1. **Node.js AI service** — ruled out; Python ecosystem required for NeMo/PyTorch/sherpa-onnx.
2. **Go BE** — Python FastAPI chosen to share the ML ecosystem and reduce context switching.
3. **Vue/Svelte FE** — Next.js chosen for SSR landing page + React component ecosystem.

## Consequences

Positive:
- Python AI + BE share Pydantic schemas and `be_client` module cleanly.
- Next.js gives server-rendered landing page; React handles dynamic interaction panel.
- Docker `linux/arm64` images run on both GB10 and M4 natively.

Tradeoffs:
- Python async GIL limits CPU parallelism in the AI service; offset by asyncio and worker pools.
- M4 TTS/STT will be slower than GB10 CUDA; acceptable for demo.

## Follow-Up

- Confirm `linux/arm64` base images for each Dockerfile when scaffolding.
- Decide NeMo container strategy for GB10 (NeMo docker vs. native install).
