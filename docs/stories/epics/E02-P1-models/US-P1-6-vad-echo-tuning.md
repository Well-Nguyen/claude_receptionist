# US-P1-6 VAD & echo tuning

## Status

implemented

## Lane

normal

## Product Contract

VAD and echo suppression parameters are tunable via env vars without code
changes. False barge-ins stay within threshold during real TTS playback.

## Relevant Product Docs

- `SPEC.md` §7 (Echo handling), §12 (.env.template VAD vars), §17.2 (US-P1-6 AC)

## Acceptance Criteria

- Given TTS speaker playback, then false barge-ins occur in ≤ 5% of turns in a
  noise test with the default VAD threshold.
  *(Threshold proposed; confirm before AC lock.)*
- Given `VAD_SILENCE_MS`, `VAD_MIN_SPEECH_MS`, `VAD_THRESHOLD`, and
  `BARGE_IN_MIN_MS` set in env, then FE and AI service use those values without
  code changes.
- Given the AI service exposes a `/config/vad` endpoint (or emits VAD config
  in `session_start`), then FE reads VAD params from the server rather than
  hardcoding them.

## Design Notes

- FE `vad/index.ts` already accepts `VadConfig`; wire `threshold`, `silenceMs`,
  `minSpeechMs` from a server-sent config rather than constants.
- P0 note in `vad/index.ts` mentions Silero WASM integration for P1 — defer
  Silero to P1.5 / P2 unless false-barge-in rate is unacceptable with energy VAD.
- Raise VAD threshold during SPEAKING state to suppress echo (already designed
  in SPEC §7).
- `BARGE_IN_MIN_MS` (default 300 ms) governs FE-side sustained speech detection
  before interrupt fires.

## Validation

| Layer | Expected proof |
| --- | --- |
| Unit | AI service returns correct VAD config from `/config/vad`; values match env vars |
| Integration | FE receives VAD config on session start; no hardcoded defaults override it |
| E2E | — |
| Platform | — |
| Release | False barge-in rate ≤ 5% on noise test recording |

## Harness Delta

None.

## Evidence

- `ai/main.py`: `_build_vad_config_event()` reads all four env vars; `VadConfigEvent`
  is sent over WS immediately after `SessionStartEvent` on every new connection.
- `ai/main.py`: `/config/vad` HTTP endpoint unchanged — still available for polling.
- `fe/voice-agent/ws/client/index.ts`: `AppEvent` union extended with `vad_config`.
- `fe/voice-agent/app/page.tsx`: `vadConfigRef` stores server config; LISTENING VAD
  uses `silence_ms`, `min_speech_ms`, `threshold`; SPEAKING (barge-in) VAD uses
  `barge_in_min_ms` + `threshold * 2` for echo suppression.
- `ai/tests/unit/test_vad_config.py`: 3 unit tests — defaults, env override, required fields.
- `ai/tests/integration/test_vad_config.py`: 3 integration tests — event ordering,
  fields present, env vars reflected in WS payload.
- Release gate (false barge-in ≤ 5%): manual noise test on real hardware; deferred
  to release validation. Silero WASM also deferred to P1.5/P2 (energy VAD sufficient).
