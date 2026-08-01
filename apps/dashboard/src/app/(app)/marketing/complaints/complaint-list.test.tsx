import type { ReactElement } from "react";
import { describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import type { Complaint, CurrentUser, PaginatedResponse } from "@rkpr/contracts";

import { ComplaintList } from "./complaint-list";
import * as useCurrentUserModule from "@/lib/hooks/use-current-user";
import * as useComplaintsModule from "@/lib/hooks/use-complaints";

vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: vi.fn() }),
  usePathname: () => "/marketing/complaints",
  useSearchParams: () => new URLSearchParams(),
}));

function renderWithQueryClient(ui: ReactElement) {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(<QueryClientProvider client={queryClient}>{ui}</QueryClientProvider>);
}

function makeComplaint(overrides: Partial<Complaint>): Complaint {
  return {
    id: "11111111-1111-1111-1111-111111111111",
    complaint_number: "CMP-AAAAAAAA",
    customer_id: "22222222-2222-2222-2222-222222222222",
    source_type: "direct",
    feedback_id: null,
    conversation_id: null,
    order_id: null,
    reservation_id: null,
    category: "delay",
    title: "Order delivered late",
    description: "Order arrived an hour late.",
    severity: "medium",
    priority: "normal",
    status: "new",
    channel: null,
    assigned_staff_id: null,
    assigned_department_id: null,
    current_escalation_level: 0,
    sla_policy_id: null,
    first_response_due_at: null,
    acknowledgement_due_at: null,
    resolution_due_at: null,
    follow_up_due_at: null,
    first_responded_at: null,
    acknowledged_at: null,
    resolved_at: null,
    closed_at: null,
    reopened_at: null,
    reopened_count: 0,
    customer_sentiment: null,
    root_cause: null,
    resolution_summary: null,
    customer_visible_summary: null,
    is_hr_sensitive: false,
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

function mockComplaintList(list: PaginatedResponse<Complaint>) {
  vi.spyOn(useComplaintsModule, "useComplaintList").mockReturnValue({
    data: list,
    isLoading: false,
    isError: false,
    refetch: vi.fn(),
  } as unknown as ReturnType<typeof useComplaintsModule.useComplaintList>);
}

const TWO_COMPLAINTS: PaginatedResponse<Complaint> = {
  data: [
    makeComplaint({ id: "1", complaint_number: "CMP-11111111", title: "Late delivery" }),
    makeComplaint({
      id: "2",
      complaint_number: "CMP-22222222",
      title: "Rude staff member",
      severity: "critical",
      current_escalation_level: 1,
    }),
  ],
  pagination: { page: 1, page_size: 25, total: 2 },
  meta: { request_id: "test" },
};

const EMPTY_LIST: PaginatedResponse<Complaint> = {
  data: [],
  pagination: { page: 1, page_size: 25, total: 0 },
  meta: { request_id: "test" },
};

describe("ComplaintList", () => {
  it("renders a real (non-empty) complaint list without throwing", () => {
    mockCurrentUser(["complaints.view"]);
    mockComplaintList(TWO_COMPLAINTS);
    renderWithQueryClient(<ComplaintList />);
    expect(screen.getByText("CMP-11111111")).toBeInTheDocument();
    expect(screen.getByText("CMP-22222222")).toBeInTheDocument();
    expect(screen.getByText("Escalated L1")).toBeInTheDocument();
  });

  it("shows the create button for a user with complaints.create", () => {
    mockCurrentUser(["complaints.view", "complaints.create"]);
    mockComplaintList(EMPTY_LIST);
    renderWithQueryClient(<ComplaintList />);
    expect(screen.getByRole("button", { name: /new complaint/i })).toBeInTheDocument();
  });

  it("hides the create button for a user without complaints.create", () => {
    mockCurrentUser(["complaints.view"]);
    mockComplaintList(EMPTY_LIST);
    renderWithQueryClient(<ComplaintList />);
    expect(screen.queryByRole("button", { name: /new complaint/i })).not.toBeInTheDocument();
  });
});
