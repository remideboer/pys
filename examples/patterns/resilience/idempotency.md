# Idempotency

**Category:** Resilience  
**Demo:** [idempotency.pys](idempotency.pys)  
**Wikipedia / ref:** [Idempotency](https://en.wikipedia.org/wiki/Idempotence)

## Intent

Same idempotency key returns the same result; duplicate work is not redone.

## Prompting an AI

**Say this:** “Idempotent create-order keyed by client token; second call replays.”

**Not this:** “Create a new order on every retry.”

**Confusion to avoid:** Idempotency ≠ Exactly-once broker magic.

## Run

```text
python -m transpiler run examples/patterns/resilience/idempotency.pys
```
