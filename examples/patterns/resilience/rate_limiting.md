# Rate limiting

**Category:** Resilience  
**Demo:** [rate_limiting.pys](rate_limiting.pys)  
**Wikipedia / ref:** [Rate limiting](https://en.wikipedia.org/wiki/Rate_limiting)

## Intent

Allow only N actions per window.

## Prompting an AI

**Say this:** “Fixed-window limiter limit=2; advanceWindow resets.”

**Not this:** “Accept unlimited login attempts.”

**Confusion to avoid:** Rate limit ≠ Circuit breaker.

## Run

```text
python -m transpiler run examples/patterns/resilience/rate_limiting.pys
```
