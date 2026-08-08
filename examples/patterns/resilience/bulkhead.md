# Bulkhead

**Category:** Resilience  
**Demo:** [bulkhead.pys](bulkhead.pys)  
**Wikipedia / ref:** [Bulkhead](https://en.wikipedia.org/wiki/Bulkhead_(computing))

## Intent

Limit concurrent slots so one workload cannot exhaust all capacity.

## Prompting an AI

**Say this:** “Bulkhead with maxSlots=2; third tryEnter fails until leave.”

**Not this:** “Share one unbounded pool for all traffic.”

**Confusion to avoid:** Teaching slots ≠ OS thread pool.

## Run

```text
python -m transpiler run examples/patterns/resilience/bulkhead.pys
```
