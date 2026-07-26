import { describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import type { CurrentUser } from "@rkpr/contracts";

import { PermissionGate } from "./permission-gate";
import * as useCurrentUserModule from "@/lib/hooks/use-current-user";

function mockUseCurrentUser(overrides: Partial<ReturnType<typeof useCurrentUserModule.useCurrentUser>>) {
  vi.spyOn(useCurrentUserModule, "useCurrentUser").mockReturnValue({
    data: undefined,
    isLoading: false,
    isError: false,
    refetch: vi.fn(),
    ...overrides,
  } as ReturnType<typeof useCurrentUserModule.useCurrentUser>);
}

describe("PermissionGate", () => {
  it("renders children when the user has the required permission", () => {
    mockUseCurrentUser({ data: { permissions: ["customers.view"] } as CurrentUser });
    render(
      <PermissionGate permission="customers.view">
        <div>Protected content</div>
      </PermissionGate>,
    );
    expect(screen.getByText("Protected content")).toBeInTheDocument();
  });

  it("shows a real permission-denied message when the profile loaded but lacks the permission", () => {
    mockUseCurrentUser({ data: { permissions: [] } as unknown as CurrentUser });
    render(
      <PermissionGate permission="customers.view">
        <div>Protected content</div>
      </PermissionGate>,
    );
    expect(screen.getByText("You don't have access to this")).toBeInTheDocument();
    expect(screen.queryByText("Protected content")).not.toBeInTheDocument();
  });

  it("shows a retryable error — not a permission-denied message — when the profile failed to load", () => {
    // Regression test: a transient /auth/me failure (network blip, cold
    // connection) used to render the exact same "you don't have access"
    // copy as a real denial, indistinguishable from actually lacking the
    // permission. It must say something different and offer a retry.
    mockUseCurrentUser({ isError: true });
    render(
      <PermissionGate permission="customers.view">
        <div>Protected content</div>
      </PermissionGate>,
    );
    expect(screen.queryByText("You don't have access to this")).not.toBeInTheDocument();
    expect(screen.getByText(/couldn't verify your access/i)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /retry/i })).toBeInTheDocument();
  });
});
