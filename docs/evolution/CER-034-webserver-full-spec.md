# CER-034: Webserver full-spec remainder (F-007)

| | |
| --- | --- |
| Status | Accepted |
| Date | 2026-08-07 |
| Source | [F-007](../TODO-FUTURE.md#f-007-webserver-full-spec-remainder); `examples/webserver/` |
| Scope | `retry.executeOnPool`, `pool.acquireCount`, `ConnQueue.tryPutConn`, `MockDownstream` faults, write timeouts, soak docs |

## Context

After F-006 relocated the teaching webserver to `src/` + `tests/`, several
full-spec items remained deferred: FR8 pool re-checkout on retry, Toxiproxy-class
fault injection, inbound 429 shedding distinct from pool 503, write-timeout
parity, and a ≥1k soak path.

## Entries

### 1. FR8 — new pool checkout per retry

- **Pre-behavior:** `proxyThrough` / `createOrder` acquired one pool slot,
  held it across `RetryPolicy.execute` (including backoff), then released.
- **Why it hurt:** Violated FR8 / §10.2; retries did not compete for bulkhead
  capacity; E6 could not observe acquire volume matching attempts.
- **Post-behavior:** `RetryPolicy.executeOnPool` does acquire → invoke →
  release per attempt; backoff sleeps with no held slot; `DownstreamPool`
  tracks `acquireCount`.
- **Evidence:** `tests/test_integration.pys` E6; `tests/test_faults.pys`
  executeOnPool acquires.

### 2. MockDownstream as Toxiproxy equivalent

- **Pre-behavior:** Only `setFailNext` / `setLatencyMs`.
- **Why it hurt:** D/E scenarios needed reset and fatal shapes without
  requiring an external Toxiproxy process for teaching CI.
- **Post-behavior:** `setResetNext`, `setFatalNext`, `clearFaults`; documented
  in `load/README.md`; covered by `tests/test_faults.pys`.
- **Evidence:** fault suite + load README mapping table.

### 3. FR4 inbound 429 vs downstream 503

- **Pre-behavior:** Acceptor always enqueued; overload only surfaced as pool
  503 (or stall).
- **Why it hurt:** Spec requires correct 429 vs 503; silent queue growth.
- **Post-behavior:** `ConnQueue(maxPending)` + `tryPutConn`; acceptor sends
  429 `inbound_full` and increments `pys_reject_inbound_full_total`.
- **Evidence:** `tests/test_inbound_shed.pys`; `main.pys` acceptor path;
  overload k6 counts 429.

### 4. Write-timeout enforcement

- **Pre-behavior:** `writeTimeoutMs` existed in config but was unused.
- **Why it hurt:** Read/idle deadlines without write parity.
- **Post-behavior:** `ConnHandler` sets socket timeout before HTTP/1.1 write;
  HTTP/2 `serve` takes `writeTimeoutSec` around sends.
- **Evidence:** wired from `cfg.writeTimeoutMs` in `main.pys` and e2e constructors.

### 5. Soak as manual gate

- **Pre-behavior:** Teaching-scale k6 only; H1–H3 listed deferred.
- **Why it hurt:** Claiming full-spec without a documented 1k path.
- **Post-behavior:** `load/k6/soak.js` + `load/SOAK.md` — manual, not CI.
- **Evidence:** SOAK.md pass criteria (FD/RSS, 429/503 shedding).

## Trade-offs

- Real Toxiproxy remains optional; mock fidelity is teaching-grade.
- 1k soak is not a CI job (runner FD / duration limits).
- Inbound shed uses single-producer `qsize` check (no PYS try/catch for
  `queue.Full`).
