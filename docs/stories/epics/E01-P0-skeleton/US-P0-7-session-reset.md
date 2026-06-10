# US-P0-7 — Session Reset

## Status

planned

## Lane

normal

## Product Contract

Sessions reset to LANDING on: 30 s idle (`SESSION_IDLE_TIMEOUT_S`), End button tap,
or "goodbye" intent (P3). On reset, conversation history and all transient state
are cleared.

## Relevant Product Docs

- `docs/product/voice-loop.md` — Session State Machine
- `docs/product/ui.md` — Session Control

## Acceptance Criteria

- Given no interaction for `SESSION_IDLE_TIMEOUT_S` (30 s), then the session resets to LANDING.
- Given an End button tap, then the session resets immediately to LANDING.
- Given reset, then conversation history and transient state are cleared.

## Design Notes

- Idle timer: reset on any WS event from FE; fire session_end after 30 s.
- End button: FE sends `session_end{reason: "user_end"}` immediately; AI clears session.
- State clear: conversation[], slot_state, gen_id all wiped from the session object.
- Goodbye intent handled in P3 (US-P3-1); P0 only needs idle + End button.

## Validation

| Layer | Expected proof |
|-------|--------------|
| Unit | Idle timer: fires after 30 s of no events; timer resets on any event |
| Integration | End button → `session_end` event → FE returns to LANDING; session object cleared |
| E2E | Start session → wait 30 s idle → auto-reset to LANDING visible |
| Platform | — |
