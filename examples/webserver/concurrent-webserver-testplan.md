# Test Plan: Concurrent Web Server (I/O-Bound, Downstream-Bottlenecked)

**Reference**: `concurrent-webserver-spec.md`
**Purpose**: verify FR1–FR12 and associated NFRs under realistic and adversarial conditions. Traceability to spec IDs is maintained per test case.

---

## 1. Test Levels

| Level | Scope | Owner |
|---|---|---|
| Unit | Circuit breaker state machine, retry backoff calculation, idempotency lookup | Dev |
| Integration | Handler ↔ pool ↔ circuit breaker ↔ mock downstream | Dev/QA |
| System/Load | Full server under concurrent client load, real or simulated downstream | QA |
| Chaos/Fault-injection | Downstream latency/failure injection during load | QA |
| Soak | Extended duration under sustained load | QA |

---

## 2. Tooling

| Purpose | Tool | Notes |
|---|---|---|
| Load generation (persistent connections, HTTP/1.1 & HTTP/2) | **k6** | Scriptable scenarios, native metrics export, supports ramping/staged VUs |
| Load generation (raw throughput baseline) | **wrk2** | Constant-throughput mode avoids coordinated omission bias |
| Load generation (alternative, HTTP/2 multiplex focus) | **vegeta** | Attack/report model, easy p99 extraction |
| Fault injection on downstream (latency, timeout, connection reset, error rate) | **Toxiproxy** | Programmable proxy sitting between server and downstream |
| Downstream mocking (deterministic responses for integration tests) | **WireMock** / **httptest** (language-native) | Used below system level |
| Circuit breaker / retry unit tests | Language-native test framework (e.g. `pytest`, `go test`, `jest`) | Table-driven tests for state transitions |
| Metrics validation | **Prometheus** + **Grafana** | Scrape server's `/metrics`; assert on pool utilization, circuit state, queue depth |
| Log/trace validation | **grep/jq** on structured JSON logs, or **Jaeger** if tracing is instrumented | Verify correlation ID propagation through retries |
| OS-level resource monitoring | `ss -s`, `lsof`, `vmstat`, `netstat`, cgroup memory stats | FD count, memory growth during soak |
| TLS handshake load | k6 with `https` protocol, or `openssl s_client` scripted loop | Verify FR5 under concurrency |
| CI gate for idempotency classification | Custom lint script (grep endpoint definitions against classification table) | Enforces PR1/PR4 from spec §5 |

---

## 3. Test Environment

| Parameter | Value |
|---|---|
| Server | Single node, resource-limited to production-equivalent spec (CPU/RAM/FD limits) |
| Downstream | Toxiproxy-fronted real dependency (or high-fidelity mock) to allow fault injection without touching production data |
| Network | Load generator and server on separate hosts/containers to avoid loopback artifacts skewing latency |
| Baseline tuning | `ulimit -n` and `somaxconn` set per spec §4 before any test run; documented in test report |

---

## 4. Test Scenarios and Test Cases

### Scenario A — Baseline Concurrency (FR1, FR2, NFR: concurrency target)

| ID | Test Case | Steps | Expected Result | Tooling |
|---|---|---|---|---|
| A1 | 1,000 concurrent HTTP/1.1 keep-alive connections, healthy downstream | Ramp k6 VUs to 1,000 over 30s, hold 5 min | No connection refusals; p99 latency within target; 0% error rate | k6 |
| A2 | 1,000 concurrent HTTP/2 multiplexed streams | Same as A1, `--http2` | Streams multiplex correctly over fewer TCP connections; latency comparable to A1 | k6, vegeta |
| A3 | TLS handshake under concurrent ramp | Ramp to 1,000 concurrent new TLS connections (no keep-alive) | Handshake success rate 100%; handshake latency stays bounded (no FD/CPU starvation) | k6 (https), openssl s_client loop |
| A4 | Mixed short-lived request burst | 1,000 concurrent requests, each <500ms duration, closed after response | All complete within NFR latency target; no connection backlog growth | wrk2 |

### Scenario B — Overload / Graceful Degradation (FR4)

| ID | Test Case | Steps | Expected Result | Tooling |
|---|---|---|---|---|
| B1 | 110% of target concurrency | Ramp to 1,100 concurrent, healthy downstream | Excess requests receive 503, not connection drop/timeout; server process remains stable | k6 |
| B2 | 150% of target concurrency | Ramp to 1,500 concurrent | Same as B1; verify no crash, no unbounded memory growth | k6 + vmstat |
| B3 | Overload recovery | After B2, ramp back to 0, then to 500 | Server returns to normal service levels; no residual degradation (stuck connections, leaked FDs) | k6 + lsof |

### Scenario C — Downstream Pool & Bulkhead (FR9, FR11, FR12)

| ID | Test Case | Steps | Expected Result | Tooling |
|---|---|---|---|---|
| C1 | Pool exhaustion under normal concurrency | Set downstream pool to 100; drive 1,000 concurrent requests to endpoint using that pool | ~900 requests queue for slot; queue bounded per FR12; excess beyond queue limit → 503 fail | k6 + Prometheus (pool utilization metric) |
| C2 | Queue wait timeout | Configure max wait for pool checkout; sustain pool exhaustion beyond that wait | Requests waiting longer than configured max wait receive 503, not indefinite hang | k6 |
| C3 | Bulkhead isolation across two downstreams | Exhaust pool for Downstream A; simultaneously drive normal load against Downstream B | Downstream B requests unaffected (latency/error rate within baseline) | k6 (two scenarios in parallel) + Toxiproxy on A only |
| C4 | Pool sizing independence from inbound concurrency | Increase inbound concurrency from 500→1,000 with fixed pool size | Pool utilization metric caps at pool size; does not scale 1:1 with inbound connections | Prometheus |

### Scenario D — Circuit Breaker (FR10, NFR: fail-fast <10ms)

| ID | Test Case | Steps | Expected Result | Tooling |
|---|---|---|---|---|
| D1 | Trip circuit via error rate | Toxiproxy injects downstream 5xx above configured threshold | Circuit transitions closed → open; subsequent calls fail fast | Toxiproxy + Prometheus (circuit state metric) |
| D2 | Trip circuit via latency | Toxiproxy injects downstream latency above threshold | Circuit opens on latency SLO breach, independent of error rate | Toxiproxy |
| D3 | Fail-fast latency measurement | With circuit open, issue 100 requests | Median rejection latency <10ms; downstream receives zero forwarded calls during open state | k6 + server access logs (verify no downstream call) |
| D4 | Half-open recovery | After open-state timeout elapses, Toxiproxy fault removed | Circuit transitions open → half-open → closed on successful probe; verify limited probe traffic during half-open, not full traffic resumption | Prometheus (state transition log) |
| D5 | Half-open re-trip | During half-open, Toxiproxy re-injects failure on probe | Circuit returns to open; does not flap to fully closed on a single success | Toxiproxy + Prometheus |

### Scenario E — Retry Policy (FR7, FR8, §6 parameters)

| ID | Test Case | Steps | Expected Result | Tooling |
|---|---|---|---|---|
| E1 | Retry on transient failure, idempotent endpoint | Toxiproxy injects single transient timeout, then allows success | Request succeeds after retry; total attempts ≤3; correlation ID identical across attempts | Toxiproxy + log inspection |
| E2 | No retry on non-idempotent endpoint | Same fault injection against endpoint classified Unsafe | Request fails on first attempt; no retry issued (verify via downstream call count) | Toxiproxy + access logs |
| E3 | Retry does not bypass open circuit | Open circuit (per D1), issue request to retry-eligible endpoint | Retries are not attempted while circuit open; single fail-fast response | Toxiproxy + Prometheus |
| E4 | Retry budget enforcement | Sustain downstream error rate that would trigger retries on >10% of a rolling window's volume | Retry rate metric caps at configured budget; excess failures surfaced without retry | k6 (sustained load) + Prometheus |
| E5 | Backoff/jitter verification | Trigger repeated retries; capture inter-attempt timing | Delays follow exponential-with-jitter pattern (base 50ms ×2, ±20%); no fixed-interval retry storm | Log timestamp analysis |
| E6 | Retry counted against pool checkout | Monitor pool utilization during retry-heavy scenario (E1 at scale) | Each retry attempt consumes a pool slot acquisition (FR8); pool metrics reflect retry volume, not just unique requests | Prometheus |
| E7 | Total retry time fits client timeout | Configure max attempts × max backoff near client-facing timeout boundary | Client never observes a response later than the documented client-facing timeout | k6 (response time histogram) |

### Scenario F — Idempotency Classification Gate (§5, PR1–PR5)

| ID | Test Case | Steps | Expected Result | Tooling |
|---|---|---|---|---|
| F1 | Unclassified endpoint defaults to no retry | Add a new endpoint without a classification row; inject transient downstream failure | No retry attempted; single failure returned | Toxiproxy + access logs |
| F2 | CI gate blocks missing classification | Open a PR introducing a new endpoint without updating classification table | CI check fails, blocking merge | Custom lint script in CI pipeline |
| F3 | Safe-with-key endpoint deduplication | Send duplicate request with same idempotency key during a retry | Downstream receives effect exactly once; duplicate detected via dedup table/window | Integration test against mock downstream (WireMock) |

### Scenario G — Timeout Hierarchy (NFR: timeout ordering)

| ID | Test Case | Steps | Expected Result | Tooling |
|---|---|---|---|---|
| G1 | Verify strict ordering | Inspect configuration: downstream call timeout, handler timeout, client-facing timeout | downstream < handler < client-facing, confirmed in config and via induced-delay test | Config review + Toxiproxy staged delay test |
| G2 | Downstream timeout triggers before client-facing timeout | Toxiproxy delay set between downstream and handler timeout values | Client receives error response before client-facing timeout expires, driven by downstream timeout | k6 (response time assertion) |

### Scenario H — Soak / Resource Stability (NFR: memory, FD)

| ID | Test Case | Steps | Expected Result | Tooling |
|---|---|---|---|---|
| H1 | Sustained load, ≥10 min | Hold 1,000 concurrent connections for 30 min minimum | Memory usage plateaus (no monotonic growth); FD count stable | vmstat, lsof, Prometheus process metrics |
| H2 | Idle-connection memory footprint | Establish 1,000 idle keep-alive connections, measure per-connection memory | <50KB per idle connection (NFR target) | Process RSS delta / connection count |
| H3 | Long-duration circuit flapping | Alternate Toxiproxy fault on/off every 30s for 30 min | No memory/FD leak from repeated circuit state transitions | Prometheus + vmstat |

### Scenario I — Observability Validation (§7)

| ID | Test Case | Steps | Expected Result | Tooling |
|---|---|---|---|---|
| I1 | Metrics completeness | Query `/metrics` during A1 and C1 | Active connections, req/sec, latency percentiles, error rate, queue depth, pool utilization, circuit state all present and updating | Prometheus scrape + manual assertion |
| I2 | Root-cause distinguishability | Trigger a queue-full 503 (C1) and a circuit-open 503 (D1) separately | Logs/metrics clearly distinguish the two causes despite identical client-facing status code | Log inspection (structured field check) |
| I3 | Correlation ID propagation through retries | Trigger E1; inspect logs for all attempts | Single correlation ID present across all retry attempts for one client request | Log inspection / grep |

---

## 5. Entry / Exit Criteria

**Entry criteria**: idempotency classification table complete and reviewed (spec §5, PR1); test environment tuned per spec §4; Toxiproxy/mocks configured and validated independently before use in fault-injection cases.

**Exit criteria**: all Scenario A–B cases pass at target concurrency; no Sev-1/Sev-2 defect open in circuit breaker, retry budget, or pool bulkhead behavior (Scenarios C–E); soak test (H) shows no resource growth trend over test duration; observability cases (I) confirm root-cause distinguishability in logs/metrics.

---

## 6. Defect Severity Guidance

| Severity | Definition |
|---|---|
| Sev-1 | Process crash, unbounded resource growth, silent request drop (no response, no timeout) |
| Sev-2 | Incorrect status code under load, retry bypassing open circuit, non-idempotent endpoint retried |
| Sev-3 | Metric/log gap, latency target miss without functional failure |
| Sev-4 | Cosmetic/logging format issues |

---

## 7. Reporting

Each test run produces: raw tool output (k6/wrk2/vegeta JSON), Prometheus metric snapshots for the test window, and a pass/fail table keyed to test case IDs above, cross-referenced to spec requirement IDs (FR/NFR) for traceability.
