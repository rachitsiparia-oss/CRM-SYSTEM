import type { ReactElement } from "react";
import { describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import type { CurrentUser, Offer, PaginatedResponse } from "@rkpr/contracts";

import { OfferLibrary } from "./offer-library";
import * as useCurrentUserModule from "@/lib/hooks/use-current-user";
import * as useOffersModule from "@/lib/hooks/use-offers";

vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: vi.fn() }),
  usePathname: () => "/marketing/offers",
  useSearchParams: () => new URLSearchParams(),
}));

function renderWithQueryClient(ui: ReactElement) {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(<QueryClientProvider client={queryClient}>{ui}</QueryClientProvider>);
}

function makeOffer(overrides: Partial<Offer>): Offer {
  return {
    id: "11111111-1111-1111-1111-111111111111",
    offer_code: "WELCOME10",
    internal_name: "Welcome 10% off",
    customer_facing_name: "10% off your first order",
    offer_type: "percentage_discount",
    status: "active",
    requires_code: true,
    stackability_group: null,
    is_exclusive: false,
    budget_cap_minor: null,
    redemption_cap: null,
    redemption_count: 0,
    requires_approval: false,
    approved_by: null,
    approved_at: null,
    financial_owner_id: null,
    terms_and_notes: null,
    latest_version_number: 1,
    latest_version_id: "version-1",
    created_at: "2026-07-30T10:00:00Z",
    updated_at: "2026-07-30T10:00:00Z",
    ...overrides,
  };
}

const EMPTY_LIST: PaginatedResponse<Offer> = {
  data: [],
  pagination: { page: 1, page_size: 25, total: 0 },
  meta: { request_id: "test" },
};

const TWO_OFFERS: PaginatedResponse<Offer> = {
  data: [
    makeOffer({ id: "1", internal_name: "Welcome 10% off" }),
    makeOffer({ id: "2", offer_code: "COMBO199", internal_name: "Combo at 199", offer_type: "combo_price" }),
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

function mockOfferList(list: PaginatedResponse<Offer>) {
  vi.spyOn(useOffersModule, "useOfferList").mockReturnValue({
    data: list,
    isLoading: false,
    isError: false,
    refetch: vi.fn(),
  } as unknown as ReturnType<typeof useOffersModule.useOfferList>);
}

describe("OfferLibrary", () => {
  it("renders a real (non-empty) offer list without throwing", () => {
    mockCurrentUser(["offers.view"]);
    mockOfferList(TWO_OFFERS);
    renderWithQueryClient(<OfferLibrary />);
    expect(screen.getByText("Welcome 10% off")).toBeInTheDocument();
    expect(screen.getByText("Combo at 199")).toBeInTheDocument();
  });

  it("shows the create button for a user with offers.manage", () => {
    mockCurrentUser(["offers.view", "offers.manage"]);
    mockOfferList(EMPTY_LIST);
    renderWithQueryClient(<OfferLibrary />);
    expect(screen.getByRole("button", { name: /new offer/i })).toBeInTheDocument();
  });

  it("hides the create button for a user without offers.manage", () => {
    mockCurrentUser(["offers.view"]);
    mockOfferList(EMPTY_LIST);
    renderWithQueryClient(<OfferLibrary />);
    expect(screen.queryByRole("button", { name: /new offer/i })).not.toBeInTheDocument();
  });
});
