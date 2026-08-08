# Fallback

**Category:** Resilience  
**Demo:** [fallback.pys](fallback.pys)  
**Wikipedia / ref:** [Fallback](https://en.wikipedia.org/wiki/Fallback_pattern)

## Intent

Use a secondary path when the primary fails.

## Prompting an AI

**Say this:** “PriceFacade: primary catalog then cache fallback.”

**Not this:** “Return null and crash the UI.”

**Confusion to avoid:** Fallback ≠ Retry.

## Run

```text
python -m transpiler run examples/patterns/resilience/fallback.pys
```
