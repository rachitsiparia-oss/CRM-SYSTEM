import type { ReactElement } from "react";
import { describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import type { CurrentUser, LeaveRequest, LeaveType, StaffShift, TrainingAssignment } from "@rkpr/contracts";

import { MyWorkView } from "./my-work-view";
import * as useCurrentUserModule from "@/lib/hooks/use-current-user";
import * as useStaffOperationsModule from "@/lib/hooks/use-staff-operations";
import { formatDate, formatDateTime } from "@/lib/crm-display";

function renderWithQueryClient(ui: ReactElement) {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(<QueryClientProvider client={queryClient}>{ui}</QueryClientProvider>);
}

const CURRENT_USER = { id: "staff-1", display_name: "Ananya Rao", permissions: [] } as unknown as CurrentUser;

const SHIFT: StaffShift = {
  id: "shift-1",
  staff_user_id: "staff-1",
  shift_date: "2026-08-01",
  shift_template_id: null,
  start_at: "2026-08-01T09:00:00Z",
  end_at: "2026-08-01T17:00:00Z",
  department_id: null,
  role_on_shift: null,
  status: "published",
  notes: null,
  is_published: true,
  published_at: "2026-07-30T10:00:00Z",
  version: 1,
};

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

const TRAINING_ASSIGNMENT: TrainingAssignment = {
  id: "assignment-1",
  course_id: "course-1",
  staff_user_id: "staff-1",
  assigned_at: "2026-07-25T10:00:00Z",
  due_at: "2026-08-10",
  status: "assigned",
};

function mockHooks() {
  vi.spyOn(useCurrentUserModule, "useCurrentUser").mockReturnValue({
    data: CURRENT_USER,
    isLoading: false,
  } as ReturnType<typeof useCurrentUserModule.useCurrentUser>);

  vi.spyOn(useStaffOperationsModule, "useShiftList").mockReturnValue({
    data: [SHIFT],
    isLoading: false,
  } as unknown as ReturnType<typeof useStaffOperationsModule.useShiftList>);

  vi.spyOn(useStaffOperationsModule, "useLeaveTypes").mockReturnValue({
    data: [LEAVE_TYPE],
    isLoading: false,
  } as unknown as ReturnType<typeof useStaffOperationsModule.useLeaveTypes>);

  vi.spyOn(useStaffOperationsModule, "useLeaveRequests").mockReturnValue({
    data: [LEAVE_REQUEST],
    isLoading: false,
  } as unknown as ReturnType<typeof useStaffOperationsModule.useLeaveRequests>);

  vi.spyOn(useStaffOperationsModule, "useTrainingAssignments").mockReturnValue({
    data: [TRAINING_ASSIGNMENT],
    isLoading: false,
  } as unknown as ReturnType<typeof useStaffOperationsModule.useTrainingAssignments>);

  vi.spyOn(useStaffOperationsModule, "useAvailabilityWindows").mockReturnValue({
    data: [],
    isLoading: false,
  } as unknown as ReturnType<typeof useStaffOperationsModule.useAvailabilityWindows>);

  vi.spyOn(useStaffOperationsModule, "useSubmitLeaveRequest").mockReturnValue({
    mutate: vi.fn(),
    isPending: false,
  } as unknown as ReturnType<typeof useStaffOperationsModule.useSubmitLeaveRequest>);

  vi.spyOn(useStaffOperationsModule, "useWithdrawLeaveRequest").mockReturnValue({
    mutate: vi.fn(),
    isPending: false,
  } as unknown as ReturnType<typeof useStaffOperationsModule.useWithdrawLeaveRequest>);

  vi.spyOn(useStaffOperationsModule, "useCreateAvailabilityWindow").mockReturnValue({
    mutate: vi.fn(),
    isPending: false,
  } as unknown as ReturnType<typeof useStaffOperationsModule.useCreateAvailabilityWindow>);
}

describe("MyWorkView", () => {
  it("renders the current staff member's own shifts, leave, and training without throwing", () => {
    mockHooks();
    renderWithQueryClient(<MyWorkView />);

    expect(screen.getByText("My work")).toBeInTheDocument();
    expect(screen.getByText(new RegExp(formatDateTime(SHIFT.start_at)))).toBeInTheDocument();
    expect(
      screen.getByText(
        new RegExp(`${formatDate(LEAVE_REQUEST.start_date)}.*${formatDate(LEAVE_REQUEST.end_date)}`),
      ),
    ).toBeInTheDocument();
  });

  it("shows a withdraw action for a submitted leave request", () => {
    mockHooks();
    renderWithQueryClient(<MyWorkView />);

    expect(screen.getByRole("button", { name: /withdraw/i })).toBeInTheDocument();
  });

  it("shows empty states when there is no data", () => {
    mockHooks();
    vi.spyOn(useStaffOperationsModule, "useShiftList").mockReturnValue({
      data: [],
      isLoading: false,
    } as unknown as ReturnType<typeof useStaffOperationsModule.useShiftList>);
    vi.spyOn(useStaffOperationsModule, "useTrainingAssignments").mockReturnValue({
      data: [],
      isLoading: false,
    } as unknown as ReturnType<typeof useStaffOperationsModule.useTrainingAssignments>);
    vi.spyOn(useStaffOperationsModule, "useLeaveRequests").mockReturnValue({
      data: [],
      isLoading: false,
    } as unknown as ReturnType<typeof useStaffOperationsModule.useLeaveRequests>);

    renderWithQueryClient(<MyWorkView />);

    expect(screen.getByText("No shifts scheduled.")).toBeInTheDocument();
    expect(screen.getByText("No training assigned.")).toBeInTheDocument();
    expect(screen.getByText("No leave requests yet.")).toBeInTheDocument();
  });
});
