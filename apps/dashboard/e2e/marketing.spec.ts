import { test, expect } from "@playwright/test";

// Phase 12: /marketing and its nine sub-domain route trees (loyalty,
// segments, offers, campaigns, referrals, achievements, gift-cards,
// customer-credit, commercial-risk) follow the exact same session gate as
// every other module (src/proxy.ts) — no exception carved out here either.
// Authenticated create/transition/redeem/reverse workflows are not covered
// here: this project has no Playwright authentication helper (no test
// Supabase session, no storageState fixture) in any phase so far — every
// prior phase stopped at this same unauthenticated-redirect boundary for
// the same reason (see health.spec.ts's own comments). Those workflows are
// fully exercised instead by apps/api/tests/test_<domain>_api.py.

const ZERO_UUID = "00000000-0000-0000-0000-000000000000";

const ROUTES = [
  ["the marketing dashboard", "/marketing"],
  ["the loyalty dashboard", "/marketing/loyalty"],
  ["a loyalty program detail page", `/marketing/loyalty/programs/${ZERO_UUID}`],
  ["loyalty accounts", "/marketing/loyalty/accounts"],
  ["the segment library", "/marketing/segments"],
  ["a segment detail page", `/marketing/segments/${ZERO_UUID}`],
  ["the offer library", "/marketing/offers"],
  ["an offer detail page", `/marketing/offers/${ZERO_UUID}`],
  ["the campaign library", "/marketing/campaigns"],
  ["a campaign detail page", `/marketing/campaigns/${ZERO_UUID}`],
  ["the referral program library", "/marketing/referrals"],
  ["a referral program detail page", `/marketing/referrals/${ZERO_UUID}`],
  ["referral relationships", "/marketing/referrals/relationships"],
  ["the achievement library", "/marketing/achievements"],
  ["an achievement detail page", `/marketing/achievements/${ZERO_UUID}`],
  ["the gift card library", "/marketing/gift-cards"],
  ["a gift card detail page", `/marketing/gift-cards/${ZERO_UUID}`],
  ["customer credit", "/marketing/customer-credit"],
  ["the commercial risk queue", "/marketing/commercial-risk"],
] as const;

for (const [description, path] of ROUTES) {
  test(`unauthenticated visitors are redirected away from ${description}`, async ({ page }) => {
    await page.goto(path);
    await expect(page).toHaveURL(/\/login(\?.*)?$/);
  });
}
