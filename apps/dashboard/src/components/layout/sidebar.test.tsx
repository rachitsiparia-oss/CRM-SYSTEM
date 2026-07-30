import { describe, expect, it, vi, beforeEach } from "vitest";
import { render, screen } from "@testing-library/react";
import type { CurrentUser } from "@rkpr/contracts";
import { Sidebar } from "./sidebar";
import * as useCurrentUserModule from "@/lib/hooks/use-current-user";

vi.mock("next/navigation", () => ({
  usePathname: () => "/",
}));

function mockCurrentUser(permissions: string[]) {
  vi.spyOn(useCurrentUserModule, "useCurrentUser").mockReturnValue({
    data: { permissions } as CurrentUser,
    isLoading: false,
  } as ReturnType<typeof useCurrentUserModule.useCurrentUser>);
}

describe("Sidebar", () => {
  beforeEach(() => {
    window.localStorage.clear();
  });

  it("shows all twelve approved sections for a user with staff.view, menu.view, orders.view, reservations.view, communications.view, and knowledge.view", () => {
    mockCurrentUser([
      "staff.view",
      "menu.view",
      "orders.view",
      "reservations.view",
      "communications.view",
      "knowledge.view",
    ]);
    render(<Sidebar />);
    const nav = screen.getByRole("navigation", { name: "Primary" });
    // Staff & HR's, Menu's, Orders', Reservations', Communication Hub's, and
    // Knowledge Base's children start collapsed (current route is "/", not
    // one of their routes), so only the twelve top-level links render.
    expect(nav.querySelectorAll("a")).toHaveLength(12);
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
    ]);
    render(<Sidebar />);
    expect(screen.queryByRole("link", { name: /Staff & HR/ })).not.toBeInTheDocument();
    const nav = screen.getByRole("navigation", { name: "Primary" });
    expect(nav.querySelectorAll("a")).toHaveLength(11);
  });

  it("hides Menu, Products & Inventory for a user without menu.view", () => {
    mockCurrentUser([
      "staff.view",
      "orders.view",
      "reservations.view",
      "communications.view",
      "knowledge.view",
    ]);
    render(<Sidebar />);
    expect(
      screen.queryByRole("link", { name: /Menu, Products & Inventory/ }),
    ).not.toBeInTheDocument();
    const nav = screen.getByRole("navigation", { name: "Primary" });
    expect(nav.querySelectorAll("a")).toHaveLength(11);
  });

  it("hides Orders & Restaurant Operations for a user without orders.view", () => {
    mockCurrentUser([
      "staff.view",
      "menu.view",
      "reservations.view",
      "communications.view",
      "knowledge.view",
    ]);
    render(<Sidebar />);
    expect(
      screen.queryByRole("link", { name: /Orders & Restaurant Operations/ }),
    ).not.toBeInTheDocument();
    const nav = screen.getByRole("navigation", { name: "Primary" });
    expect(nav.querySelectorAll("a")).toHaveLength(11);
  });

  it("hides Reservations & Calendar for a user without reservations.view", () => {
    mockCurrentUser(["staff.view", "menu.view", "orders.view", "communications.view", "knowledge.view"]);
    render(<Sidebar />);
    expect(
      screen.queryByRole("link", { name: /Reservations & Calendar/ }),
    ).not.toBeInTheDocument();
    const nav = screen.getByRole("navigation", { name: "Primary" });
    expect(nav.querySelectorAll("a")).toHaveLength(11);
  });

  it("hides Communication Hub for a user without communications.view", () => {
    mockCurrentUser(["staff.view", "menu.view", "orders.view", "reservations.view", "knowledge.view"]);
    render(<Sidebar />);
    expect(screen.queryByRole("link", { name: /Communication Hub/ })).not.toBeInTheDocument();
    const nav = screen.getByRole("navigation", { name: "Primary" });
    expect(nav.querySelectorAll("a")).toHaveLength(11);
  });

  it("hides Lightweight Knowledge Base for a user without knowledge.view", () => {
    mockCurrentUser(["staff.view", "menu.view", "orders.view", "reservations.view", "communications.view"]);
    render(<Sidebar />);
    expect(
      screen.queryByRole("link", { name: /Lightweight Knowledge Base/ }),
    ).not.toBeInTheDocument();
    const nav = screen.getByRole("navigation", { name: "Primary" });
    expect(nav.querySelectorAll("a")).toHaveLength(11);
  });

  it("marks the current route as active via aria-current", () => {
    mockCurrentUser(["staff.view"]);
    render(<Sidebar />);
    const dashboardLink = screen.getByRole("link", { name: "Dashboard" });
    expect(dashboardLink).toHaveAttribute("aria-current", "page");
  });
});
