/**
 * Scenario C1 (subset): pool pressure via /proxy/slow — watch 503 queue_full and /metrics.
 *
 *   k6 run -e BASE_URL=http://127.0.0.1:8080 examples/webserver/load/k6/pool_exhaust.js
 *
 * Tip: lower poolSize in config.pys (e.g. 2) before starting main.pys to saturate faster.
 */
import http from "k6/http";
import { check, sleep } from "k6";
import { Counter } from "k6/metrics";

const queueFull = new Counter("reject_queue_full");
const circuitOpen = new Counter("reject_circuit_open");

export const options = {
  scenarios: {
    c1_pool: {
      executor: "constant-vus",
      vus: 40,
      duration: "30s",
    },
  },
  thresholds: {
    http_req_failed: ["rate<0.1"],
  },
};

const BASE = __ENV.BASE_URL || "http://127.0.0.1:8080";

export default function () {
  const res = http.get(`${BASE}/proxy/slow`, {
    headers: { "X-Correlation-Id": `pool-${__VU}-${__ITER}` },
    tags: { name: "proxy_slow" },
    timeout: "3s",
  });
  const reason = (res.headers["X-Reject-Reason"] || res.headers["x-reject-reason"] || "").toLowerCase();
  if (reason === "queue_full") {
    queueFull.add(1);
  }
  if (reason === "circuit_open") {
    circuitOpen.add(1);
  }
  check(res, {
    "status ok or shed": (r) => r.status === 200 || r.status === 503 || r.status === 502,
  });
  if (__ITER % 20 === 0) {
    const m = http.get(`${BASE}/metrics`, { tags: { name: "metrics" } });
    check(m, { "metrics 200": (r) => r.status === 200 });
  }
  sleep(0.02);
}
