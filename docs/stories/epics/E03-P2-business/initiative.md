# E03 — P2: Business Functions

## Goal

Implement all four business functions via LLM tool-calling on mock BE.
Voice slot-filling, read-back confirmation before any commit, and interaction
panel sync.

## Exit Criteria (DoD P2)

- All four functions complete end-to-end on mock BE with read-back confirmation.
- Slot-filling + normalization robust to voice variability.
- Right panel mirrors flow.
- No commit (booking/appointment) without explicit user confirmation.

## Affected Product Docs

- `docs/product/business-functions.md`
- `docs/product/ui.md` (right panel sync)

## Candidate Stories

| ID | Title | Lane |
|----|-------|------|
| US-P2-1 | Information consulting (search_knowledge_base) | normal |
| US-P2-2 | Directory lookup | normal |
| US-P2-3 | Employee verification for room booking | high-risk |
| US-P2-4 | Collect & validate meeting slots | normal |
| US-P2-5 | Check availability & confirm | normal |
| US-P2-6 | Create meeting booking | normal |
| US-P2-7 | Visitor appointment | normal |
| US-P2-8 | Interaction panel reflects voice flow | normal |
| US-P2-9 | Mock BE & seed data | normal |

## Architecture Decisions In Scope

- `docs/decisions/0010-llm-openai-compatible-api.md` (tool schemas)
- `docs/decisions/0008-runtime-stack.md` (BE FastAPI + PostgreSQL)

## Blocked By

- E01-P0 DoD (voice loop working).

## High-Risk Flags

US-P2-3 (employee verification) is high-risk:
- Authorization: gates access to room booking.
- Public contracts: `verify_employee` API shape.
- Data model: employee records in mock DB.

Requires high-risk story packet when implementation is selected.

## Open Questions

- Seed data volume: how many employees, rooms, KB entries?
- Date/time normalization edge cases for Vietnamese spoken dates.
