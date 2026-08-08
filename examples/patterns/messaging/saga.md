# Saga

**Category:** Messaging  
**Demo:** [saga.pys](saga.pys)  
**Wikipedia / ref:** [Saga](https://microservices.io/patterns/data/saga.html)

## Intent

Multi-step workflow with compensating actions on failure.

## Prompting an AI

**Say this:** “Saga: reserve then charge; on charge fail compensate reserve.”

**Not this:** “Distributed 2PC everywhere.”

**Confusion to avoid:** Saga ≠ two-phase commit.

## Run

```text
python -m transpiler run examples/patterns/messaging/saga.pys
```
