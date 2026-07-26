import { test, expect } from "@playwright/test";

test("health page confirms the dashboard is serving requests", async ({
  page,
}) => {
  await page.goto("/health");
  await expect(page.getByRole("heading", { name: "Dashboard: OK" })).toBeVisible();
});

test("unauthenticated visitors are redirected to sign in", async ({ page }) => {
  // Phase 3: every route except the public auth pages requires a session —
  // src/proxy.ts. The full twelve-section nav is covered by
  // sidebar.test.tsx instead, since rendering it now requires an
  // authenticated current-user response the e2e environment doesn't have.
  await page.goto("/");
  await expect(page).toHaveURL(/\/login(\?.*)?$/);
});

test("unauthenticated visitors are redirected away from the customer directory", async ({
  page,
}) => {
  // Phase 5: /customers is gated by the same session check as every other
  // module — no exception was carved out when the CRM pages replaced the
  // placeholder.
  await page.goto("/customers");
  await expect(page).toHaveURL(/\/login(\?.*)?$/);
});

test("unauthenticated visitors are redirected away from the lead pipeline", async ({ page }) => {
  await page.goto("/leads");
  await expect(page).toHaveURL(/\/login(\?.*)?$/);
});

test("the login page renders the sign-in form", async ({ page }) => {
  await page.goto("/login");
  await expect(page.getByLabel("Email")).toBeVisible();
  await expect(page.getByLabel("Password")).toBeVisible();
  await expect(page.getByRole("button", { name: "Sign in" })).toBeVisible();
});
