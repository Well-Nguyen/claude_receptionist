# US-P1-2 English STT

## Status

planned

## Lane

normal

## Product Contract

An English-language session transcribes visitor speech using parakeet-tdt-0.6b-v3
via NeMo. The service runs on GB10 CUDA and falls back gracefully (slower) on M4.

## Relevant Product Docs

- `SPEC.md` §6 (STT-EN row), §17.2 (US-P1-2 AC)

## Acceptance Criteria

- Given an EN session and a scripted English sentence set, when the user speaks,
  then parakeet transcribes with WER ≤ 10% on the internal test set.
  *(Threshold proposed; confirm before AC lock.)*
- Given GB10, then NeMo runs on CUDA (`STT_DEVICE=cuda` or `auto`).
- Given M4, then NeMo falls back to CPU/MPS without crashing and returns a
  non-empty transcript.
- Given `STT_EN_MODEL_PATH` set in env, then NeMo loads the checkpoint from
  that path.

## Design Notes

- `ai/services/stt.py` — `NeMoSTT` class implementing `STTService`.
- Model: `nvidia/parakeet-tdt-0.6b-v3`; runtime: NeMo.
- Input: 16 kHz mono Int16 PCM bytes.
- Env vars: `STT_EN_MODEL_PATH`, `STT_DEVICE`.
- NeMo Docker image size: keep base image lean; evaluate `nemo_toolkit[asr]`
  slim install vs. full toolkit.

## Validation

| Layer | Expected proof |
| --- | --- |
| Unit | Mock NeMo; verify transcribe() called with correct PCM and device config |
| Integration | Real checkpoint + real PCM → returns non-empty string for speech |
| E2E | — |
| Platform | GB10: CUDA; M4: CPU fallback |
| Release | WER measurement on internal test set |

## Harness Delta

None.

## Evidence

