# Event sourcing

**Category:** Messaging  
**Demo:** [event_sourcing.pys](event_sourcing.pys)  
**Wikipedia / ref:** [Event sourcing](https://en.wikipedia.org/wiki/Event_sourcing)

## Intent

Append domain events; fold them to current state.

## Prompting an AI

**Say this:** “Event store + projection for order status; contrast with CQRS demo.”

**Not this:** “Overwrite a status column and call it event sourcing.”

**Confusion to avoid:** Event sourcing ≠ CQRS (often paired).

## Run

```text
python -m transpiler run examples/patterns/messaging/event_sourcing.pys
```
