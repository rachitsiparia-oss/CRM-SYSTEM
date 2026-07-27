import { test, expect } from "@playwright/test";

// Phase 8: /inventory and its sub-routes follow the exact same session gate
// as every other module (src/proxy.ts) — no exception was carved out here
// either. Authenticated create/post/reverse/approve workflows (items,
// recipes, suppliers, receipts, adjustments, wastage, transfers, stock
// counts) are not covered here: this project has no Playwright
// authentication helper (no test Supabase session, no storageState fixture)
// in any phase so far — Phase 3, 5, 6, and 7 all stopped at this same
// unauthenticated-redirect boundary for the same reason (see
// health.spec.ts's own comments). Those workflows are fully exercised
// instead by apps/api/tests/test_inventory_api.py and the other
// test_inventory_*.py files (103 tests covering permissions, receipts,
// adjustments, wastage, transfers, stock counts, recipes, and the full
// order-to-inventory reservation/consumption lifecycle) and by the
// component tests alongside this file. See docs/DATABASE_AND_API.md
// section 9.8 for the manual verification checklist covering the
// authenticated workflows this suite cannot exercise.

test("unauthenticated visitors are redirected away from the inventory dashboard", async ({
  page,
}) => {
  await page.goto("/inventory");
  await expect(page).toHaveURL(/\/login(\?.*)?$/);
});

test("unauthenticated visitors are redirected away from inventory items", async ({ page }) => {
  await page.goto("/inventory/items");
  await expect(page).toHaveURL(/\/login(\?.*)?$/);
});

test("unauthenticated visitors are redirected away from an inventory item detail page", async ({
  page,
}) => {
  await page.goto("/inventory/items/00000000-0000-0000-0000-000000000000");
  await expect(page).toHaveURL(/\/login(\?.*)?$/);
});

test("unauthenticated visitors are redirected away from recipes", async ({ page }) => {
  await page.goto("/inventory/recipes");
  await expect(page).toHaveURL(/\/login(\?.*)?$/);
});

test("unauthenticated visitors are redirected away from suppliers", async ({ page }) => {
  await page.goto("/inventory/suppliers");
  await expect(page).toHaveURL(/\/login(\?.*)?$/);
});

test("unauthenticated visitors are redirected away from receipts", async ({ page }) => {
  await page.goto("/inventory/receipts");
  await expect(page).toHaveURL(/\/login(\?.*)?$/);
});

test("unauthenticated visitors are redirected away from adjustments and wastage", async ({
  page,
}) => {
  await page.goto("/inventory/adjustments");
  await expect(page).toHaveURL(/\/login(\?.*)?$/);
});

test("unauthenticated visitors are redirected away from transfers", async ({ page }) => {
  await page.goto("/inventory/transfers");
  await expect(page).toHaveURL(/\/login(\?.*)?$/);
});

test("unauthenticated visitors are redirected away from stock counts", async ({ page }) => {
  await page.goto("/inventory/stock-counts");
  await expect(page).toHaveURL(/\/login(\?.*)?$/);
});

test("unauthenticated visitors are redirected away from the movement ledger", async ({ page }) => {
  await page.goto("/inventory/movements");
  await expect(page).toHaveURL(/\/login(\?.*)?$/);
});
