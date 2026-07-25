import { describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import type { CurrentUser } from "@rkpr/contracts";
import { DashboardNav } from "./dashboard-nav";
import * as useCurrentUserModule from "@/lib/hooks/use-current-user";

function mockCurrentUser(permissions: string[]) {
  vi.spyOn(useCurrentUserModule, "useCurrentUser").mockReturnValue({
    data: { permissions } as CurrentUser,
    isLoading: false,
  } as ReturnType<typeof useCurrentUserModule.useCurrentUser>);
}

describe("DashboardNav", () => {
  it("shows all twelve approved sections for a user with staff.view", () => {
    mockCurrentUser(["staff.view"]);
    render(<DashboardNav />);
    expect(screen.getByRole("navigation", { name: "Primary" }).querySelectorAll("a")).toHaveLength(
      12,
    );
  });

  it("hides Staff & HR for a user without staff.view", () => {
    mockCurrentUser([]);
    render(<DashboardNav />);
    expect(screen.queryByRole("link", { name: "Staff & HR" })).not.toBeInTheDocument();
    expect(screen.getByRole("navigation", { name: "Primary" }).querySelectorAll("a")).toHaveLength(
      11,
    );
  });
});
