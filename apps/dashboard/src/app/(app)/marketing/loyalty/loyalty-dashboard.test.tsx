import type { ReactElement } from "react";
import { describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import type { CurrentUser, LoyaltyAnalytics, LoyaltyProgram } from "@rkpr/contracts";

import { LoyaltyDashboard } from "./loyalty-dashboard";
import * as useCurrentUserModule from "@/lib/hooks/use-current-user";
import * as useLoyaltyModule from "@/lib/hooks/use-loyalty";

vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: vi.fn() }),
  usePathname: () => "/marketing/loyalty",
  useSearchParams: () => new URLSearchParams(),
}));

function renderWithQueryClient(ui: ReactElement) {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(<QueryClientProvider client={queryClient}>{ui}</QueryClientProvider>);
}

function makeProgram(overrides: Partial<LoyaltyProgram>): LoyaltyProgram {
  return {
    id: "11111111-1111-1111-1111-111111111111",
    code: "RKPR_REWARDS",
    name: "RKPR Rewards",
    points_display_name: "points",
    description: null,
    status: "active",
    is_default: true,
    points_per_currency_unit: 1,
    currency_unit_minor: 100,
    redemption_points_per_unit: 100,
    redemption_value_minor: 100,
    minimum_redemption_points: 100,
    max_redemption_percent: null,
    points_expiry_days: null,
    terms_summary: null,
    created_at: "2026-07-30T10:00:00Z",
    updated_at: "2026-07-30T10:00:00Z",
    ...overrides,
  };
}

const TWO_PROGRAMS: LoyaltyProgram[] = [
  makeProgram({ id: "1", name: "RKPR Rewards" }),
  makeProgram({ id: "2", code: "STUDENT_PLAN", name: "Student Plan", is_default: false, status: "draft" }),
];

const ANALYTICS: LoyaltyAnalytics = {
  active_members: 42,
  points_issued_30d: 1000,
  points_redeemed_30d: 400,
  points_expired_30d: 0,
  outstanding_points_liability_minor: 50000,
  redemption_rate_pct: "40.0",
  tier_distribution: [],
};

function mockCurrentUser(permissions: string[]) {
  vi.spyOn(useCurrentUserModule, "useCurrentUser").mockReturnValue({
    data: { permissions } as CurrentUser,
    isLoading: false,
  } as ReturnType<typeof useCurrentUserModule.useCurrentUser>);
}

function mockPrograms(programs: LoyaltyProgram[]) {
  vi.spyOn(useLoyaltyModule, "useLoyaltyPrograms").mockReturnValue({
    data: programs,
    isLoading: false,
    isError: false,
    refetch: vi.fn(),
  } as unknown as ReturnType<typeof useLoyaltyModule.useLoyaltyPrograms>);
}

function mockAnalytics() {
  vi.spyOn(useLoyaltyModule, "useLoyaltyAnalytics").mockReturnValue({
    data: ANALYTICS,
    isLoading: false,
  } as unknown as ReturnType<typeof useLoyaltyModule.useLoyaltyAnalytics>);
}

describe("LoyaltyDashboard", () => {
  it("renders a real (non-empty) program list without throwing", () => {
    mockCurrentUser(["loyalty.view"]);
    mockPrograms(TWO_PROGRAMS);
    mockAnalytics();
    renderWithQueryClient(<LoyaltyDashboard />);
    expect(screen.getByText("RKPR Rewards")).toBeInTheDocument();
    expect(screen.getByText("Student Plan")).toBeInTheDocument();
  });

  it("shows the create button for a user with loyalty.manage", () => {
    mockCurrentUser(["loyalty.view", "loyalty.manage"]);
    mockPrograms([]);
    mockAnalytics();
    renderWithQueryClient(<LoyaltyDashboard />);
    expect(screen.getByRole("button", { name: /new program/i })).toBeInTheDocument();
  });

  it("hides the create button for a user without loyalty.manage", () => {
    mockCurrentUser(["loyalty.view"]);
    mockPrograms([]);
    mockAnalytics();
    renderWithQueryClient(<LoyaltyDashboard />);
    expect(screen.queryByRole("button", { name: /new program/i })).not.toBeInTheDocument();
  });
});
