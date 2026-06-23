// k6 ingest-throughput scenario: hammer the webhook-IN endpoint and measure events/s.
// Validates the P1 target (>= 10k events/s on a dev node). Run against the live stack:
//   k6 run --summary-export /dev/stdout k6/ingest_throughput.js
import http from "k6/http";
import { check } from "k6";

const BASE = __ENV.BASE_URL || "http://localhost:8000";
const SOURCE = __ENV.WEBHOOK_SOURCE || "loadtest";
const TOKEN = __ENV.WEBHOOK_TOKEN || "";

export const options = {
  scenarios: {
    ingest: {
      executor: "constant-vus",
      vus: Number(__ENV.VUS || 50),
      duration: __ENV.DURATION || "30s",
    },
  },
};

export default function () {
  const payload = JSON.stringify({
    "@timestamp": new Date().toISOString(),
    "event.action": "loadtest_event",
    "host.name": `vu-${__VU}`,
    message: "k6 ingest throughput sample",
  });
  const res = http.post(`${BASE}/ingest/webhook/${SOURCE}`, payload, {
    headers: { "Content-Type": "application/json", Authorization: `Bearer ${TOKEN}` },
  });
  check(res, { accepted: (r) => r.status === 202 });
}
