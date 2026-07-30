import { test, expect } from "@playwright/test";

// Phase 11: /knowledge-base and its sub-routes follow the exact same
// session gate as every other module (src/proxy.ts) — no exception carved
// out here either. Authenticated create/review/approve/publish workflows
// are not covered here: this project has no Playwright authentication
// helper (no test Supabase session, no storageState fixture) in any phase
// so far — every prior phase stopped at this same unauthenticated-redirect
// boundary for the same reason (see health.spec.ts's own comments). Those
// workflows are fully exercised instead by apps/api/tests/test_knowledge_api.py.

test("unauthenticated visitors are redirected away from the knowledge base dashboard", async ({
  page,
}) => {
  await page.goto("/knowledge-base");
  await expect(page).toHaveURL(/\/login(\?.*)?$/);
});

test("unauthenticated visitors are redirected away from the article library", async ({ page }) => {
  await page.goto("/knowledge-base/articles");
  await expect(page).toHaveURL(/\/login(\?.*)?$/);
});

test("unauthenticated visitors are redirected away from an article detail page", async ({ page }) => {
  await page.goto("/knowledge-base/articles/00000000-0000-0000-0000-000000000000");
  await expect(page).toHaveURL(/\/login(\?.*)?$/);
});

test("unauthenticated visitors are redirected away from the review queue", async ({ page }) => {
  await page.goto("/knowledge-base/review-queue");
  await expect(page).toHaveURL(/\/login(\?.*)?$/);
});

test("unauthenticated visitors are redirected away from categories", async ({ page }) => {
  await page.goto("/knowledge-base/categories");
  await expect(page).toHaveURL(/\/login(\?.*)?$/);
});

test("unauthenticated visitors are redirected away from knowledge analytics", async ({ page }) => {
  await page.goto("/knowledge-base/analytics");
  await expect(page).toHaveURL(/\/login(\?.*)?$/);
});
