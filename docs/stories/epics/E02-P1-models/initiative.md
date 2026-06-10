# E02 — P1: Real Models

## Goal

Replace stubs with the four real ML models. Validate latency targets on GB10.
Tune VAD and echo handling for real-world use.

## Exit Criteria (DoD P1)

- All four models integrated, selected by session language.
- GB10 meets latency targets (or has a documented gap + plan).
- Audio fidelity verified (16 kHz STT input, 24 kHz TTS output).
- VAD/echo tuned; demo works on M4 (EN snappy, VI slower as expected).

## Affected Product Docs

- `docs/product/voice-loop.md` (models section, VAD config)
- `docs/product/deployment.md` (checkpoint paths, GPU profile)

## Candidate Stories

| ID | Title | Lane |
|----|-------|------|
| US-P1-1 | Vietnamese STT (gipformer/sherpa-onnx) | normal |
| US-P1-2 | English STT (parakeet/NeMo) | normal |
| US-P1-3 | Natural TTS default voices (OmniVoice + ChatterBox) | normal |
| US-P1-4 | Audio fidelity (resampling) | normal |
| US-P1-5 | GB10 latency targets | normal |
| US-P1-6 | VAD & echo tuning | normal |

## Architecture Decisions In Scope

- `docs/decisions/0011-stt-tts-model-selection.md`

## Blocked By

- E01-P0 DoD must be met first.
- WER thresholds agreed before P1 story AC are locked.
- False-barge-in thresholds agreed before P1 story AC are locked.

## Open Questions

- NeMo install strategy for GB10 Docker image (base image size).
- GB10 preload all models at boot: **yes** (locked).
- Kiosk audio hardware (all-in-one vs. separated mic/speaker) affects echo tuning.
