import type { ReactElement } from "react";
import { describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import type { CurrentUser, GiftCard, PaginatedResponse } from "@rkpr/contracts";

import { GiftCardLibrary } from "./gift-card-library";
import * as useCurrentUserModule from "@/lib/hooks/use-current-user";
import * as useGiftCardsModule from "@/lib/hooks/use-gift-cards";

vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: vi.fn() }),
  usePathname: () => "/marketing/gift-cards",
  useSearchParams: () => new URLSearchParams(),
}));

function renderWithQueryClient(ui: ReactElement) {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(<QueryClientProvider client={queryClient}>{ui}</QueryClientProvider>);
}

function makeGiftCard(overrides: Partial<GiftCard>): GiftCard {
  return {
    id: "11111111-1111-1111-1111-111111111111",
    card_number: "GC-ABCDEF12",
    masked_display: "****-****-****-WXYZ",
    purchaser_customer_id: null,
    purchaser_contact: null,
    recipient_customer_id: null,
    recipient_name: "Priya Sharma",
    recipient_contact: null,
    initial_amount_minor: 100000,
    current_balance_minor: 100000,
    status: "active",
    issued_at: "2026-07-30T10:00:00Z",
    purchased_at: "2026-07-30T10:00:00Z",
    activated_at: "2026-07-30T10:00:00Z",
    expires_at: null,
    source_order_id: null,
    delivery_status: null,
    notes: null,
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

function mockGiftCardList(list: PaginatedResponse<GiftCard>) {
  vi.spyOn(useGiftCardsModule, "useGiftCardList").mockReturnValue({
    data: list,
    isLoading: false,
    isError: false,
    refetch: vi.fn(),
  } as unknown as ReturnType<typeof useGiftCardsModule.useGiftCardList>);
}

function mockAnalytics() {
  vi.spyOn(useGiftCardsModule, "useGiftCardAnalytics").mockReturnValue({
    data: undefined,
    isLoading: false,
  } as unknown as ReturnType<typeof useGiftCardsModule.useGiftCardAnalytics>);
}

const TWO_CARDS: PaginatedResponse<GiftCard> = {
  data: [
    makeGiftCard({ id: "1", masked_display: "****-****-****-AAAA", recipient_name: "Priya Sharma" }),
    makeGiftCard({ id: "2", masked_display: "****-****-****-BBBB", recipient_name: "Rahul Verma" }),
  ],
  pagination: { page: 1, page_size: 25, total: 2 },
  meta: { request_id: "test" },
};

const EMPTY_LIST: PaginatedResponse<GiftCard> = {
  data: [],
  pagination: { page: 1, page_size: 25, total: 0 },
  meta: { request_id: "test" },
};

describe("GiftCardLibrary", () => {
  it("renders a real (non-empty) gift card list without throwing", () => {
    mockCurrentUser(["gift_cards.view"]);
    mockAnalytics();
    mockGiftCardList(TWO_CARDS);
    renderWithQueryClient(<GiftCardLibrary />);
    expect(screen.getByText("****-****-****-AAAA")).toBeInTheDocument();
    expect(screen.getByText("****-****-****-BBBB")).toBeInTheDocument();
  });

  it("shows the issue button for a user with gift_cards.issue", () => {
    mockCurrentUser(["gift_cards.view", "gift_cards.issue"]);
    mockAnalytics();
    mockGiftCardList(EMPTY_LIST);
    renderWithQueryClient(<GiftCardLibrary />);
    expect(screen.getByRole("button", { name: /issue gift card/i })).toBeInTheDocument();
  });

  it("hides the issue button for a user without gift_cards.issue", () => {
    mockCurrentUser(["gift_cards.view"]);
    mockAnalytics();
    mockGiftCardList(EMPTY_LIST);
    renderWithQueryClient(<GiftCardLibrary />);
    expect(screen.queryByRole("button", { name: /issue gift card/i })).not.toBeInTheDocument();
  });
});
