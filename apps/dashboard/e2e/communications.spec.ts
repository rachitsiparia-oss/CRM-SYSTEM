import { test, expect } from "@playwright/test";

// Phase 10: /communications and its sub-routes (Communication Hub, Tasks,
// Notifications) follow the exact same session gate as every other module
// (src/proxy.ts) — no exception carved out here either. Authenticated
// reply/assign/transition/create workflows are not covered here: this
// project has no Playwright authentication helper (no test Supabase
// session, no storageState fixture) in any phase so far — Phase 3, 5, 6, 7,
// 8, and 9 all stopped at this same unauthenticated-redirect boundary for
// the same reason (see health.spec.ts's own comments). Those workflows are
// fully exercised instead by apps/api/tests/test_communications_api.py,
// test_tasks_api.py, test_notifications_api.py, and the other
// apps/api/tests/test_communications_*.py files.

test("unauthenticated visitors are redirected away from the communication dashboard", async ({
  page,
}) => {
  await page.goto("/communications");
  await expect(page).toHaveURL(/\/login(\?.*)?$/);
});

test("unauthenticated visitors are redirected away from the inbox", async ({ page }) => {
  await page.goto("/communications/inbox");
  await expect(page).toHaveURL(/\/login(\?.*)?$/);
});

test("unauthenticated visitors are redirected away from a conversation detail page", async ({
  page,
}) => {
  await page.goto("/communications/inbox/00000000-0000-0000-0000-000000000000");
  await expect(page).toHaveURL(/\/login(\?.*)?$/);
});

test("unauthenticated visitors are redirected away from templates", async ({ page }) => {
  await page.goto("/communications/templates");
  await expect(page).toHaveURL(/\/login(\?.*)?$/);
});

test("unauthenticated visitors are redirected away from scheduled messages", async ({ page }) => {
  await page.goto("/communications/scheduled");
  await expect(page).toHaveURL(/\/login(\?.*)?$/);
});

test("unauthenticated visitors are redirected away from preferences", async ({ page }) => {
  await page.goto("/communications/preferences");
  await expect(page).toHaveURL(/\/login(\?.*)?$/);
});

test("unauthenticated visitors are redirected away from the suppression list", async ({ page }) => {
  await page.goto("/communications/suppressions");
  await expect(page).toHaveURL(/\/login(\?.*)?$/);
});

test("unauthenticated visitors are redirected away from channels & providers", async ({ page }) => {
  await page.goto("/communications/channels");
  await expect(page).toHaveURL(/\/login(\?.*)?$/);
});

test("unauthenticated visitors are redirected away from call logs", async ({ page }) => {
  await page.goto("/communications/call-logs");
  await expect(page).toHaveURL(/\/login(\?.*)?$/);
});

test("unauthenticated visitors are redirected away from communication analytics", async ({
  page,
}) => {
  await page.goto("/communications/analytics");
  await expect(page).toHaveURL(/\/login(\?.*)?$/);
});

test("unauthenticated visitors are redirected away from tasks", async ({ page }) => {
  await page.goto("/communications/tasks");
  await expect(page).toHaveURL(/\/login(\?.*)?$/);
});

test("unauthenticated visitors are redirected away from notifications", async ({ page }) => {
  await page.goto("/communications/notifications");
  await expect(page).toHaveURL(/\/login(\?.*)?$/);
});
