/**
 * Scenario A2 (subset): HTTP/2 multiplexed streams over TLS (FR2).
 *
 *   python examples/webserver/scripts/gen_dev_certs.py
 *   # enable cfg.tlsEnabled in main.pys
 *   python -m transpiler run examples/webserver/main.pys
 *   k6 run -e BASE_URL=https://127.0.0.1:8080 examples/webserver/load/k6/http2_multiplex.js
 */
import http from "k6/http";
import { check, sleep } from "k6";

export const options = {
  insecureSkipTLSVerify: true,
  scenarios: {
    a2_http2: {
      executor: "ramping-vus",
      startVUs: 0,
      stages: [
        { duration: "10s", target: 20 },
        { duration: "20s", target: 20 },
        { duration: "5s", target: 0 },
      ],
      gracefulRampDown: "5s",
    },
  },
  thresholds: {
    http_req_failed: ["rate<0.05"],
    http_req_duration: ["p(95)<1000"],
  },
};

const BASE = __ENV.BASE_URL || "https://127.0.0.1:8080";

export default function () {
  // k6 uses HTTP/2 when the server negotiates it over TLS.
  const batch = http.batch([
    ["GET", `${BASE}/health`, null, { tags: { name: "health_a" } }],
    ["GET", `${BASE}/health`, null, { tags: { name: "health_b" } }],
  ]);
  check(batch[0], { "health_a 200": (r) => r.status === 200 });
  check(batch[1], { "health_b 200": (r) => r.status === 200 });
  sleep(0.05);
}
