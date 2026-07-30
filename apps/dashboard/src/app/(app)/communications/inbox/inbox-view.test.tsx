import type { ReactElement } from "react";
import { describe, expect, it, vi, beforeEach } from "vitest";
import { render, screen } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import type { Conversation, CurrentUser, PaginatedResponse } from "@rkpr/contracts";

import { InboxView } from "./inbox-view";
import * as useCurrentUserModule from "@/lib/hooks/use-current-user";
import * as useCommunicationsModule from "@/lib/hooks/use-communications";

vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: vi.fn() }),
  usePathname: () => "/communications/inbox",
  useSearchParams: () => new URLSearchParams(),
}));

// InboxView always mounts NewConversationModal, whose form calls
// useCreateConversation() (and channel reference data) unconditionally at
// render time — every TanStack useMutation() needs a QueryClient in
// context to exist at all, whether or not it's ever triggered.
function renderWithQueryClient(ui: ReactElement) {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(<QueryClientProvider client={queryClient}>{ui}</QueryClientProvider>);
}

function makeConversation(overrides: Partial<Conversation>): Conversation {
  return {
    id: "11111111-1111-1111-1111-111111111111",
    conversation_number: "CONV-AAAA1111",
    channel_id: "channel-1",
    customer_id: null,
    lead_id: null,
    guest_name: "Ananya Rao",
    phone_e164: "+919845012345",
    email: null,
    subject: null,
    status: "open",
    priority: "normal",
    source: "inbound",
    assigned_staff_id: null,
    last_inbound_at: null,
    last_outbound_at: null,
    last_activity_at: "2026-07-30T10:00:00Z",
    first_response_at: null,
    resolved_at: null,
    closed_at: null,
    snoozed_until: null,
    unread_count: 0,
    version: 1,
    created_at: "2026-07-30T10:00:00Z",
    updated_at: "2026-07-30T10:00:00Z",
    ...overrides,
  };
}

const EMPTY_LIST: PaginatedResponse<Conversation> = {
  data: [],
  pagination: { page: 1, page_size: 25, total: 0 },
  meta: { request_id: "test" },
};

const TWO_CONVERSATIONS: PaginatedResponse<Conversation> = {
  data: [
    makeConversation({ id: "1", guest_name: "Ananya Rao", status: "open" }),
    makeConversation({
      id: "2",
      conversation_number: "CONV-BBBB2222",
      guest_name: "Rahul Mehta",
      status: "resolved",
    }),
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

function mockChannels() {
  vi.spyOn(useCommunicationsModule, "useCommunicationChannels").mockReturnValue({
    data: [],
    isLoading: false,
  } as unknown as ReturnType<typeof useCommunicationsModule.useCommunicationChannels>);
}

function mockInboxList(list: PaginatedResponse<Conversation>) {
  vi.spyOn(useCommunicationsModule, "useInboxList").mockReturnValue({
    data: list,
    isLoading: false,
    isError: false,
    refetch: vi.fn(),
  } as unknown as ReturnType<typeof useCommunicationsModule.useInboxList>);
}

describe("InboxView", () => {
  beforeEach(() => {
    mockChannels();
  });

  it("renders a real (non-empty) conversation list without throwing", () => {
    mockCurrentUser(["communications.view", "communications.create"]);
    mockInboxList(TWO_CONVERSATIONS);
    renderWithQueryClient(<InboxView />);
    expect(screen.getByText("Ananya Rao")).toBeInTheDocument();
    expect(screen.getByText("Rahul Mehta")).toBeInTheDocument();
  });

  it("shows the create button for a user with communications.create", () => {
    mockCurrentUser(["communications.view", "communications.create"]);
    mockInboxList(EMPTY_LIST);
    renderWithQueryClient(<InboxView />);
    expect(screen.getByRole("button", { name: /new conversation/i })).toBeInTheDocument();
  });

  it("hides the create button for a user without communications.create", () => {
    mockCurrentUser(["communications.view"]);
    mockInboxList(EMPTY_LIST);
    renderWithQueryClient(<InboxView />);
    expect(screen.queryByRole("button", { name: /new conversation/i })).not.toBeInTheDocument();
  });

  it("shows the empty state when there are no conversations", () => {
    mockCurrentUser(["communications.view"]);
    mockInboxList(EMPTY_LIST);
    renderWithQueryClient(<InboxView />);
    expect(screen.getByText(/no conversations match these filters/i)).toBeInTheDocument();
  });
});
