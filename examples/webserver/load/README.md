# Load & fault scripts (Increment 3)

Maps to `concurrent-webserver-testplan.md` scenarios A/B/C at teaching scale
(not full 1,000 VU CI by default).

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
| `k6/tls_handshake.js` | A3 subset | Generate certs (`scripts/gen_dev_certs.py`), enable `cfg.tlsEnabled` in `src/main.pys`, then `k6 run -e BASE_URL=https://127.0.0.1:8080 examples/webserver/load/k6/tls_handshake.js` |
| `k6/http2_multiplex.js` | A2 subset | Same TLS setup, then `k6 run -e BASE_URL=https://127.0.0.1:8080 examples/webserver/load/k6/http2_multiplex.js` |

For faster pool saturation, lower `poolSize` in `src/config.pys` before starting `src/main.pys`,
and prefer `/proxy/slow` (300ms mock latency).

## Metrics during load

```bash
curl -s http://127.0.0.1:8080/metrics
```

Look for `pys_reject_queue_full_total` vs `pys_reject_circuit_open_total` (I2).

## Toxiproxy

Optional later. Until then, use `MockDownstream.setFailNext` / `/proxy/slow`
latency for fault-shaped demos. TLS + HTTP/2 are covered by `tls_term.pys`,
`http2.pys`, and the `test_https_e2e` / `test_http2_e2e` suites.
