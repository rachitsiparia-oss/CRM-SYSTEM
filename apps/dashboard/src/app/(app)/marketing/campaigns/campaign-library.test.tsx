import type { ReactElement } from "react";
import { describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import type { Campaign, CurrentUser, PaginatedResponse } from "@rkpr/contracts";

import { CampaignLibrary } from "./campaign-library";
import * as useCurrentUserModule from "@/lib/hooks/use-current-user";
import * as useCampaignsModule from "@/lib/hooks/use-campaigns";
import * as useSegmentsModule from "@/lib/hooks/use-segments";

vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: vi.fn() }),
  usePathname: () => "/marketing/campaigns",
  useSearchParams: () => new URLSearchParams(),
}));

function renderWithQueryClient(ui: ReactElement) {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(<QueryClientProvider client={queryClient}>{ui}</QueryClientProvider>);
}

function makeCampaign(overrides: Partial<Campaign>): Campaign {
  return {
    id: "11111111-1111-1111-1111-111111111111",
    code: "SUMMER_PROMO",
    name: "Summer promo",
    objective: null,
    campaign_type: null,
    status: "draft",
    channel_templates: { whatsapp: "summer_promo_v1" },
    target_segment_ids: ["seg-1"],
    excluded_segment_ids: null,
    linked_offer_id: null,
    scheduled_at: null,
    send_window_start_local: null,
    send_window_end_local: null,
    audience_snapshot_taken_at: null,
    estimated_size: null,
    budget_minor: null,
    owner_staff_id: null,
    approved_by: null,
    approved_at: null,
    started_at: null,
    completed_at: null,
    cancelled_reason: null,
    created_at: "2026-07-30T10:00:00Z",
    updated_at: "2026-07-30T10:00:00Z",
    ...overrides,
  };
}

const EMPTY_LIST: PaginatedResponse<Campaign> = {
  data: [],
  pagination: { page: 1, page_size: 25, total: 0 },
  meta: { request_id: "test" },
};

const TWO_CAMPAIGNS: PaginatedResponse<Campaign> = {
  data: [
    makeCampaign({ id: "1", name: "Summer promo" }),
    makeCampaign({ id: "2", code: "WINTER_PROMO", name: "Winter promo", status: "running" }),
  ],
  pagination: { page: 1, page_size: 25, total: 2 },
  meta: { request_id: "test" },
};

function mockCurrentUser(permissions: string[]) {
  vi.spyOn(useCurrentUserModule, "useCurrentUser").mockReturnValue({
    data: { permissions } as CurrentUser,
    isLoading: false,
  } as ReturnType<typeof useCurrentUserModule.useCurrentUser>);
}

function mockCampaignList(list: PaginatedResponse<Campaign>) {
  vi.spyOn(useCampaignsModule, "useCampaignList").mockReturnValue({
    data: list,
    isLoading: false,
    isError: false,
    refetch: vi.fn(),
  } as unknown as ReturnType<typeof useCampaignsModule.useCampaignList>);
}

function mockSegmentList() {
  vi.spyOn(useSegmentsModule, "useSegmentList").mockReturnValue({
    data: { data: [], pagination: { page: 1, page_size: 100, total: 0 }, meta: { request_id: "test" } },
    isLoading: false,
    isError: false,
    refetch: vi.fn(),
  } as unknown as ReturnType<typeof useSegmentsModule.useSegmentList>);
}

describe("CampaignLibrary", () => {
  it("renders a real (non-empty) campaign list without throwing", () => {
    mockCurrentUser(["campaigns.view"]);
    mockCampaignList(TWO_CAMPAIGNS);
    mockSegmentList();
    renderWithQueryClient(<CampaignLibrary />);
    expect(screen.getByText("Summer promo")).toBeInTheDocument();
    expect(screen.getByText("Winter promo")).toBeInTheDocument();
  });

  it("shows the create button for a user with campaigns.manage", () => {
    mockCurrentUser(["campaigns.view", "campaigns.manage"]);
    mockCampaignList(EMPTY_LIST);
    mockSegmentList();
    renderWithQueryClient(<CampaignLibrary />);
    expect(screen.getByRole("button", { name: /new campaign/i })).toBeInTheDocument();
  });

  it("hides the create button for a user without campaigns.manage", () => {
    mockCurrentUser(["campaigns.view"]);
    mockCampaignList(EMPTY_LIST);
    mockSegmentList();
    renderWithQueryClient(<CampaignLibrary />);
    expect(screen.queryByRole("button", { name: /new campaign/i })).not.toBeInTheDocument();
  });
});
