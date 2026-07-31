import type { ReactElement } from "react";
import { describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import type { CurrentUser, PaginatedResponse, ReferralRelationship } from "@rkpr/contracts";

import { RelationshipsView } from "./relationships-view";
import * as useCurrentUserModule from "@/lib/hooks/use-current-user";
import * as useReferralsModule from "@/lib/hooks/use-referrals";

vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: vi.fn() }),
  usePathname: () => "/marketing/referrals/relationships",
  useSearchParams: () => new URLSearchParams(),
}));

function renderWithQueryClient(ui: ReactElement) {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(<QueryClientProvider client={queryClient}>{ui}</QueryClientProvider>);
}

function makeRelationship(overrides: Partial<ReferralRelationship>): ReferralRelationship {
  return {
    id: "11111111-1111-1111-1111-111111111111",
    program_id: "program-1",
    code_id: "code-1",
    referrer_customer_id: "referrer-1",
    referred_identity_key: "+919999999999",
    referred_customer_id: null,
    attributed_at: "2026-07-30T10:00:00Z",
    qualifying_order_id: null,
    status: "attributed",
    referrer_reward_ledger_entry_id: null,
    referee_reward_ledger_entry_id: null,
    rejection_reason: null,
    qualified_at: null,
    rewarded_at: null,
    created_at: "2026-07-30T10:00:00Z",
    ...overrides,
  };
}

function mockCurrentUser(permissions: string[]) {
  vi.spyOn(useCurrentUserModule, "useCurrentUser").mockReturnValue({
    data: { permissions } as CurrentUser,
    isLoading: false,
  } as ReturnType<typeof useCurrentUserModule.useCurrentUser>);
}

function mockRelationships(list: PaginatedResponse<ReferralRelationship>) {
  vi.spyOn(useReferralsModule, "useReferralRelationships").mockReturnValue({
    data: list,
    isLoading: false,
    isError: false,
    refetch: vi.fn(),
  } as unknown as ReturnType<typeof useReferralsModule.useReferralRelationships>);
}

function mockPrograms() {
  vi.spyOn(useReferralsModule, "useReferralPrograms").mockReturnValue({
    data: [],
    isLoading: false,
    isError: false,
    refetch: vi.fn(),
  } as unknown as ReturnType<typeof useReferralsModule.useReferralPrograms>);
}

const TWO_RELATIONSHIPS: PaginatedResponse<ReferralRelationship> = {
  data: [
    makeRelationship({ id: "1", referred_identity_key: "+919999999999" }),
    makeRelationship({ id: "2", referred_identity_key: "friend@example.com", status: "qualified" }),
  ],
  pagination: { page: 1, page_size: 25, total: 2 },
  meta: { request_id: "test" },
};

const EMPTY_LIST: PaginatedResponse<ReferralRelationship> = {
  data: [],
  pagination: { page: 1, page_size: 25, total: 0 },
  meta: { request_id: "test" },
};

describe("RelationshipsView", () => {
  it("renders a real (non-empty) relationship list without throwing", () => {
    mockCurrentUser(["referrals.view"]);
    mockPrograms();
    mockRelationships(TWO_RELATIONSHIPS);
    renderWithQueryClient(<RelationshipsView />);
    expect(screen.getByText("+919999999999")).toBeInTheDocument();
    expect(screen.getByText("friend@example.com")).toBeInTheDocument();
  });

  it("shows the attribute-referral button for a user with referrals.manage", () => {
    mockCurrentUser(["referrals.view", "referrals.manage"]);
    mockPrograms();
    mockRelationships(EMPTY_LIST);
    renderWithQueryClient(<RelationshipsView />);
    expect(screen.getByRole("button", { name: /attribute referral/i })).toBeInTheDocument();
  });

  it("hides the attribute-referral button for a user without referrals.manage", () => {
    mockCurrentUser(["referrals.view"]);
    mockPrograms();
    mockRelationships(EMPTY_LIST);
    renderWithQueryClient(<RelationshipsView />);
    expect(screen.queryByRole("button", { name: /attribute referral/i })).not.toBeInTheDocument();
  });
});
