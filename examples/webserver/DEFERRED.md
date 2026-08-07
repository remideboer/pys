# examples/webserver deferred remaining work

All items from [F-007](../../docs/TODO-FUTURE.md#f-007-webserver-full-spec-remainder)
are delivered for this teaching example:

| Spec item | Delivery |
|-----------|----------|
| **FR8** re-checkout | `RetryPolicy.executeOnPool` — acquire → invoke → release per attempt |
| **Toxiproxy equiv.** | `MockDownstream` fail/reset/fatal/latency; `tests/test_faults.pys` |
| **FR4 429 vs 503** | Bounded `ConnQueue.tryPutConn` → 429 `inbound_full`; pool → 503 |
| **Write timeout** | `writeTimeoutMs` applied before HTTP/1.1 and HTTP/2 sends |
| **FR1 / soak** | Manual gate: [`load/SOAK.md`](load/SOAK.md) + `load/k6/soak.js` (not CI) |

Teaching increments 1–6 remain the baseline. External Toxiproxy is still
optional if you prefer a real proxy in front of a live dependency.
