# US-P1-5 GB10 latency targets

## Status

planned

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

