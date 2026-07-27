import { test, expect } from "@playwright/test";

// Phase 9: /reservations and its sub-routes follow the exact same session
// gate as every other module (src/proxy.ts) — no exception was carved out
// here either. Authenticated create/approve/assign/merge/waitlist workflows
// are not covered here: this project has no Playwright authentication
// helper (no test Supabase session, no storageState fixture) in any phase
// so far — Phase 3, 5, 6, 7, and 8 all stopped at this same
// unauthenticated-redirect boundary for the same reason (see
// health.spec.ts's own comments). Those workflows are fully exercised
// instead by apps/api/tests/test_reservations_api.py and the other
// apps/api/tests/test_reservation_*.py files, and by the component tests
// alongside this file.

test("unauthenticated visitors are redirected away from the reservation dashboard", async ({
  page,
}) => {
  await page.goto("/reservations");
  await expect(page).toHaveURL(/\/login(\?.*)?$/);
});

test("unauthenticated visitors are redirected away from the calendar", async ({ page }) => {
  await page.goto("/reservations/calendar");
  await expect(page).toHaveURL(/\/login(\?.*)?$/);
});

test("unauthenticated visitors are redirected away from the reservations list", async ({ page }) => {
  await page.goto("/reservations/list");
  await expect(page).toHaveURL(/\/login(\?.*)?$/);
});

test("unauthenticated visitors are redirected away from a reservation detail page", async ({
  page,
}) => {
  await page.goto("/reservations/list/00000000-0000-0000-0000-000000000000");
  await expect(page).toHaveURL(/\/login(\?.*)?$/);
});

test("unauthenticated visitors are redirected away from tables & floor", async ({ page }) => {
  await page.goto("/reservations/tables");
  await expect(page).toHaveURL(/\/login(\?.*)?$/);
});

test("unauthenticated visitors are redirected away from a table detail page", async ({ page }) => {
  await page.goto("/reservations/tables/00000000-0000-0000-0000-000000000000");
  await expect(page).toHaveURL(/\/login(\?.*)?$/);
});

test("unauthenticated visitors are redirected away from dining areas", async ({ page }) => {
  await page.goto("/reservations/dining-areas");
  await expect(page).toHaveURL(/\/login(\?.*)?$/);
});

test("unauthenticated visitors are redirected away from the waitlist", async ({ page }) => {
  await page.goto("/reservations/waitlist");
  await expect(page).toHaveURL(/\/login(\?.*)?$/);
});

test("unauthenticated visitors are redirected away from business hours", async ({ page }) => {
  await page.goto("/reservations/business-hours");
  await expect(page).toHaveURL(/\/login(\?.*)?$/);
});

test("unauthenticated visitors are redirected away from reservation settings", async ({ page }) => {
  await page.goto("/reservations/settings");
  await expect(page).toHaveURL(/\/login(\?.*)?$/);
});
