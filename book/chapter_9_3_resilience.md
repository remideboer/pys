# 10.3. Resilience — when dependencies fail

Production systems assume **failure**. These names tell an AI (and a teammate)
how you want failure handled. Demos are **in-process fakes** — no sockets.

## Retry

Repeat up to N times.

Demo: [`retry.pys`](../examples/patterns/resilience/retry.pys)

**Output:**

```text
ok:3
failed:2
```

## Timeout

Logical **step budget** (teaching). Wall-clock timers need platform support.

Demo: [`timeout.pys`](../examples/patterns/resilience/timeout.pys)

**Output:**

```text
ok:3
timeout:3
```

## Circuit breaker

States: **Closed → Open → HalfOpen**. Stop calling a sick dependency.

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


Cap concurrent **slots** so one workload cannot take all capacity.

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

Demo: [`fallback.pys`](../examples/patterns/resilience/fallback.pys)

**Output:**

```text
45.99
stale:BG-999
```

## Rate limiting

Allow N actions per window.

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
