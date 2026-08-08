# 10.3. Resilience — when dependencies fail

Production systems assume **failure**. These names tell an AI (and a teammate)
how you want failure handled. Demos are **in-process fakes** — no sockets.

## Retry

Repeat up to N times.

<figure class="concept-diagram" role="img" aria-label="Attempt loop until success or max attempts reached">
  <div class="diagram-flow" style="min-width:30rem">
    <div class="diagram-box"><strong>try</strong><span>call port</span></div>
    <div class="diagram-arrow" aria-hidden="true">→</div>
    <div class="diagram-box"><strong>ERR?</strong><span>attempt++</span></div>
    <div class="diagram-arrow" aria-hidden="true">→</div>
    <div class="diagram-box diagram-layer-core" style="border:2px solid var(--accent);background:#e5edff;padding:0.7rem;border-radius:6px;text-align:center">
      <strong>ok or failed:N</strong>
      <span>stop at budget</span>
    </div>
  </div>
  <figcaption>
    Retry has a ceiling — not an infinite loop.
  </figcaption>
</figure>

Demo: [`retry.pys`](../examples/patterns/resilience/retry.pys)

**Output:**

```text
ok:3
failed:2
```

## Timeout

Logical **step budget** (teaching). Wall-clock timers need platform support.

<figure class="concept-diagram" role="img" aria-label="Work consumes steps until done or budget exceeded">
  <div class="diagram-stack">
    <div class="diagram-box"><strong>Budget = 2 steps</strong><span>logical timer</span></div>
    <div class="diagram-box diagram-outside"><strong>Work needs 5</strong><span>still running…</span></div>
    <div class="diagram-box" style="border:2px solid #8a6d3b;background:#f5ecd8;padding:0.7rem;border-radius:6px;text-align:center">
      <strong>timeout</strong>
      <span>stop — do not wait forever</span>
    </div>
  </div>
  <figcaption>
    A budget is a hard stop, independent of retry.
  </figcaption>
</figure>

Demo: [`timeout.pys`](../examples/patterns/resilience/timeout.pys)

**Output:**

```text
ok:3
timeout:3
```

## Circuit breaker

States: **Closed → Open → HalfOpen**. Stop calling a sick dependency.

<figure class="concept-diagram" role="img" aria-label="Circuit breaker states CLOSED OPEN HALF_OPEN with OPEN active">
  <div class="diagram-states">
    <div class="diagram-state"><span>calls flow</span>CLOSED</div>
    <div class="diagram-arrow" aria-hidden="true">→</div>
    <div class="diagram-state is-active"><span>short-circuit</span>OPEN</div>
    <div class="diagram-arrow" aria-hidden="true">→</div>
    <div class="diagram-state"><span>probe once</span>HALF_OPEN</div>
  </div>
  <figcaption>
    After enough failures the breaker opens; later a probe may close it again.
  </figcaption>
</figure>

Demo: [`circuit_breaker.pys`](../examples/patterns/resilience/circuit_breaker.pys)

**Output:**

```text
err
err
OPEN
short-circuit
short-circuit
ok
CLOSED
```

## Bulkhead

Cap concurrent **slots** so one workload cannot take all capacity.

<figure class="concept-diagram" role="img" aria-label="Two full slots and one blocked tryEnter">
  <div class="diagram-slot-row">
    <div class="diagram-slot is-full">1</div>
    <div class="diagram-slot is-full">2</div>
    <div class="diagram-slot is-blocked">×</div>
  </div>
  <figcaption>
    Quota full — the third caller is refused until a slot is freed.
  </figcaption>
</figure>

Demo: [`bulkhead.pys`](../examples/patterns/resilience/bulkhead.pys)

**Output:**

```text
True
True
False
True
2
```

## Fallback

Primary fails → secondary path.

<figure class="concept-diagram" role="img" aria-label="Primary miss then fallback cache path">
  <div class="diagram-flow" style="min-width:30rem">
    <div class="diagram-box"><strong>Primary</strong><span>live catalog</span></div>
    <div class="diagram-arrow" aria-hidden="true">miss</div>
    <div class="diagram-box diagram-layer-core" style="border:2px solid var(--accent);background:#e5edff;padding:0.7rem;border-radius:6px;text-align:center">
      <strong>Fallback</strong>
      <span>stale cache path</span>
    </div>
  </div>
  <figcaption>
    Degrade gracefully instead of returning nothing useful.
  </figcaption>
</figure>

Demo: [`fallback.pys`](../examples/patterns/resilience/fallback.pys)

**Output:**

```text
45.99
stale:BG-999
```

## Rate limiting

Allow N actions per window.

<figure class="concept-diagram" role="img" aria-label="Fixed window allows two then rejects until window advances">
  <div class="diagram-flow" style="min-width:28rem">
    <div class="diagram-box"><strong>Window</strong><span>count 0→2</span></div>
    <div class="diagram-arrow" aria-hidden="true">→</div>
    <div class="diagram-box diagram-outside"><strong>3rd call</strong><span>deny</span></div>
    <div class="diagram-arrow" aria-hidden="true">→</div>
    <div class="diagram-box"><strong>advanceWindow</strong><span>count resets</span></div>
  </div>
  <figcaption>
    Protect capacity with a simple fixed window in the teaching demo.
  </figcaption>
</figure>

Demo: [`rate_limiting.pys`](../examples/patterns/resilience/rate_limiting.pys)

**Output:**

```text
True
True
False
True
```

## Idempotency

Same client key → same result; duplicates do not create twice.

<figure class="concept-diagram" role="img" aria-label="Same idempotency key returns stored result on second call">
  <div class="diagram-stack">
    <div class="diagram-box"><strong>key-1 → create O-1</strong><span>first call stores result</span></div>
    <div class="diagram-box diagram-layer-core" style="border:2px solid var(--accent);background:#e5edff;padding:0.7rem;border-radius:6px;text-align:center">
      <strong>key-1 again</strong>
      <span>replay same result · no second create</span>
    </div>
  </div>
  <figcaption>
    Retries become safe when the key is the identity of the intent.
  </figcaption>
</figure>

Demo: [`idempotency.pys`](../examples/patterns/resilience/idempotency.pys)

**Output:**

```text
created:O-1
replay:created:O-1
created:O-2
```

### Prompt dialogue

> **You:** Wrap the payment port in a circuit breaker (threshold 2) and make
> create-order idempotent by `Idempotency-Key`.
>
> **Not:** “Make it resilient” with no named pattern.

### Confusion

Retry ≠ Circuit breaker ≠ Rate limit. Often combine: retry inside, breaker
outside, idempotency on writes.

---

[Previous: Authorization](chapter_9_2_authorization.md) · [Next: Integration](chapter_9_4_integration.md)
