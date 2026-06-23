// k6 query-latency scenario: measure GET /events p95 latency.
// Validates the P1 target (24h log query p95 < 2000ms). Run against the live stack:
//   k6 run --summary-export /dev/stdout k6/query_latency.js
import http from "k6/http";
import { check } from "k6";

const BASE = __ENV.BASE_URL || "http://localhost:8000";

export const options = {
  scenarios: {
    query: {
      executor: "constant-vus",
      vus: Number(__ENV.VUS || 10),
      duration: __ENV.DURATION || "30s",
    },
  },
  thresholds: {
    http_req_duration: ["p(95)<2000"],
  },
};

export default function () {
  const res = http.get(`${BASE}/events?limit=100`);
  check(res, { ok: (r) => r.status === 200 });
}
