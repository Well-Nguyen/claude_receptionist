# E04 — P3: Hardening

## Goal

Production-ready: goodbye/idle/End reset with PII wipe, usage logging,
graceful failure, and one-command GB10 deploy verified on LAN.

## Exit Criteria (DoD P3)

- Goodbye/idle/End all reset cleanly with PII wipe.
- Usage logging in place (per-session `/sessions/log`).
- LLM/network/engine failures degrade gracefully (polite fallback, no crash).
- Single-command GB10 deploy verified on LAN (`docker compose --profile gpu up`).

## Affected Product Docs

- `docs/product/overview.md` (NFR section)
- `docs/product/voice-loop.md` (session reset, idle timeout)
- `docs/product/deployment.md` (GB10 packaging)

## Candidate Stories

| ID | Title | Lane |
|----|-------|------|
| US-P3-1 | Goodbye intent | normal |
| US-P3-2 | Idle reset & PII wipe | high-risk |
| US-P3-3 | Usage logging | normal |
| US-P3-4 | Graceful failure | normal |
| US-P3-5 | GB10 packaging | normal |

## High-Risk Flags

US-P3-2 (PII wipe) is high-risk:
- Audit/security: transient PII must be wiped from memory on reset.
- Data model: determines what persists vs. what is cleared.

Requires high-risk story packet when implementation is selected.

## Blocked By

- E01-P0 DoD + E02-P1 DoD + E03-P2 DoD.

## Open Questions

- Logging PII policy: session log must not include raw audio or names beyond booking record.
- GB10 network setup for LAN reachability testing.
