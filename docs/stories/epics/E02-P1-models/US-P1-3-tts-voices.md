# US-P1-3 Natural TTS default voices

## Status

planned

## Lane

normal

## Product Contract

TTS synthesis uses real model voices: OmniVoice (default) for Vietnamese and
ChatterBox/Turbo (default) for English. Both produce intelligible 24 kHz audio.
Domino pipelining holds — no reordering or gaps > 150 ms between sentences.

## Relevant Product Docs

- `SPEC.md` §6 (TTS-VI and TTS-EN rows), §17.2 (US-P1-3 AC)

## Acceptance Criteria

- Given a VI reply, then OmniVoice (default voice) synthesizes intelligible
  24 kHz mono Int16 PCM audio.
- Given an EN reply, then ChatterBox/Turbo (default voice) synthesizes
  intelligible 24 kHz mono Int16 PCM audio.
- Given multi-sentence replies, then the domino pipeline plays segments strictly
  in seq order with no audible gap > 150 ms between sentences.
- Given `TTS_VI_MODEL` and `TTS_EN_ENGINE` in env, then the correct model is
  loaded without code changes.
- Given `TTS_DEVICE=cuda`, then inference runs on GPU; given `auto`, then the
  service selects the best available device.

## Design Notes

- `ai/services/tts.py` — `OmniVoiceTTS` and `ChatterBoxTTS` implementing `TTSService`.
- TTS-VI model: `kjanh/KhanhTTS-OmniVoice`; runtime: PyTorch diffusion.
- TTS-EN engine: `chatterbox-turbo`; runtime: PyTorch.
- Output: 24 kHz mono Int16 PCM bytes (base64-encoded for WS transport).
- Env vars: `TTS_VI_MODEL`, `TTS_EN_ENGINE`, `TTS_DEVICE`, `TTS_SAMPLE_RATE`.
- Note: TTS-VI model card is research-use; commercial licensing to be confirmed
  separately.

## Validation

| Layer | Expected proof |
| --- | --- |
| Unit | Mock TTS; verify synthesize() called with correct text; output is non-empty bytes |
| Integration | Real model + text input → non-silent 24 kHz audio chunk |
| E2E | — |
| Platform | GB10: CUDA; M4: CPU/slower |
| Release | Audio quality review on M4; domino gap measurement |

## Harness Delta

None.

## Evidence

