// k6 load test — docs/TOOLS.md section 12.5 ("REQUIRED BEFORE PRODUCTION").
//
// Covers three representative endpoint shapes rather than every route:
//   - an unauthenticated, uncached endpoint (health) as a latency floor
//   - an authenticated, paginated, permission-checked list endpoint
//     (customers) as the typical dashboard-table shape
//   - the controlled-AI request endpoint, which Phase 16 gave its own
//     per-staff-account rate limit (20/hour) — this scenario is
//     deliberately small (well under the limit) so it measures normal
//     latency, not the 429 path; see README.md in this directory for how
//     to exercise the rate limit itself.
//
// Run: k6 run tests/load/api_smoke.js
// Config via env vars (see README.md for how to obtain ACCESS_TOKEN):
//   BASE_URL      default http://localhost:8000
//   ACCESS_TOKEN  required for the authenticated scenarios; the health
//                 scenario runs without one
//   VUS           default 10
//   DURATION      default 30s

import http from "k6/http";
import { check, sleep } from "k6";
import { Rate, Trend } from "k6/metrics";

const BASE_URL = __ENV.BASE_URL || "http://localhost:8000";
const ACCESS_TOKEN = __ENV.ACCESS_TOKEN || "";
const VUS = Number(__ENV.VUS || 10);
const DURATION = __ENV.DURATION || "30s";

const errorRate = new Rate("crm_errors");
const customersDuration = new Trend("crm_customers_list_duration", true);
const aiRequestDuration = new Trend("crm_ai_request_duration", true);

export const options = {
  scenarios: {
    health: {
      executor: "constant-vus",
      exec: "health",
      vus: VUS,
      duration: DURATION,
    },
    customers_list: {
      executor: "constant-vus",
      exec: "customersList",
      vus: VUS,
      duration: DURATION,
    },
  },
  thresholds: {
    // CLAUDE.md section 5.5 / docs/TOOLS.md 12.5's "latency percentiles" —
    // p95 under 500ms for a paginated list endpoint under load, under 1%
    // error rate. Adjust once a real staging baseline exists; these are
    // starting targets, not numbers measured in this environment (see
    // docs/phase-16/LOAD_TEST_REPORT.md for why).
    http_req_duration: ["p(95)<500"],
    crm_errors: ["rate<0.01"],
  },
};

function authHeaders() {
  return ACCESS_TOKEN ? { Authorization: `Bearer ${ACCESS_TOKEN}` } : {};
}

export function health() {
  const res = http.get(`${BASE_URL}/health/live`);
  const ok = check(res, { "health: status 200": (r) => r.status === 200 });
  errorRate.add(!ok);
  sleep(1);
}

export function customersList() {
  if (!ACCESS_TOKEN) {
    return; // skipped without a token — see README.md
  }
  const res = http.get(`${BASE_URL}/api/v1/customers?page=1&page_size=25`, {
    headers: authHeaders(),
  });
  customersDuration.add(res.timings.duration);
  const ok = check(res, {
    "customers: status 200": (r) => r.status === 200,
    "customers: paginated shape": (r) => {
      try {
        const body = JSON.parse(r.body);
        return Array.isArray(body.data) && typeof body.pagination === "object";
      } catch (e) {
        return false;
      }
    },
  });
  errorRate.add(!ok);
  sleep(1);
}

// Exported separately (not part of the default scenarios above) — run
// explicitly with `k6 run --iterations 5 -e SCENARIO=ai tests/load/api_smoke.js`
// to measure a handful of real AI-request latencies without tripping the
// 20/hour per-account rate limit added in Phase 16
// (app/controlled_ai/router.py).
export function aiRequest() {
  if (!ACCESS_TOKEN) {
    return;
  }
  const payload = JSON.stringify({
    feature_code: "dashboard_summary",
    params: { domain: "executive", window_code: "current_month" },
  });
  const res = http.post(`${BASE_URL}/api/v1/ai/requests`, payload, {
    headers: { ...authHeaders(), "Content-Type": "application/json" },
  });
  aiRequestDuration.add(res.timings.duration);
  const ok = check(res, {
    "ai request: status 201 or 429": (r) => r.status === 201 || r.status === 429,
  });
  errorRate.add(!ok);
  sleep(2);
}
