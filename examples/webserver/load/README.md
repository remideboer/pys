# Load & fault scripts (Increment 3 + F-007)

Maps to `concurrent-webserver-testplan.md` scenarios A/B/C at teaching scale.
Full ≥1k soak is a **manual** gate — see [`SOAK.md`](SOAK.md).

## Prerequisites

1. Install [k6](https://k6.io/docs/get-started/installation/).
2. From the **repo root**, start the server:

```bash
python -m transpiler run examples/webserver/src/main.pys
```

3. OS notes (spec §4): on Linux/macOS raise FDs before large runs (`ulimit -n 65535`).
   Windows: cap VUs to what the process can accept; this teaching server uses a
   small worker task set (4) and a downstream pool (default 8).

## Scripts

| Script | Testplan | Command |
|--------|----------|---------|
| `k6/baseline.js` | A1 subset | `k6 run -e BASE_URL=http://127.0.0.1:8080 examples/webserver/load/k6/baseline.js` |
| `k6/overload.js` | B1 subset | `k6 run -e BASE_URL=http://127.0.0.1:8080 examples/webserver/load/k6/overload.js` |
| `k6/pool_exhaust.js` | C1 subset | `k6 run -e BASE_URL=http://127.0.0.1:8080 examples/webserver/load/k6/pool_exhaust.js` |
| `k6/soak.js` | H1 manual | See [`SOAK.md`](SOAK.md) — not CI |
| `k6/tls_handshake.js` | A3 subset | Generate certs (`scripts/gen_dev_certs.py`), enable `cfg.tlsEnabled` in `src/main.pys`, then `k6 run -e BASE_URL=https://127.0.0.1:8080 examples/webserver/load/k6/tls_handshake.js` |
| `k6/http2_multiplex.js` | A2 subset | Same TLS setup, then `k6 run -e BASE_URL=https://127.0.0.1:8080 examples/webserver/load/k6/http2_multiplex.js` |

For faster pool saturation, lower `poolSize` in `src/config.pys` before starting `src/main.pys`,
and prefer `/proxy/slow` (250ms mock latency).

## Metrics during load

```bash
curl -s http://127.0.0.1:8080/metrics
```

| Metric | Meaning |
|--------|---------|
| `pys_reject_queue_full_total` | Downstream pool / bulkhead full → **503** |
| `pys_reject_circuit_open_total` | Circuit open → **503** |
| `pys_reject_inbound_full_total` | Inbound `ConnQueue` full → **429** |

## Fault injection (Toxiproxy equivalent)

Real Toxiproxy is optional. This example uses `MockDownstream` for D/E/H-shaped
faults without an external proxy:

| Knob | Effect |
|------|--------|
| `setFailNext(n)` | Next *n* invokes return `retryable` (after optional latency) |
| `setResetNext(n)` | Next *n* invokes return immediate `retryable` (RST / drop stand-in) |
| `setFatalNext(n)` | Next *n* invokes return `fatal` (no success retry) |
| `setLatencyMs(ms)` | Sleep; if over call budget → `retryable` timeout |

Covered by `tests/test_faults.pys`. TLS + HTTP/2 remain in `tls_term.pys` /
`http2.pys` and the HTTPS/HTTP2 e2e suites.
