import { test, expect } from "@playwright/test";

// Phase 14: /reports and its sub-domain route trees (dashboards, library,
// schedules, anomalies, forecasts, AI center) follow the exact same session
// gate as every other module (src/proxy.ts) — no exception carved out here
// either.
// Authenticated report-builder/export/schedule/anomaly-rule/forecast/AI
// workflows are not covered here: this project has no Playwright
// authentication helper (no test Supabase session, no storageState fixture)
// in any phase so far — every prior phase stopped at this same
// unauthenticated-redirect boundary for the same reason (see
// health.spec.ts's own comments). Those workflows are fully exercised
// instead by apps/api/tests/test_phase14_api.py and the other Phase 14
// backend test modules.

const ROUTES = [
  ["the executive dashboard", "/reports"],
  ["the sales dashboard", "/reports/sales"],
  ["the customer analytics dashboard", "/reports/customers"],
  ["the lead analytics dashboard", "/reports/leads"],
  ["the reservation analytics dashboard", "/reports/reservations"],
  ["the inventory & supplier dashboard", "/reports/inventory"],
  ["the marketing analytics dashboard", "/reports/marketing"],
  ["the loyalty analytics dashboard", "/reports/loyalty"],
  ["the feedback analytics dashboard", "/reports/feedback"],
  ["the complaint analytics dashboard", "/reports/complaints"],
  ["the staff & task analytics dashboard", "/reports/staff"],
  ["the report library", "/reports/library"],
  ["scheduled reports", "/reports/schedules"],
  ["the anomaly center", "/reports/anomalies"],
  ["forecasts", "/reports/forecasts"],
  ["the AI center", "/reports/ai"],
] as const;

for (const [description, path] of ROUTES) {
  test(`unauthenticated visitors are redirected away from ${description}`, async ({ page }) => {
    await page.goto(path);
    await expect(page).toHaveURL(/\/login(\?.*)?$/);
  });
}
