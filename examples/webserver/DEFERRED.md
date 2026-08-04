# examples/webserver deferred remaining work

Remaining full-spec items are tracked as [F-007](../../docs/TODO-FUTURE.md#f-007-webserver-full-spec-remainder).

**Layout:** `src/` + `tests/` via `pys.toml` `[source_roots]` is in place (F-006).
Teaching increments 1–6 remain the working baseline.

Still deferred vs full concurrent-webserver spec/testplan:

- **FR8** — each retry acquires a new downstream pool checkout
- **Toxiproxy** (or equivalent) for D/E/H fault scenarios
- **FR4** — broader 429 capacity shedding if distinct from 503 queue-full
- **FR1 / soak** — real ≥1k concurrent / memory-FD soak (H1–H3)
- Write-timeout enforcement parity with read/idle/handler
