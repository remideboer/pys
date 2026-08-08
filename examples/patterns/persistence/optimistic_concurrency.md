# Optimistic concurrency

**Category:** Persistence  
**Demo:** [optimistic_concurrency.pys](optimistic_concurrency.pys)  
**Wikipedia / ref:** [Optimistic concurrency](https://en.wikipedia.org/wiki/Optimistic_concurrency_control)

## Intent

Version field; reject stale writes.

## Prompting an AI

**Say this:** “updateIfVersion with expectedVersion; show stale failure.”

**Not this:** “Last write wins with no version check.”

**Confusion to avoid:** Optimistic ≠ pessimistic locking.

## Run

```text
python -m transpiler run examples/patterns/persistence/optimistic_concurrency.pys
```
