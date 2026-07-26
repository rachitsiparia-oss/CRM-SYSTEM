import { test, expect } from "@playwright/test";

// Phase 7: /orders and its sub-routes follow the exact same session gate as
// every other module (src/proxy.ts) — no exception was carved out here
// either. Authenticated create/transition/payment/note workflows are not
// covered here: this project has no Playwright authentication helper (no
// test Supabase session, no storageState fixture) in any phase so far —
// Phase 3, 5, and 6 all stopped at this same unauthenticated-redirect
// boundary for the same reason (see health.spec.ts's own comments). Those
// workflows are fully exercised instead by apps/api/tests/test_orders_api.py
// (30 real HTTP round trips through permission checks, pricing, the state
// machine, payments, and concurrency) and by the component tests alongside
// this file.

test("unauthenticated visitors are redirected away from the orders dashboard", async ({ page }) => {
  await page.goto("/orders");
  await expect(page).toHaveURL(/\/login(\?.*)?$/);
});

test("unauthenticated visitors are redirected away from the orders list", async ({ page }) => {
  await page.goto("/orders/list");
  await expect(page).toHaveURL(/\/login(\?.*)?$/);
});

test("unauthenticated visitors are redirected away from the create-order page", async ({ page }) => {
  await page.goto("/orders/new");
  await expect(page).toHaveURL(/\/login(\?.*)?$/);
});

test("unauthenticated visitors are redirected away from an order detail page", async ({ page }) => {
  await page.goto("/orders/00000000-0000-0000-0000-000000000000");
  await expect(page).toHaveURL(/\/login(\?.*)?$/);
});
