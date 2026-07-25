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

  it("shows all twelve approved sections for a user with staff.view", () => {
    mockCurrentUser(["staff.view"]);
    render(<Sidebar />);
    const nav = screen.getByRole("navigation", { name: "Primary" });
    // Staff & HR's children start collapsed (current route is "/", not a
    // staff route), so only the twelve top-level links render.
    expect(nav.querySelectorAll("a")).toHaveLength(12);
  });

  it("hides Staff & HR for a user without staff.view", () => {
    mockCurrentUser([]);
    render(<Sidebar />);
    expect(screen.queryByRole("link", { name: /Staff & HR/ })).not.toBeInTheDocument();
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
