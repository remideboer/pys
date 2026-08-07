# Soak gate (FR1 / testplan H1–H3) — manual, not CI

Teaching k6 scripts under `k6/` stay small by default. Full ≥1k concurrent /
memory-FD soak is a **manual** maturity gate for F-007.

## Why not CI

- 1k VUs needs OS FD / ephemeral-port headroom the GitHub runners do not
  guarantee for this teaching server (4 worker tasks).
- Duration (minutes) would dominate the monorepo test budget.
- Windows and Linux FD limits differ; the gate is environment-specific.

## H1 — 1k VU constant load (5 minutes)

1. Unix: `ulimit -n 65535` (or higher).
2. Optionally lower `inboundMaxPending` / `poolSize` in `src/config.pys` if you
   want visible 429 vs 503 shedding under pressure.
3. Start server from repo root:

```bash
python -m transpiler run examples/webserver/src/main.pys
```

4. Run soak:

```bash
k6 run -e BASE_URL=http://127.0.0.1:8080 examples/webserver/load/k6/soak.js
```

5. During the run, sample metrics and process FDs:

```bash
curl -s http://127.0.0.1:8080/metrics
# Linux example:
# ls /proc/$(pgrep -f main.pys)/fd | wc -l
```

**Pass:** process stays up; `http_req_failed` under threshold; 429
(`inbound_full`) and/or 503 (`queue_full` / `circuit_open`) appear under load
without silent connection drops; FD / RSS do not climb unboundedly across the
window.

## H2 / H3 — optional extensions

- **H2:** extend `soak.js` duration to 30m and watch RSS / FD plateau.
- **H3:** toggle MockDownstream faults (or restart with `setFailNext` test
  harness) every ~30s while soaking; circuit metric should flap without leak.

Record results outside the repo (or a local note); do not require CI green for
these runs.
