/**
 * Scenario B1 (subset): overload ramp — expect some 503s, not connection drops.
 *
 *   k6 run -e BASE_URL=http://127.0.0.1:8080 examples/webserver/load/k6/overload.js
 */
import http from "k6/http";
import { check, sleep } from "k6";
import { Counter } from "k6/metrics";

const status503 = new Counter("status_503");
const status429 = new Counter("status_429");
const status200 = new Counter("status_200");

export const options = {
  scenarios: {
    b1_overload: {
      executor: "ramping-vus",
      startVUs: 0,
      stages: [
        { duration: "10s", target: 100 },
        { duration: "20s", target: 200 },
        { duration: "10s", target: 0 },
      ],
    },
  },
  thresholds: {
    // Allow shedding; fail only if requests error at transport level heavily.
    http_req_failed: ["rate<0.05"],
  },
};

const BASE = __ENV.BASE_URL || "http://127.0.0.1:8080";

export default function () {
  const res = http.get(`${BASE}/proxy/slow`, {
    headers: { "X-Correlation-Id": `ov-${__VU}-${__ITER}` },
    tags: { name: "proxy_slow" },
    timeout: "2s",
  });
  if (res.status === 503) {
    status503.add(1);
    check(res, {
      "503 has reject reason": (r) =>
        (r.headers["X-Reject-Reason"] || r.headers["x-reject-reason"] || "") !== "",
    });
  } else if (res.status === 429) {
    status429.add(1);
    check(res, {
      "429 inbound shed": (r) =>
        (r.headers["X-Reject-Reason"] || r.headers["x-reject-reason"] || "") ===
        "inbound_full",
    });
  } else if (res.status === 200) {
    status200.add(1);
  }
  check(res, {
    "got response": (r) =>
      r.status === 200 || r.status === 503 || r.status === 502 || r.status === 429,
  });
  sleep(0.01);
}
