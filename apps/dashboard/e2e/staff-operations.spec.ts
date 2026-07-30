import { test, expect } from "@playwright/test";

// Phase 11: the new Staff Operations sub-routes under /staff follow the
// exact same session gate as every other module (src/proxy.ts) — no
// exception carved out here either. Authenticated onboarding/roster/
// leave-decision/training/review workflows are not covered here: this
// project has no Playwright authentication helper (no test Supabase
// session, no storageState fixture) in any phase so far — every prior
// phase stopped at this same unauthenticated-redirect boundary for the
// same reason (see health.spec.ts's own comments). Those workflows are
// fully exercised instead by apps/api/tests/test_staff_operations_api.py.

test("unauthenticated visitors are redirected away from the staff dashboard", async ({ page }) => {
  await page.goto("/staff/dashboard");
  await expect(page).toHaveURL(/\/login(\?.*)?$/);
});

test("unauthenticated visitors are redirected away from my work", async ({ page }) => {
  await page.goto("/staff/my-work");
  await expect(page).toHaveURL(/\/login(\?.*)?$/);
});

test("unauthenticated visitors are redirected away from onboarding & offboarding", async ({ page }) => {
  await page.goto("/staff/transitions");
  await expect(page).toHaveURL(/\/login(\?.*)?$/);
});

test("unauthenticated visitors are redirected away from shifts & roster", async ({ page }) => {
  await page.goto("/staff/roster");
  await expect(page).toHaveURL(/\/login(\?.*)?$/);
});

test("unauthenticated visitors are redirected away from attendance", async ({ page }) => {
  await page.goto("/staff/attendance");
  await expect(page).toHaveURL(/\/login(\?.*)?$/);
});

test("unauthenticated visitors are redirected away from leave", async ({ page }) => {
  await page.goto("/staff/leave");
  await expect(page).toHaveURL(/\/login(\?.*)?$/);
});

test("unauthenticated visitors are redirected away from training", async ({ page }) => {
  await page.goto("/staff/training");
  await expect(page).toHaveURL(/\/login(\?.*)?$/);
});

test("unauthenticated visitors are redirected away from certifications & skills", async ({ page }) => {
  await page.goto("/staff/certifications");
  await expect(page).toHaveURL(/\/login(\?.*)?$/);
});

test("unauthenticated visitors are redirected away from performance reviews", async ({ page }) => {
  await page.goto("/staff/reviews");
  await expect(page).toHaveURL(/\/login(\?.*)?$/);
});

test("unauthenticated visitors are redirected away from staff analytics", async ({ page }) => {
  await page.goto("/staff/analytics");
  await expect(page).toHaveURL(/\/login(\?.*)?$/);
});

test("unauthenticated visitors are redirected away from a staff detail page", async ({ page }) => {
  await page.goto("/staff/00000000-0000-0000-0000-000000000000");
  await expect(page).toHaveURL(/\/login(\?.*)?$/);
});
