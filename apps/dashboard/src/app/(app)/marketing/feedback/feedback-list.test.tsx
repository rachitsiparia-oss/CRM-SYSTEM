import type { ReactElement } from "react";
import { describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import type { CurrentUser, Feedback, PaginatedResponse } from "@rkpr/contracts";

import { FeedbackList } from "./feedback-list";
import * as useCurrentUserModule from "@/lib/hooks/use-current-user";
import * as useFeedbackModule from "@/lib/hooks/use-feedback";

vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: vi.fn() }),
  usePathname: () => "/marketing/feedback",
  useSearchParams: () => new URLSearchParams(),
}));

function renderWithQueryClient(ui: ReactElement) {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(<QueryClientProvider client={queryClient}>{ui}</QueryClientProvider>);
}

function makeFeedback(overrides: Partial<Feedback>): Feedback {
  return {
    id: "11111111-1111-1111-1111-111111111111",
    feedback_number: "FB-AAAAAAAA",
    customer_id: "22222222-2222-2222-2222-222222222222",
    guest_name: null,
    guest_contact: null,
    source: "website",
    order_id: null,
    reservation_id: null,
    campaign_id: null,
    comment: "Great meal",
    sentiment: "positive",
    consent_for_follow_up: false,
    assigned_staff_id: null,
    status: "new",
    priority: "normal",
    acknowledged_at: null,
    resolved_at: null,
    closed_at: null,
    converted_to_complaint_id: null,
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

function mockFeedbackList(list: PaginatedResponse<Feedback>) {
  vi.spyOn(useFeedbackModule, "useFeedbackList").mockReturnValue({
    data: list,
    isLoading: false,
    isError: false,
    refetch: vi.fn(),
  } as unknown as ReturnType<typeof useFeedbackModule.useFeedbackList>);
}

const TWO_FEEDBACK: PaginatedResponse<Feedback> = {
  data: [
    makeFeedback({ id: "1", feedback_number: "FB-11111111", comment: "Loved the tacos" }),
    makeFeedback({
      id: "2",
      feedback_number: "FB-22222222",
      comment: "Order was late",
      sentiment: "negative",
    }),
  ],
  pagination: { page: 1, page_size: 25, total: 2 },
  meta: { request_id: "test" },
};

const EMPTY_LIST: PaginatedResponse<Feedback> = {
  data: [],
  pagination: { page: 1, page_size: 25, total: 0 },
  meta: { request_id: "test" },
};

describe("FeedbackList", () => {
  it("renders a real (non-empty) feedback list without throwing", () => {
    mockCurrentUser(["feedback.view"]);
    mockFeedbackList(TWO_FEEDBACK);
    renderWithQueryClient(<FeedbackList />);
    expect(screen.getByText("FB-11111111")).toBeInTheDocument();
    expect(screen.getByText("FB-22222222")).toBeInTheDocument();
  });

  it("shows the log-feedback button for a user with feedback.create", () => {
    mockCurrentUser(["feedback.view", "feedback.create"]);
    mockFeedbackList(EMPTY_LIST);
    renderWithQueryClient(<FeedbackList />);
    expect(screen.getByRole("button", { name: /log feedback/i })).toBeInTheDocument();
  });

  it("hides the log-feedback button for a user without feedback.create", () => {
    mockCurrentUser(["feedback.view"]);
    mockFeedbackList(EMPTY_LIST);
    renderWithQueryClient(<FeedbackList />);
    expect(screen.queryByRole("button", { name: /log feedback/i })).not.toBeInTheDocument();
  });
});
