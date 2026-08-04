/**
 * Scenario A3 (subset): concurrent TLS handshakes + GET /health (FR5).
 *
 *   k6 run -e BASE_URL=https://127.0.0.1:8080 examples/webserver/load/k6/tls_handshake.js
 *
 * Start the server with TLS enabled (uncomment cfg.tlsEnabled in main.pys), from repo root:
 *   python -m transpiler run examples/webserver/main.pys
 *
 * Self-signed certs: examples/webserver/certs/ (insecureSkipTLSVerify below).
 */
import http from "k6/http";
import { check, sleep } from "k6";

export const options = {
  insecureSkipTLSVerify: true,
  scenarios: {
    a3_tls: {
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
  const res = http.get(`${BASE}/health`, { tags: { name: "health_tls" } });
  check(res, { "health 200": (r) => r.status === 200 });
  sleep(0.05);
}
