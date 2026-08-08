# Retry

**Category:** Resilience  
**Demo:** [retry.pys](retry.pys)  
**Wikipedia / ref:** [Retry](https://en.wikipedia.org/wiki/Retry_pattern)

## Intent

Repeat a failing operation up to N times.

## Prompting an AI

**Say this:** “Wrap the flaky port in a Retrier with maxAttempts and show success/fail cases.”

**Not this:** “Infinite retry with no budget.”

**Confusion to avoid:** Retry ≠ Circuit Breaker.

## Run

```text
python -m transpiler run examples/patterns/resilience/retry.pys
```
