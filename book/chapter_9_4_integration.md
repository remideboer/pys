# 10.4. Integration — events, outbox, saga, request–reply

You already saw [CQRS](../examples/patterns/messaging/cqrs.pys) and
[publish–subscribe](../examples/patterns/messaging/publish_subscribe.pys).
These add the names engineers use for **distributed workflows**.

## Event sourcing

Append **events**; fold them to state. Often paired with CQRS — not the same
thing.

Demo: [`event_sourcing.pys`](../examples/patterns/messaging/event_sourcing.pys)

**Output:**

```text
shipped
True
```

## Transactional outbox

Write the domain change **and** an outbox row together; a relay publishes later.

Demo: [`outbox.pys`](../examples/patterns/messaging/outbox.pys)

**Output (shape):**

```text
True
publish:orders:O-7
1
True
```

## Saga

Multi-step process with **compensations** when a later step fails.

Demo: [`saga.pys`](../examples/patterns/messaging/saga.pys)

**Output:**

```text
reserve:ok
charge:ok
completed
reserve:ok
charge:fail
reserve:undo
aborted:charge
```

## Request–reply

**Correlation id** links a reply to its request.

Demo: [`request_reply.pys`](../examples/patterns/messaging/request_reply.pys)

**Output:**

```text
echo:ping
True
```

### Prompt dialogue

> **You:** Use a transactional outbox when placing an order, and a saga for
> reserve-stock then charge-card with compensation.
>
> **Not:** “Call three microservices and hope.”

### Confusion card

| Name | Idea |
|------|------|
| CQRS | Split read/write models |
| Event sourcing | State from event log |
| Outbox | Reliable publish after commit |
| Saga | Compensating long transaction |

---

[Previous: Resilience](chapter_9_3_resilience.md) · [Next: Test doubles](chapter_9_5_test_doubles.md)
