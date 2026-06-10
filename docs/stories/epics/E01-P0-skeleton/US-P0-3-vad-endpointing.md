# US-P0-3 — Capture, VAD & Endpointing

## Status

implemented

## Lane

normal

## Product Contract

FE-side VAD detects speech start within 200 ms, streams 16 kHz mono PCM over WS,
and emits `utterance_end` exactly once after ≥ `VAD_SILENCE_MS` (default 800 ms) of
silence. Brief pauses below threshold do not trigger end. Background noise below
`VAD_THRESHOLD` does not trigger false utterances.

## Relevant Product Docs

- `docs/product/voice-loop.md` — VAD Configuration, Real-Time Turn Lifecycle

## Acceptance Criteria

- Given LISTENING, when I speak, then FE-side VAD marks speech start within 200 ms and streams 16 kHz mono PCM.
- Given I pause briefly mid-sentence (< `VAD_SILENCE_MS`), then the utterance is NOT ended.
- Given I stop for ≥ `VAD_SILENCE_MS` (default 800 ms), then FE emits `utterance_end` exactly once.
- Given background noise below `vad_threshold`, then no false utterance is triggered.

## Design Notes

- Commands: `getUserMedia` with `echoCancellation`, `noiseSuppression`, `autoGainControl`; AudioWorklet or ScriptProcessor for VAD.
- Domain rules: VAD uses Silero VAD (WASM) or Web Speech API level detection. `VAD_SILENCE_MS`, `VAD_MIN_SPEECH_MS`, `VAD_THRESHOLD` all configurable via env → served to FE via config endpoint or embedded in bundle.

## Validation

| Layer | Expected proof |
|-------|--------------|
| Unit | VAD silence timer: exactly one `utterance_end` per utterance; no double-fire |
| Integration | Speak 3 s → silence 900 ms → one `utterance_end` received by AI stub |
| E2E | Real mic: speech → end detected; brief pause mid-sentence → no false end |
| Platform | — |
