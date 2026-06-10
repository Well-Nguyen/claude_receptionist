# 0011 STT and TTS Model Selection

Date: 2026-06-10

## Status

Accepted

## Context

The kiosk requires Vietnamese and English STT and TTS, running locally on NVIDIA
GB10 (CUDA) and Apple M4 (MPS/CPU). Models must be open-weight (no API calls for
inference), produce real-time output on GB10, and support default voices only.

## Decision

| Module | Model | Runtime | Rationale |
|--------|-------|---------|-----------|
| STT-VI | `g-group-ai-lab/gipformer-65M-rnnt` | ONNX via sherpa-onnx | Small (65 M), ONNX portable, CPU/CUDA, MIT license |
| STT-EN | `nvidia/parakeet-tdt-0.6b-v3` | NeMo | State-of-art EN accuracy, CUDA-optimized, CC-BY-4.0 |
| TTS-VI | `kjanh/KhanhTTS-OmniVoice` (default voice) | PyTorch diffusion | Best available open VI TTS, apache-2.0 research |
| TTS-EN | ChatterBox / Turbo (default voice) | PyTorch | MIT, fast, good quality |

Audio format contract:
- STT input: 16 kHz mono PCM. AI service resamples from device capture rate.
- TTS output: 24 kHz. FE plays at correct pitch/speed.

## Alternatives Considered

1. **Whisper for STT-VI** — lower Vietnamese accuracy than gipformer for this domain; heavier. Rejected.
2. **Coqui TTS for Vietnamese** — less natural; KhanhTTS preferred. Rejected.
3. **Cloud STT/TTS APIs** — violates local-only constraint and adds latency. Rejected.

## Consequences

Positive:
- All models run fully offline on device; no cloud STT/TTS latency.
- sherpa-onnx provides CPU/CUDA portability for STT-VI.
- GB10 CUDA can hit < 400 ms STT and < 500 ms TTS targets per spec.

Tradeoffs:
- NeMo (STT-EN) is heavier; on M4 it falls back to CPU/MPS (slower, no crash).
- TTS-VI (KhanhTTS) has a research-use card; commercial licensing is separate.
- M4 TTS will be slower than GB10; acceptable as dev/demo environment.

## Follow-Up

- Agree on WER thresholds for VI and EN before P1 starts (see SPEC §19.1).
- Set false-barge-in threshold before P1 VAD tuning begins (see SPEC §19.1).
- Evaluate NeMo container strategy for GB10 (base image size vs. native install).
- GB10 model preloading at boot vs lazy-load: preload all models at boot (locked default).
