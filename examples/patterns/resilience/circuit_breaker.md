# Circuit breaker

**Category:** Resilience  
**Demo:** [circuit_breaker.pys](circuit_breaker.pys)  
**Wikipedia / ref:** [Circuit breaker](https://en.wikipedia.org/wiki/Circuit_breaker_design_pattern)

## Intent

Stop calling a failing dependency (Open), then probe (HalfOpen).

## Prompting an AI

**Say this:** “Implement Closed/Open/HalfOpen circuit breaker around a remote port.”

**Not this:** “Keep hammering a down service.”

**Confusion to avoid:** Circuit breaker ≠ Retry alone.

## Run

```text
python -m transpiler run examples/patterns/resilience/circuit_breaker.pys
```
