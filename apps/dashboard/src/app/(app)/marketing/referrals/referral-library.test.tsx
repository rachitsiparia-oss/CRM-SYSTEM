import type { ReactElement } from "react";
import { describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import type { CurrentUser, ReferralProgram } from "@rkpr/contracts";

import { ReferralLibrary } from "./referral-library";
import * as useCurrentUserModule from "@/lib/hooks/use-current-user";
import * as useReferralsModule from "@/lib/hooks/use-referrals";

vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: vi.fn() }),
  usePathname: () => "/marketing/referrals",
  useSearchParams: () => new URLSearchParams(),
}));

function renderWithQueryClient(ui: ReactElement) {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(<QueryClientProvider client={queryClient}>{ui}</QueryClientProvider>);
}

function makeProgram(overrides: Partial<ReferralProgram>): ReferralProgram {
  return {
    id: "11111111-1111-1111-1111-111111111111",
    code: "FRIENDS10",
    name: "Friends & Family",
    status: "active",
    starts_at: null,
    ends_at: null,
    referrer_eligibility_note: null,
    referee_eligibility_note: null,
    qualifying_order_minimum_minor: null,
    reward_ledger: "loyalty_points",
    referrer_reward_amount: 100,
    referee_reward_amount: 50,
    max_active_codes_per_referrer: 5,
    max_rewarded_referrals_per_window: null,
    window_days: null,
    reward_hold_days: 7,
    version: 1,
    is_active_default: true,
    created_at: "2026-07-30T10:00:00Z",
    updated_at: "2026-07-30T10:00:00Z",
    ...overrides,
  };
}

function mockCurrentUser(permissions: string[]) {
  vi.spyOn(useCurrentUserModule, "useCurrentUser").mockReturnValue({
    data: { permissions } as CurrentUser,
    isLoading: false,
  } as ReturnType<typeof useCurrentUserModule.useCurrentUser>);
}

function mockPrograms(programs: ReferralProgram[]) {
  vi.spyOn(useReferralsModule, "useReferralPrograms").mockReturnValue({
    data: programs,
    isLoading: false,
    isError: false,
    refetch: vi.fn(),
  } as unknown as ReturnType<typeof useReferralsModule.useReferralPrograms>);
}

const TWO_PROGRAMS = [
  makeProgram({ id: "1", name: "Friends & Family", code: "FRIENDS10" }),
  makeProgram({ id: "2", name: "Winter Referral", code: "WINTER25", status: "draft" }),
];

describe("ReferralLibrary", () => {
  it("renders a real (non-empty) referral program list without throwing", () => {
    mockCurrentUser(["referrals.view"]);
    mockPrograms(TWO_PROGRAMS);
    renderWithQueryClient(<ReferralLibrary />);
    expect(screen.getByText("Friends & Family")).toBeInTheDocument();
    expect(screen.getByText("Winter Referral")).toBeInTheDocument();
  });

  it("shows the create button for a user with referrals.manage", () => {
    mockCurrentUser(["referrals.view", "referrals.manage"]);
    mockPrograms([]);
    renderWithQueryClient(<ReferralLibrary />);
    expect(screen.getByRole("button", { name: /new program/i })).toBeInTheDocument();
  });

  it("hides the create button for a user without referrals.manage", () => {
    mockCurrentUser(["referrals.view"]);
    mockPrograms([]);
    renderWithQueryClient(<ReferralLibrary />);
    expect(screen.queryByRole("button", { name: /new program/i })).not.toBeInTheDocument();
  });
});
