import type { ReactElement } from "react";
import { describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import type { CurrentUser, LeaveRequest, LeaveType, PaginatedResponse, StaffUserListItem } from "@rkpr/contracts";

import { LeaveView } from "./leave-view";
import * as useCurrentUserModule from "@/lib/hooks/use-current-user";
import * as useStaffOperationsModule from "@/lib/hooks/use-staff-operations";
import * as useStaffModule from "@/lib/hooks/use-staff";

function renderWithQueryClient(ui: ReactElement) {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(<QueryClientProvider client={queryClient}>{ui}</QueryClientProvider>);
}

const LEAVE_TYPE: LeaveType = {
  id: "leave-type-1",
  name: "Casual leave",
  code: "CASUAL",
  is_paid: true,
  requires_notice_days: 1,
  max_consecutive_days: null,
  allows_carry_forward: false,
  is_active: true,
};

const LEAVE_REQUEST: LeaveRequest = {
  id: "leave-1",
  staff_user_id: "staff-1",
  leave_type_id: "leave-type-1",
  start_date: "2026-08-05",
  end_date: "2026-08-06",
  is_partial_day: false,
  partial_day_portion: null,
  reason: null,
  status: "submitted",
  approver_id: null,
  decision_reason: null,
  decided_at: null,
};

const STAFF_PAGE: PaginatedResponse<StaffUserListItem> = {
  data: [
    {
      id: "staff-1",
      employee_code: "RK-0001",
      display_name: "Ananya Rao",
      email: "ananya@example.com",
      department_id: null,
      job_title: null,
      account_status: "active",
      employment_status: "full_time",
      is_privileged: false,
    },
  ],
  pagination: { page: 1, page_size: 100, total: 1 },
  meta: { request_id: "test" },
};

function mockCurrentUser(permissions: string[]) {
  vi.spyOn(useCurrentUserModule, "useCurrentUser").mockReturnValue({
    data: { permissions } as CurrentUser,
    isLoading: false,
  } as ReturnType<typeof useCurrentUserModule.useCurrentUser>);
}

function mockData() {
  vi.spyOn(useStaffModule, "useStaffList").mockReturnValue({
    data: STAFF_PAGE,
    isLoading: false,
  } as unknown as ReturnType<typeof useStaffModule.useStaffList>);

  vi.spyOn(useStaffOperationsModule, "useLeaveRequests").mockReturnValue({
    data: [LEAVE_REQUEST],
    isLoading: false,
  } as unknown as ReturnType<typeof useStaffOperationsModule.useLeaveRequests>);

  vi.spyOn(useStaffOperationsModule, "useLeaveTypes").mockReturnValue({
    data: [LEAVE_TYPE],
    isLoading: false,
  } as unknown as ReturnType<typeof useStaffOperationsModule.useLeaveTypes>);

  vi.spyOn(useStaffOperationsModule, "useDecideLeaveRequest").mockReturnValue({
    mutate: vi.fn(),
    isPending: false,
  } as unknown as ReturnType<typeof useStaffOperationsModule.useDecideLeaveRequest>);

  vi.spyOn(useStaffOperationsModule, "useCreateLeaveType").mockReturnValue({
    mutate: vi.fn(),
    isPending: false,
  } as unknown as ReturnType<typeof useStaffOperationsModule.useCreateLeaveType>);
}

describe("LeaveView", () => {
  it("renders the submitted leave request with the requesting staff member's name", () => {
    mockCurrentUser(["staff.leave.view"]);
    mockData();
    renderWithQueryClient(<LeaveView />);

    expect(screen.getByText(/Ananya Rao/)).toBeInTheDocument();
    expect(screen.getByText(/Casual leave/)).toBeInTheDocument();
  });

  it("shows approve/reject actions for a user with staff.leave.approve", () => {
    mockCurrentUser(["staff.leave.view", "staff.leave.approve"]);
    mockData();
    renderWithQueryClient(<LeaveView />);

    expect(screen.getByRole("button", { name: /approve/i })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /reject/i })).toBeInTheDocument();
  });

  it("hides approve/reject actions for a user without staff.leave.approve", () => {
    mockCurrentUser(["staff.leave.view"]);
    mockData();
    renderWithQueryClient(<LeaveView />);

    expect(screen.queryByRole("button", { name: /approve/i })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /reject/i })).not.toBeInTheDocument();
  });
});
