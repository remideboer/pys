/**
 * Scenario H1 subset: sustained ~1k VU soak (manual gate — not CI).
 *
 * Prerequisites: raise FDs on Unix; see load/SOAK.md.
 *
 *   k6 run -e BASE_URL=http://127.0.0.1:8080 examples/webserver/load/k6/soak.js
 */
import http from "k6/http";
import { check, sleep } from "k6";
import { Counter } from "k6/metrics";

const status200 = new Counter("status_200");
const status429 = new Counter("status_429");
const status503 = new Counter("status_503");

export const options = {
  scenarios: {
    h1_soak: {
      executor: "constant-vus",
      vus: 1000,
      duration: "5m",
    },
  },
  thresholds: {
    // Transport failures should stay rare; shedding via 429/503 is expected.
    http_req_failed: ["rate<0.10"],
  },
};

const BASE = __ENV.BASE_URL || "http://127.0.0.1:8080";

export default function () {
  const path = __ITER % 5 === 0 ? "/proxy/slow" : "/health";
  const res = http.get(`${BASE}${path}`, {
    headers: { "X-Correlation-Id": `soak-${__VU}-${__ITER}` },
    timeout: "3s",
  });
  if (res.status === 200) {
    status200.add(1);
  } else if (res.status === 429) {
    status429.add(1);
  } else if (res.status === 503) {
    status503.add(1);
  }
  check(res, {
    "got response": (r) =>
      r.status === 200 || r.status === 429 || r.status === 503 || r.status === 502,
  });
  sleep(0.05);
}
