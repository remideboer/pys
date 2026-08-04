# Concurrent webserver (PYS)

Project root for the I/O-bound concurrent HTTP server (see
`concurrent-webserver-spec.md` / `concurrent-webserver-testplan.md`).

## Canonical PYS style

- **OO**: `package class` / `package interface` for domain types.
- **Least privilege**: same-folder `package` exports only (no `global` app API).
- **Concurrency**: `tasks` / `task` acceptor + workers; `shared` queue/objects;
  instance locks where class fields need cross-task mutation.

## Run tests

```bash
python -m transpiler run examples/webserver/test_core.pys
python -m transpiler run examples/webserver/test_integration.pys
python -m transpiler run examples/webserver/test_http_e2e.pys
python -m transpiler run examples/webserver/test_http_keepalive_e2e.pys
python -m transpiler run examples/webserver/test_timeouts.pys
python -m transpiler run examples/webserver/test_https_e2e.pys
python -m transpiler run examples/webserver/test_http2_e2e.pys
python examples/webserver/scripts/check_idempotency.py
python -m pytest tests/test_webserver_idempotency_gate.py -q
```

First HTTP/2 run installs locked `h2` (see `pys.deps` / `pys.lock`). On another
OS/Python minor, refresh with `python -m transpiler deps lock examples/webserver/pys.deps`.

## Run server

```bash
python -m transpiler run examples/webserver/main.pys
curl http://127.0.0.1:8080/health
curl http://127.0.0.1:8080/proxy/data
curl http://127.0.0.1:8080/proxy/slow
curl http://127.0.0.1:8080/metrics
```

### HTTPS + HTTP/2 (FR5 / FR2)

Generate local certs first (never committed):

```bash
python examples/webserver/scripts/gen_dev_certs.py
```

In `main.pys`, set `cfg.tlsEnabled = true`. TLS advertises ALPN `h2` and
`http/1.1`; cleartext stays HTTP/1.1 only.

```bash
python -m transpiler run examples/webserver/main.pys
curl -k https://127.0.0.1:8080/health
curl -k --http2 https://127.0.0.1:8080/health
```

## Load (k6) — testplan A/B/C subsets

See [`load/README.md`](load/README.md). Example:

```bash
# terminal 1
python -m transpiler run examples/webserver/main.pys
# terminal 2
k6 run -e BASE_URL=http://127.0.0.1:8080 examples/webserver/load/k6/baseline.js
```

| k6 script | Testplan |
|-----------|----------|
| `load/k6/baseline.js` | A1 subset |
| `load/k6/overload.js` | B1 subset |
| `load/k6/pool_exhaust.js` | C1 subset |
| `load/k6/tls_handshake.js` | A3 subset (HTTPS; enable `tlsEnabled`) |
| `load/k6/http2_multiplex.js` | A2 subset (HTTPS+h2; enable `tlsEnabled`) |

On Linux/macOS for larger VU counts: `ulimit -n 65535`. This teaching server uses
4 worker tasks and a small downstream pool (default 8) — capacity is intentional
for FR9/FR12 demos, not a 1k-VU production tune.

## Layout

| File | Role |
|------|------|
| `config.pys` | `ServerConfig` |
| `circuit_breaker.pys` | `CircuitBreaker` (FR10) |
| `pool.pys` / `bulkhead.pys` | `DownstreamPool` / `Bulkheads` (FR9/11/12) |
| `idempotency.pys` + `.md` | §5 classification |
| `retry.pys` | `RetryPolicy` + `DownstreamCall` |
| `http11.pys` | HTTP/1.1 parse/write |
| `http2.pys` | HTTP/2 multiplex via `h2` (FR2) |
| `conn_handler.pys` | ALPN dispatch HTTP/1.1 vs HTTP/2 |
| `tls_term.pys` | TLS 1.2/1.3 + ALPN (FR5) |
| `certs/README.md` | How to generate local PEMs (gitignored) |
| `conn_queue.pys` | Acceptor→worker queue |
| `metrics.pys` | Counters + `/metrics` text |
| `mock_downstream.pys` | Inject latency/failures |
| `router.pys` | `AppContext` + `Router` (FR3) |
| `main.pys` | Accept + 4 worker tasks |
| `scripts/check_idempotency.py` | PR1/PR4 / F2 gate |
| `load/k6/*.js` | Load scenarios |
| `test_*.pys` | Same-package checks |

## Increment status

1. Core OO types — done  
2. HTTP/1.1 + router + mock + metrics + e2e — done  
3. k6 + idempotency lint — done  
4a. TLS termination (FR5) — done  
4b. HTTP/2 multiplex over TLS ALPN (FR2) — done  
5. HTTP/1.1 keep-alive (FR2) — done  
6. Timeout hierarchy (FR6) — done  

## Pending refactor (PYS-level)

`test_*.pys` live in this folder only so they share `package` visibility with
production types (today: same-folder rule). That is a language/tooling gap, not
the desired project shape.

**After** [F-006](../../docs/TODO-FUTURE.md#f-006-source-roots-and-same-package-tests) /
[ADR-017](../../docs/adr/ADR-017-source-roots-same-package-tests.md) (`pys.toml`
source roots: same package iff post-root relative paths match), refactor this
example into e.g. `src/` + `tests/` with mirrored paths — **without** widening
`package` members to `public`.
