# Voice Loop — Product Contract

## Architecture

```
FE :8000  ←→  AI Service :7700 (WS)  ←→  LLM (OpenAI-compat HTTPS)
                     ↕
              BE :9000 (HTTP tool calls)
```

FE captures mic audio, streams PCM over WebSocket to the AI service.
AI runs VAD endpointing → STT → LLM(stream+tools) → sentence splitter → TTS worker pool → ordered audio queue → streams audio chunks back to FE.

## Real-Time Turn Lifecycle

```
User speaks
  → FE VAD: speech start within 200 ms, stream 16 kHz mono PCM
  → FE VAD: silence ≥ silence_ms (default 800 ms) → emit utterance_end once
  → AI: STT pass → transcript(role:user) → FE chatbox
  → AI: LLM stream + tools → tokens accumulate into sentences
  → AI: sentence N complete → TTS synth(sentence, seq, gen_id)
  → AI: audio_chunk(seq, gen_id) + transcript(assistant) → FE
  → FE: play strictly by seq; sentence N+1 generated while N plays
```

## Session State Machine

```
LANDING ──(click EN/VI)──► GREETING ──► LISTENING ⇄ THINKING ⇄ SPEAKING
   ▲                                          │           │         │
   │                                          └─ barge-in ┴─────────┘
   └── IDLE_TIMEOUT(30s) / "goodbye" / End button ◄────────────────┘
```

State transitions:
- **LANDING → GREETING:** Language chosen; session created; greeting audio plays (<300 ms).
- **GREETING → LISTENING:** Greeting complete; mic opens.
- **LISTENING → THINKING:** `utterance_end` received; STT starts.
- **THINKING → SPEAKING:** First TTS audio chunk ready.
- **SPEAKING → LISTENING:** All audio chunks played; ready for next utterance.
- **Any → LANDING:** 30 s idle / End button / "goodbye" intent; session wiped.

## Barge-In

While `SPEAKING`, sustained VAD ≥ `barge_in_min_ms` (default 300 ms):
1. FE stops playback and clears audio queue within 200 ms.
2. FE sends `interrupt{gen_id}` event.
3. AI cancels LLM stream and TTS jobs for that `gen_id`; drops stale chunks.
4. State returns to `LISTENING`.

Echo guard: browser AEC (`echoCancellation/noiseSuppression/autoGainControl`) +
raised VAD threshold during `SPEAKING` prevents self-interruption.

## Session Object

```
session_id, language (en|vi), state, conversation[], slot_state, gen_id
```

## Models & Runtime

| Module | Model | Runtime | GB10 | M4 (demo) |
|--------|-------|---------|------|-----------|
| STT-VI | `g-group-ai-lab/gipformer-65M-rnnt` | ONNX via sherpa-onnx | CPU/CUDA | CPU |
| STT-EN | `nvidia/parakeet-tdt-0.6b-v3` | NeMo | CUDA | CPU/MPS slower |
| TTS-VI | `kjanh/KhanhTTS-OmniVoice` (default voice) | PyTorch diffusion | CUDA | slower |
| TTS-EN | ChatterBox / Turbo (default voice) | PyTorch | CUDA >RT | OK |

Audio format: STT expects 16 kHz mono PCM; TTS outputs 24 kHz; AI service resamples.

## VAD Configuration

| Parameter | Default | Description |
|-----------|---------|-------------|
| `VAD_SILENCE_MS` | 800 | Silence duration triggering utterance end. |
| `VAD_MIN_SPEECH_MS` | 250 | Minimum speech duration to register. |
| `VAD_THRESHOLD` | 0.5 | Silero VAD activation threshold. |
| `BARGE_IN_MIN_MS` | 300 | Sustained speech during SPEAKING to trigger barge-in. |

## WebSocket Protocol

Binary frames: 16 kHz mono PCM audio (FE → AI).

JSON events (both directions):

| Event | Direction | Fields |
|-------|-----------|--------|
| `session_start` | AI → FE | `session_id, language` |
| `utterance_end` | FE → AI | `session_id` |
| `transcript` | AI → FE | `role (user\|assistant), text, session_id` |
| `audio_chunk` | AI → FE | `seq, gen_id, data (base64 PCM 24kHz)` |
| `interrupt` | FE → AI | `gen_id` |
| `state_change` | AI → FE | `state` |
| `session_end` | FE → AI | `session_id, reason` |

## Latency Harness

Every turn must log timestamps for:
- `utterance_end` received
- STT done
- LLM first token
- First TTS audio ready
- First FE playback start

Per-turn latency summary must be retrievable after session.
