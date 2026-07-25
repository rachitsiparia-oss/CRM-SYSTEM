import { test, expect } from "@playwright/test";

test("health page confirms the dashboard is serving requests", async ({
  page,
}) => {
  await page.goto("/health");
  await expect(page.getByRole("heading", { name: "Dashboard: OK" })).toBeVisible();
});

test("primary navigation lists all twelve approved sections", async ({
  page,
}) => {
  await page.goto("/");
  const nav = page.getByRole("navigation", { name: "Primary" });
  await expect(nav.getByRole("link")).toHaveCount(12);
});
