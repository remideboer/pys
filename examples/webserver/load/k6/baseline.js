/**
 * Scenario A1 (subset): ramp concurrent HTTP/1.1 keep-alive GETs against a healthy server.
 *
 *   k6 run -e BASE_URL=http://127.0.0.1:8080 examples/webserver/load/k6/baseline.js
 *
 * Start the server first:
 *   python -m transpiler run examples/webserver/src/main.pys
 */
import http from "k6/http";
import { check, sleep } from "k6";

export const options = {
  scenarios: {
    a1_baseline: {
      executor: "ramping-vus",
      startVUs: 0,
      stages: [
        { duration: "15s", target: 50 },
        { duration: "30s", target: 50 },
        { duration: "10s", target: 0 },
      ],
      gracefulRampDown: "5s",
    },
  },
  thresholds: {
    http_req_failed: ["rate<0.01"],
    http_req_duration: ["p(95)<500"],
  },
};

const BASE = __ENV.BASE_URL || "http://127.0.0.1:8080";

export default function () {
  const health = http.get(`${BASE}/health`, { tags: { name: "health" } });
  check(health, { "health 200": (r) => r.status === 200 });

  const proxy = http.get(`${BASE}/proxy/data`, {
    headers: { "X-Correlation-Id": `k6-${__VU}-${__ITER}` },
    tags: { name: "proxy_data" },
  });
  check(proxy, { "proxy 200": (r) => r.status === 200 });

  sleep(0.05);
}
