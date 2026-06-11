# US-P1-5 GB10 latency targets

## Status

implemented

## Lane

normal

## Product Contract

On GB10 production hardware with all four real models loaded, per-turn median
latencies meet the targets in SPEC §14. Gaps are documented with a tuning plan.

## Relevant Product Docs

- `SPEC.md` §14 (Non-functional requirements), §17.2 (US-P1-5 AC)

## Acceptance Criteria

- Given GB10 with CUDA and all four models loaded, then measured median latencies
  meet: STT < 400 ms, LLM first token < 700 ms, TTS first audio < 500 ms/sentence,
  first sound < ~1.5 s end-to-end.
- Given any target is missed, then a documented tuning path exists covering
  engine selection, quantization level, and worker-pool count.
- Given the existing latency harness (US-P0-8), then latency data is read from
  `/sessions/{id}/latency` without additional instrumentation.

## Design Notes

- Depends on US-P1-1, US-P1-2, US-P1-3 being integrated.
- Tuning levers: TTS worker count (`TTS_WORKERS`), STT batch size, NeMo half-precision.
- If GB10 hardware is unavailable, record gap + plan as the completion artifact.

## Validation

| Layer | Expected proof |
| --- | --- |
| Unit | — |
| Integration | Latency report from `/sessions/{id}/latency` on GB10 |
| E2E | — |
| Platform | GB10 only |
| Release | Median latency report or documented gap + tuning plan |

## Harness Delta

None.

## Evidence

### Gap: GB10 hardware unavailable (dev machine is macOS M4)

GB10 (CUDA) is not available in the current dev environment. Structural integration
tests in `ai/tests/integration/test_latency_targets.py` validate that:
- `/sessions/{id}/latency` returns all stage timestamps for every turn
- All per-stage durations are strictly positive
- Stages are monotonically ordered (utterance_end ≤ stt ≤ llm ≤ tts)

The four target-gate tests (`test_gb10_median_*`) are marked
`skipif(RUN_PLATFORM != "gb10")` and will assert the SPEC §14 targets when run
on production hardware.

### Tuning plan for GB10

| Lever | Env var | Default | Tuning note |
| --- | --- | --- | --- |
| TTS thread workers | `TTS_WORKERS` | OS default (ThreadPoolExecutor) | Raise to 2–4 on GB10 to overlap sentence synthesis |
| STT batch size (NeMo EN) | `STT_BATCH_SIZE` | 1 | Raise to 4–8 if queue depth allows |
| NeMo half-precision | `STT_HALF_PRECISION` | `false` | Set `true` on CUDA for ~1.5× throughput |
| STT thread count (Sherpa VI) | `STT_NUM_THREADS` | 4 | Raise to 8 on GB10 |
| TTS device | `TTS_DEVICE` | `auto` | Ensure `cuda` on GB10; `auto` selects it if available |

If STT median exceeds 400 ms on GB10: try `STT_HALF_PRECISION=true` + `STT_NUM_THREADS=8`.
If TTS median exceeds 500 ms: raise `TTS_WORKERS=4`.
If LLM first token exceeds 700 ms: profile LLM stub vs real model; real LLM is a separate story (E03).

