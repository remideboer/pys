# 10.4. Integration — events, outbox, saga, request–reply

You already saw [CQRS](../examples/patterns/messaging/cqrs.pys) and
[publish–subscribe](../examples/patterns/messaging/publish_subscribe.pys).
These add the names engineers use for **distributed workflows**.

## Event sourcing

Append **events**; fold them to state. Often paired with CQRS — not the same
thing.

<figure class="concept-diagram" role="img" aria-label="Append-only event log folded into current status">
  <div class="diagram-stack">
    <div class="diagram-box"><strong>Created O-1</strong><span>append</span></div>
    <div class="diagram-box"><strong>Shipped O-1</strong><span>append</span></div>
    <div class="diagram-arrow" aria-hidden="true">↓ fold</div>
    <div class="diagram-box diagram-layer-core" style="border:2px solid var(--accent);background:#e5edff;padding:0.7rem;border-radius:6px;text-align:center">
      <strong>status = shipped</strong>
      <span>projection · not an overwrite-only column</span>
    </div>
  </div>
  <figcaption>
    State is derived from the log; do not confuse this with “just CQRS.”
  </figcaption>
</figure>

Demo: [`event_sourcing.pys`](../examples/patterns/messaging/event_sourcing.pys)

**Output:**

```text
shipped
True
```

## Transactional outbox

Write the domain change **and** an outbox row together; a relay publishes later.

<figure class="concept-diagram" role="img" aria-label="Same unit writes order and outbox then relay publishes">
  <div class="diagram-flow" style="min-width:32rem">
    <div class="diagram-box diagram-layer-core" style="border:2px solid var(--accent);background:#e5edff;padding:0.7rem;border-radius:6px;text-align:center">
      <strong>placeOrder</strong>
      <span>orders + outbox row</span>
    </div>
    <div class="diagram-arrow" aria-hidden="true">→</div>
    <div class="diagram-box"><strong>Relay</strong><span>drain · publish</span></div>
    <div class="diagram-arrow" aria-hidden="true">→</div>
    <div class="diagram-box diagram-outside"><strong>Broker / bus</strong><span>outside</span></div>
  </div>
  <figcaption>
    Publish after the write is durable — not mid-transaction hope.
  </figcaption>
</figure>

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

<figure class="concept-diagram" role="img" aria-label="Reserve then charge; on charge fail compensate reserve">
  <div class="diagram-stack">
    <div class="diagram-box"><strong>1. reserve</strong><span>ok</span></div>
    <div class="diagram-box" style="border:2px solid #8a6d3b;background:#f5ecd8;padding:0.7rem;border-radius:6px;text-align:center">
      <strong>2. charge</strong>
      <span>fail</span>
    </div>
    <div class="diagram-arrow" aria-hidden="true">↓ compensate</div>
    <div class="diagram-box diagram-outside"><strong>reserve:undo</strong><span>reverse earlier work</span></div>
  </div>
  <figcaption>
    Long workflows undo prior steps instead of pretending one big transaction.
  </figcaption>
</figure>

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

<figure class="concept-diagram" role="img" aria-label="Request and reply share correlation id c-1">
  <div class="diagram-flow" style="min-width:30rem">
    <div class="diagram-box"><strong>Request</strong><span>c-1 · ping</span></div>
    <div class="diagram-arrow" aria-hidden="true">→</div>
    <div class="diagram-box"><strong>Replier</strong><span>handle</span></div>
    <div class="diagram-arrow" aria-hidden="true">→</div>
    <div class="diagram-box diagram-layer-core" style="border:2px solid var(--accent);background:#e5edff;padding:0.7rem;border-radius:6px;text-align:center">
      <strong>Reply</strong>
      <span>c-1 · echo:ping</span>
    </div>
  </div>
  <figcaption>
    Without a correlation id, replies cannot find their waiting caller.
  </figcaption>
</figure>

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
