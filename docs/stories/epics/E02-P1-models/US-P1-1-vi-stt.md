# US-P1-1 Vietnamese STT

## Status

planned

## Lane

normal

## Product Contract

A Vietnamese-language session transcribes visitor speech using gipformer-65M-rnnt
via sherpa-onnx. Transcription is accurate enough for kiosk use across north,
central, and south accents. The service never crashes on regional-accent input.

## Relevant Product Docs

- `SPEC.md` §6 (STT-VI row), §17.2 (US-P1-1 AC)

## Acceptance Criteria

- Given a VI session and a scripted Vietnamese sentence set, when the user
  speaks, then gipformer transcribes with WER ≤ 20% on the internal test set.
  *(Threshold proposed; confirm before AC lock.)*
- Given a north, central, or south accent input, then transcription completes
  without crash or exception (graceful degradation is acceptable).
- Given `STT_VI_MODEL_PATH` set in env, then sherpa-onnx loads the checkpoint
  from that path at startup (GB10) or on first use (M4 lazy-load).
- Given `STT_DEVICE=cuda`, then inference runs on GPU; given `auto`, then the
  service selects the best available device.

## Design Notes

- `ai/services/stt.py` — `SherpaOnnxSTT` class implementing `STTService`.
- Model: `g-group-ai-lab/gipformer-65M-rnnt`; format: ONNX; runtime: sherpa-onnx.
- Input: 16 kHz mono Int16 PCM bytes (from session PCM buffer via US-P1-4).
- Env vars: `STT_VI_MODEL_PATH`, `STT_DEVICE`.

## Validation

| Layer | Expected proof |
| --- | --- |
| Unit | Mock sherpa-onnx; verify transcribe() called with correct PCM and config |
| Integration | Real checkpoint + real PCM → returns non-empty string for speech |
| E2E | — |
| Platform | GB10: CUDA path; M4: CPU path |
| Release | WER measurement on internal test set |

## Harness Delta

None.

## Evidence

