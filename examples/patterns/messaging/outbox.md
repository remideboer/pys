# Transactional outbox

**Category:** Messaging  
**Demo:** [outbox.pys](outbox.pys)  
**Wikipedia / ref:** [Transactional outbox](https://microservices.io/patterns/data/transactional-outbox.html)

## Intent

Write domain change and outbox message together; relay publishes later.

## Prompting an AI

**Say this:** “In-memory outbox: placeOrder appends message; relay drains.”

**Not this:** “Publish to a broker mid-transaction without an outbox.”

**Confusion to avoid:** Outbox ≠ Saga.

## Run

```text
python -m transpiler run examples/patterns/messaging/outbox.pys
```
