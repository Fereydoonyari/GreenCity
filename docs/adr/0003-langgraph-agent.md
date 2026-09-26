# ADR-0003: Use LangGraph for Agent Orchestration

## Status

Accepted

## Context

Analysis is a multi-step workflow (imagery → indices → GIS → population → scoring → explanation). An agent should decide tool order and handle retries, but must not reimplement scientific algorithms inside prompts.

## Decision

Use LangGraph to orchestrate tools that call application use cases / domain services. The LLM plans and explains; deterministic pipelines compute indicators and scores.

## Consequences

### Positive

- Explicit, inspectable graph of analysis steps.
- Extensible: new tools register without rewriting the whole pipeline.
- Clear separation between orchestration and computation.

### Negative

- Additional dependency and operational cost (LLM API).
- Requires careful tool contracts and evaluation harnesses.

## Alternatives Considered

- Hard-coded sequential pipeline only — simpler, less adaptable to partial failures / optional data.
- Ad-hoc LLM function calling without a graph — harder to visualize, test, and resume jobs.
