import type { ReactElement } from "react";
import { describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import type { CommercialRiskFlag, CurrentUser, PaginatedResponse } from "@rkpr/contracts";

import { RiskQueue } from "./risk-queue";
import * as useCurrentUserModule from "@/lib/hooks/use-current-user";
import * as useCommercialRiskModule from "@/lib/hooks/use-commercial-risk";

vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: vi.fn() }),
  usePathname: () => "/marketing/commercial-risk",
  useSearchParams: () => new URLSearchParams(),
}));

function renderWithQueryClient(ui: ReactElement) {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(<QueryClientProvider client={queryClient}>{ui}</QueryClientProvider>);
}

function makeFlag(overrides: Partial<CommercialRiskFlag>): CommercialRiskFlag {
  return {
    id: "11111111-1111-1111-1111-111111111111",
    flag_type: "repeated_manual_adjustment",
    status: "open",
    customer_id: "customer-1",
    staff_user_id: null,
    related_type: null,
    related_id: null,
    summary: "Three manual adjustments in 24 hours.",
    detail: null,
    reviewed_by: null,
    reviewed_at: null,
    resolution_note: null,
    task_id: null,
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

function mockFlagList(list: PaginatedResponse<CommercialRiskFlag>) {
  vi.spyOn(useCommercialRiskModule, "useCommercialRiskFlagList").mockReturnValue({
    data: list,
    isLoading: false,
    isError: false,
    refetch: vi.fn(),
  } as unknown as ReturnType<typeof useCommercialRiskModule.useCommercialRiskFlagList>);
}

const TWO_FLAGS: PaginatedResponse<CommercialRiskFlag> = {
  data: [
    makeFlag({ id: "1", summary: "Three manual adjustments in 24 hours." }),
    makeFlag({ id: "2", summary: "Self-referral attempt detected.", flag_type: "self_referral_attempt" }),
  ],
  pagination: { page: 1, page_size: 25, total: 2 },
  meta: { request_id: "test" },
};

const EMPTY_LIST: PaginatedResponse<CommercialRiskFlag> = {
  data: [],
  pagination: { page: 1, page_size: 25, total: 0 },
  meta: { request_id: "test" },
};

describe("RiskQueue", () => {
  it("renders a real (non-empty) flag list without throwing", () => {
    mockCurrentUser(["commercial_risk.view"]);
    mockFlagList(TWO_FLAGS);
    renderWithQueryClient(<RiskQueue />);
    expect(screen.getByText("Three manual adjustments in 24 hours.")).toBeInTheDocument();
    expect(screen.getByText("Self-referral attempt detected.")).toBeInTheDocument();
  });

  it("shows the review action for a user with commercial_risk.review", () => {
    mockCurrentUser(["commercial_risk.view", "commercial_risk.review"]);
    mockFlagList(TWO_FLAGS);
    renderWithQueryClient(<RiskQueue />);
    expect(screen.getAllByRole("button", { name: /review/i }).length).toBeGreaterThan(0);
  });

  it("hides the review action for a user without commercial_risk.review", () => {
    mockCurrentUser(["commercial_risk.view"]);
    mockFlagList(TWO_FLAGS);
    renderWithQueryClient(<RiskQueue />);
    expect(screen.queryByRole("button", { name: /review/i })).not.toBeInTheDocument();
  });

  it("shows the empty state when there are no flagged events", () => {
    mockCurrentUser(["commercial_risk.view"]);
    mockFlagList(EMPTY_LIST);
    renderWithQueryClient(<RiskQueue />);
    expect(screen.getByText(/flags appear automatically/i)).toBeInTheDocument();
  });
});
