import type { ReactElement } from "react";
import { describe, expect, it, vi, beforeEach } from "vitest";
import { render, screen } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import type { CurrentUser } from "@rkpr/contracts";
import { Sidebar } from "./sidebar";
import * as useCurrentUserModule from "@/lib/hooks/use-current-user";

vi.mock("next/navigation", () => ({
  usePathname: () => "/",
  // UserMenu (now rendered in the Sidebar footer, Phase 17.5) calls
  // useRouter() for its sign-out redirect — unused by these tests
  // otherwise, but must exist or rendering UserMenu throws.
  useRouter: () => ({ replace: vi.fn(), refresh: vi.fn(), push: vi.fn() }),
}));

// UserMenu also calls useQueryClient() (query-cache eviction on sign-out) —
// needs a real QueryClient in the tree or that hook throws at render time.
function renderSidebar(ui: ReactElement = <Sidebar />) {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(<QueryClientProvider client={queryClient}>{ui}</QueryClientProvider>);
}

function mockCurrentUser(permissions: string[]) {
  // The sidebar footer now renders UserMenu (Phase 17.5), which also reads
  // useCurrentUser() and needs display_name/email/roles beyond just
  // permissions — a bare { permissions } object crashes it at render time.
  vi.spyOn(useCurrentUserModule, "useCurrentUser").mockReturnValue({
    data: {
      display_name: "Test User",
      email: "test.user@example.com",
      roles: [{ id: "role-1", code: "test_role", name: "Test Role" }],
      permissions,
    } as CurrentUser,
    isLoading: false,
  } as ReturnType<typeof useCurrentUserModule.useCurrentUser>);
}

describe("Sidebar", () => {
  beforeEach(() => {
    window.localStorage.clear();
  });

  it("shows ten of the twelve approved sections for a user with staff.view, menu.view, orders.view, reservations.view, communications.view, knowledge.view, and loyalty.view", () => {
    mockCurrentUser([
      "staff.view",
      "menu.view",
      "orders.view",
      "reservations.view",
      "communications.view",
      "knowledge.view",
      "loyalty.view",
    ]);
    renderSidebar();
    const nav = screen.getByRole("navigation", { name: "Primary" });
    // Staff & HR's, Menu's, Orders', Reservations', Communication Hub's,
    // Knowledge Base's, and Marketing's children start collapsed (current
    // route is "/", not one of their routes), so only the top-level links
    // render. Reports, Analytics & AI Center (Phase 14) requires an
    // analytics/reports/anomalies/forecasts/ai.analytics permission, and
    // Integrations, Security & Settings (Phase 15) requires a
    // jobs/queues/scheduler/dead_letter/settings.integrations/settings/
    // event_log/cache permission — this user has none of either, so both
    // are hidden — ten of the twelve sections show.
    expect(nav.querySelectorAll("a")).toHaveLength(10);
  });

  it("hides Staff & HR for a user without staff.view or staff.leave.request", () => {
    // The other gates are granted so this test isolates the Staff & HR
    // gate rather than incidentally also exercising the other gates.
    mockCurrentUser([
      "menu.view",
      "orders.view",
      "reservations.view",
      "communications.view",
      "knowledge.view",
      "loyalty.view",
    ]);
    renderSidebar();
    expect(screen.queryByRole("link", { name: /Staff & HR/ })).not.toBeInTheDocument();
    const nav = screen.getByRole("navigation", { name: "Primary" });
    expect(nav.querySelectorAll("a")).toHaveLength(9);
  });

  it("hides Menu, Products & Inventory for a user without menu.view", () => {
    mockCurrentUser([
      "staff.view",
      "orders.view",
      "reservations.view",
      "communications.view",
      "knowledge.view",
      "loyalty.view",
    ]);
    renderSidebar();
    expect(
      screen.queryByRole("link", { name: /Menu, Products & Inventory/ }),
    ).not.toBeInTheDocument();
    const nav = screen.getByRole("navigation", { name: "Primary" });
    expect(nav.querySelectorAll("a")).toHaveLength(9);
  });

  it("hides Orders & Restaurant Operations for a user without orders.view", () => {
    mockCurrentUser([
      "staff.view",
      "menu.view",
      "reservations.view",
      "communications.view",
      "knowledge.view",
      "loyalty.view",
    ]);
    renderSidebar();
    expect(
      screen.queryByRole("link", { name: /Orders & Restaurant Operations/ }),
    ).not.toBeInTheDocument();
    const nav = screen.getByRole("navigation", { name: "Primary" });
    expect(nav.querySelectorAll("a")).toHaveLength(9);
  });

  it("hides Reservations & Calendar for a user without reservations.view", () => {
    mockCurrentUser([
      "staff.view",
      "menu.view",
      "orders.view",
      "communications.view",
      "knowledge.view",
      "loyalty.view",
    ]);
    renderSidebar();
    expect(
      screen.queryByRole("link", { name: /Reservations & Calendar/ }),
    ).not.toBeInTheDocument();
    const nav = screen.getByRole("navigation", { name: "Primary" });
    expect(nav.querySelectorAll("a")).toHaveLength(9);
  });

  it("hides Communication Hub for a user without communications.view", () => {
    mockCurrentUser([
      "staff.view",
      "menu.view",
      "orders.view",
      "reservations.view",
      "knowledge.view",
      "loyalty.view",
    ]);
    renderSidebar();
    expect(screen.queryByRole("link", { name: /Communication Hub/ })).not.toBeInTheDocument();
    const nav = screen.getByRole("navigation", { name: "Primary" });
    expect(nav.querySelectorAll("a")).toHaveLength(9);
  });

  it("hides Lightweight Knowledge Base for a user without knowledge.view", () => {
    mockCurrentUser([
      "staff.view",
      "menu.view",
      "orders.view",
      "reservations.view",
      "communications.view",
      "loyalty.view",
    ]);
    renderSidebar();
    expect(
      screen.queryByRole("link", { name: /Lightweight Knowledge Base/ }),
    ).not.toBeInTheDocument();
    const nav = screen.getByRole("navigation", { name: "Primary" });
    expect(nav.querySelectorAll("a")).toHaveLength(9);
  });

  it("hides Marketing, Loyalty & Feedback for a user without any of its twelve domain view permissions", () => {
    mockCurrentUser([
      "staff.view",
      "menu.view",
      "orders.view",
      "reservations.view",
      "communications.view",
      "knowledge.view",
    ]);
    renderSidebar();
    expect(
      screen.queryByRole("link", { name: /Marketing, Loyalty & Feedback/ }),
    ).not.toBeInTheDocument();
    const nav = screen.getByRole("navigation", { name: "Primary" });
    expect(nav.querySelectorAll("a")).toHaveLength(9);
  });

  it("shows Reports, Analytics & AI Center for a user with reports.view", () => {
    mockCurrentUser([
      "staff.view",
      "menu.view",
      "orders.view",
      "reservations.view",
      "communications.view",
      "knowledge.view",
      "loyalty.view",
      "reports.view",
    ]);
    renderSidebar();
    expect(
      screen.getByRole("link", { name: /Reports, Analytics & AI Center/ }),
    ).toBeInTheDocument();
    const nav = screen.getByRole("navigation", { name: "Primary" });
    expect(nav.querySelectorAll("a")).toHaveLength(11);
  });

  it("shows Integrations, Security & Settings for a user with jobs.view", () => {
    mockCurrentUser([
      "staff.view",
      "menu.view",
      "orders.view",
      "reservations.view",
      "communications.view",
      "knowledge.view",
      "loyalty.view",
      "jobs.view",
    ]);
    renderSidebar();
    expect(
      screen.getByRole("link", { name: /Integrations, Security & Settings/ }),
    ).toBeInTheDocument();
    const nav = screen.getByRole("navigation", { name: "Primary" });
    expect(nav.querySelectorAll("a")).toHaveLength(11);
  });

  it("marks the current route as active via aria-current", () => {
    mockCurrentUser(["staff.view"]);
    renderSidebar();
    const dashboardLink = screen.getByRole("link", { name: "Dashboard" });
    expect(dashboardLink).toHaveAttribute("aria-current", "page");
  });
});
