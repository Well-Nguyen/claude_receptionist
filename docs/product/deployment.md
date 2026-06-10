# Deployment — Product Contract

## Target Environments

| Target | FE / BE / DB | AI service | GPU |
|--------|-------------|------------|-----|
| **GB10 (prod)** | Docker | Docker + `--gpus all` | CUDA |
| **M4 (dev/demo)** | Docker | Native uvicorn (MPS) or Docker CPU | MPS only outside Docker |

GB10 is the performance-representative environment. All latency targets are
validated on GB10.

## Folder Structure

```
project-root/
├── ai/
│   ├── main.py
│   ├── orchestrator/
│   │   ├── pipeline.py
│   │   ├── sentence_splitter.py
│   │   └── state.py
│   ├── services/
│   │   ├── stt/
│   │   ├── tts/
│   │   └── llm/
│   └── shared/
│       ├── schemas/
│       ├── be_client/
│       ├── deps/
│       ├── prompts/
│       └── audio/
├── be/
│   ├── main.py
│   ├── routers/
│   ├── models/
│   ├── schemas/
│   └── db/
│       ├── migrations/
│       └── seed/
├── fe/
│   └── voice-agent/
│       ├── pages/
│       │   └── Landing/
│       ├── components/
│       │   ├── Avatar/
│       │   ├── ChatBox/
│       │   └── InteractionPanel/
│       ├── audio/
│       │   ├── vad/
│       │   ├── capture/
│       │   └── player/
│       └── ws/
│           └── client/
└── docker/
    ├── Dockerfile.ai
    ├── Dockerfile.be
    ├── Dockerfile.fe
    └── compose.yaml   # profiles: gpu | cpu
```

## Docker Compose Profiles

- `gpu` — all services in Docker; AI service with `--gpus all`; for GB10.
- `cpu` — all services in Docker; AI service without GPU; for M4 demo / CI.

## Ports

| Service | Port |
|---------|------|
| FE (Voice Agent) | 8000 |
| AI service (WS) | 7700 |
| BE (FastAPI) | 9000 |
| PostgreSQL | 5432 |

## Model Checkpoints

Model weights are **not** baked into images. They are volume-mounted at runtime.
Checkpoint paths are configured via env vars.

## Environment Configuration

Key env vars (full template in `.env.template`):

| Variable | Purpose |
|----------|---------|
| `OPENAI_API_KEY` | LLM provider key |
| `OPENAI_BASE_URL` | LLM endpoint (OpenAI now; vLLM later) |
| `OPENAI_MODEL` | Model ID |
| `STT_VI_MODEL_PATH` | Path to sherpa-onnx gipformer checkpoint |
| `STT_EN_MODEL_PATH` | Path to parakeet checkpoint |
| `STT_DEVICE` | `auto` / `cuda` / `cpu` |
| `TTS_VI_MODEL` | KhanhTTS-OmniVoice HF id |
| `TTS_EN_ENGINE` | `chatterbox-turbo` |
| `TTS_DEVICE` | `auto` / `cuda` / `cpu` |
| `TTS_SAMPLE_RATE` | 24000 |
| `VAD_SILENCE_MS` | 800 |
| `VAD_THRESHOLD` | 0.5 |
| `BARGE_IN_MIN_MS` | 300 |
| `AI_WS_PORT` | 7700 |
| `FE_PORT` | 8000 |
| `BE_BASE_URL` | `http://be:9000` |
| `SESSION_IDLE_TIMEOUT_S` | 30 |
| `DATABASE_URL` | PostgreSQL connection string |

## One-Command Deploy (GB10)

```bash
docker compose --profile gpu up
```

FE reachable on LAN at `:8000` after all services healthy.

## M4 Dev/Demo

```bash
docker compose --profile cpu up
# or AI service native:
cd ai && uvicorn main:app --port 7700
docker compose up fe be db
```

## CI

Three Docker images must build in CI: `Dockerfile.ai`, `Dockerfile.be`, `Dockerfile.fe`.
`cpu` profile is the CI target.
