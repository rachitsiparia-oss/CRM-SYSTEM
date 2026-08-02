import { test, expect } from "@playwright/test";

// Phase 15: /settings and its sub-route tree (jobs, scheduler, dead-letter,
// integrations, feature flags, operational settings, event log, cache)
// follow the exact same session gate as every other module (src/proxy.ts)
// — no exception carved out here either.
// Authenticated jobs/scheduler/dead-letter/integrations/feature-flag/
// operational-settings/event-log/cache workflows are not covered here: this
// project has no Playwright authentication helper (no test Supabase
// session, no storageState fixture) in any phase so far — every prior phase
// stopped at this same unauthenticated-redirect boundary for the same
// reason (see health.spec.ts's own comments). Those workflows are fully
// exercised instead by apps/api/tests/test_phase15_api_permissions.py and
// the other Phase 15 backend test modules.

const ROUTES = [
  ["the settings overview", "/settings"],
  ["the jobs list", "/settings/jobs"],
  ["the scheduler", "/settings/scheduler"],
  ["the dead letter queue", "/settings/dead-letter"],
  ["integrations", "/settings/integrations"],
  ["feature flags", "/settings/feature-flags"],
  ["operational settings", "/settings/operational"],
  ["the event log", "/settings/event-log"],
  ["cache", "/settings/cache"],
] as const;

for (const [description, path] of ROUTES) {
  test(`unauthenticated visitors are redirected away from ${description}`, async ({ page }) => {
    await page.goto(path);
    await expect(page).toHaveURL(/\/login(\?.*)?$/);
  });
}
