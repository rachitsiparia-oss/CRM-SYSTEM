import { test, expect } from "@playwright/test";

// Phase 6: /menu and its sub-routes follow the exact same session gate as
// every other module (src/proxy.ts) — no exception was carved out when the
// placeholder was replaced. Authenticated create/edit/duplicate/archive/
// variant/modifier workflows are not covered here: this project has no
// Playwright authentication helper (no test Supabase session, no
// storageState fixture) in any phase so far — Phase 3 and Phase 5 both
// stopped at this same unauthenticated-redirect boundary for the same
// reason (see health.spec.ts's own comments). Those workflows are fully
// exercised instead by apps/api/tests/test_menu_api.py (24 real HTTP round
// trips through permission checks, archive/restore, duplication, variants,
// and modifiers) and by the component tests alongside this file.

test("unauthenticated visitors are redirected away from menu products", async ({ page }) => {
  await page.goto("/menu");
  await expect(page).toHaveURL(/\/login(\?.*)?$/);
});

test("unauthenticated visitors are redirected away from menu categories", async ({ page }) => {
  await page.goto("/menu/categories");
  await expect(page).toHaveURL(/\/login(\?.*)?$/);
});

test("unauthenticated visitors are redirected away from modifier groups", async ({ page }) => {
  await page.goto("/menu/modifier-groups");
  await expect(page).toHaveURL(/\/login(\?.*)?$/);
});

test("unauthenticated visitors are redirected away from a product detail page", async ({
  page,
}) => {
  await page.goto("/menu/products/00000000-0000-0000-0000-000000000000");
  await expect(page).toHaveURL(/\/login(\?.*)?$/);
});
