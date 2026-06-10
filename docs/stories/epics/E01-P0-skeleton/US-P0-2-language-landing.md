# US-P0-2 — Language Landing

## Status

planned

## Lane

normal

## Product Contract

The landing page presents two buttons (English / Tiếng Việt). One tap enters GREETING
within 300 ms, fixes the language for the session, and plays a greeting audio (stub OK
in P0) before entering LISTENING.

## Relevant Product Docs

- `docs/product/ui.md` — Landing Page, Visual States
- `docs/product/voice-loop.md` — Session State Machine

## Acceptance Criteria

- Given the LANDING page, when I tap `English` or `Tiếng Việt`, then the session enters GREETING within 300 ms and the mic opens.
- Given a language is selected, then it is fixed for the whole session and reflected in all transcripts/events.
- Given GREETING, then a greeting audio (stub allowed) plays in the chosen language before LISTENING.

## Design Notes

- UI surfaces: Landing page with two large buttons; red-on-white theme.
- Domain rules: language selection fires `session_start{language}` WS event; language immutable until session reset.
- Stub greeting: static wav file or synthesized silence with a text overlay is acceptable for P0.

## Validation

| Layer | Expected proof |
|-------|--------------|
| Unit | State machine LANDING → GREETING transition within 300 ms; language immutability |
| Integration | Language selection → WS `session_start` event with correct language field |
| E2E | Tap EN → greeting plays → mic waveform visible |
| Platform | — |
