# Timeout

**Category:** Resilience  
**Demo:** [timeout.pys](timeout.pys)  
**Wikipedia / ref:** [Timeout](https://en.wikipedia.org/wiki/Timeout_(computing))

## Intent

Fail when a logical step budget is exceeded (teaching form; not OS threads).

## Prompting an AI

**Say this:** “Run work under a step budget; return timeout when exceeded.”

**Not this:** “Block forever waiting on a call.”

**Confusion to avoid:** Timeout ≠ Retry.

## Run

```text
python -m transpiler run examples/patterns/resilience/timeout.pys
```
