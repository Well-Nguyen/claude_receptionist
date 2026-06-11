# US-P1-4 Audio fidelity

## Status

in-progress

## Lane

normal

## Product Contract

The audio pipeline carries PCM at the correct sample rates end-to-end with no
pitch or speed distortion. FE captures at 16 kHz mono and streams it; AI
service buffers the frames and passes accumulated PCM to STT; TTS outputs
24 kHz and FE plays it back at the same rate.

## Relevant Product Docs

- `SPEC.md` §6 (Models & Runtime), §7 (Turn lifecycle), §14 (NFRs)

## Acceptance Criteria

- Given the FE is capturing, when binary PCM frames arrive at the AI service
  over WebSocket, then each frame is appended to the session's PCM buffer.
- Given `utterance_end`, when STT is invoked, then it receives the accumulated
  16 kHz mono Int16 PCM (not empty bytes).
- Given session reset or new utterance, then the PCM buffer is cleared.
- Given TTS synthesizes a sentence, then the output is 24 kHz mono Int16 PCM
  and the FE `AudioContext` plays it at the correct pitch and speed.
- Given the FE `AudioContext({ sampleRate: 16000 })`, then mic input arrives at
  the AI service as 16 kHz mono — no additional resampling needed in the AI
  service for STT.

## Design Notes

- `Session.pcm_buffer: list[bytes]` accumulates binary frames per utterance.
- Buffer cleared in `_reset_session` and at the start of each new utterance.
- `ai/services/stt.py` defines the `STTService` Protocol; concrete impls
  receive `pcm: bytes` already at 16 kHz.
- `ai/services/tts.py` defines the `TTSService` Protocol; concrete impls
  return Int16 PCM bytes at 24 kHz.
- FE `player/index.ts` already sets `AudioContext({ sampleRate: 24000 })` — no
  FE change required.

## Validation

| Layer | Expected proof |
| --- | --- |
| Unit | PCM buffer accumulates frames; clears on reset; stub STT receives non-empty bytes |
| Integration | Turn with real binary frames → STT receives all bytes; TTS output plays at 24 kHz |
| E2E | — |
| Platform | — |
| Release | — |

## Harness Delta

None.

## Evidence

