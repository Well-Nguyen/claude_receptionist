# 0010 LLM via OpenAI-Compatible API (vLLM-Ready)

Date: 2026-06-10

## Status

Accepted

## Context

The AI service needs an LLM with tool-calling and streaming support. The production
target (GB10) may run a local vLLM instance in the future. The dev/demo target (M4)
uses the OpenAI hosted API.

## Decision

Use the **OpenAI Python SDK** pointed at `OPENAI_BASE_URL` (default: `https://api.openai.com/v1`).
Future vLLM migration is a single config swap: change `OPENAI_BASE_URL` and `OPENAI_MODEL`.
No code changes needed.

Parameters controlled via env:
- `OPENAI_BASE_URL` — endpoint
- `OPENAI_MODEL` — model ID
- `LLM_TEMPERATURE` — 0.4 default
- `LLM_MAX_TOKENS` — 512 default

System prompt, tool schemas, and slot-filling logic are in English regardless of
session language. Voice I/O follows user-selected language.

## Alternatives Considered

1. **Direct vLLM client** — ties implementation to vLLM now; OpenAI SDK is
   equally capable and vLLM exposes OpenAI-compatible endpoints. Rejected.
2. **LangChain abstraction** — adds a heavy dependency with its own update cycle.
   Unnecessary for a bounded tool-calling use case. Rejected.

## Consequences

Positive:
- vLLM is a zero-code-change migration.
- OpenAI SDK handles streaming + tool-call delta parsing out of the box.
- Model can be swapped via env for performance testing.

Tradeoffs:
- OpenAI API costs during dev (before vLLM).
- Tool schema must stay within OpenAI function-calling spec for compatibility.

## Follow-Up

- Validate tool schemas against vLLM's OpenAI-compatible endpoint when vLLM is
  introduced (P4 or on-demand).
- Confirm model ID supports tool-calling before finalizing `OPENAI_MODEL` default.
