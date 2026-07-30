import type { ReactElement } from "react";
import { describe, expect, it, vi, beforeEach } from "vitest";
import { render, screen } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import type { CurrentUser, PaginatedResponse, Task } from "@rkpr/contracts";

import { TasksView } from "./tasks-view";
import * as useCurrentUserModule from "@/lib/hooks/use-current-user";
import * as useTasksModule from "@/lib/hooks/use-tasks";
import * as useStaffModule from "@/lib/hooks/use-staff";

vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: vi.fn() }),
  usePathname: () => "/communications/tasks",
  useSearchParams: () => new URLSearchParams(),
}));

function renderWithQueryClient(ui: ReactElement) {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(<QueryClientProvider client={queryClient}>{ui}</QueryClientProvider>);
}

function makeTask(overrides: Partial<Task>): Task {
  return {
    id: "11111111-1111-1111-1111-111111111111",
    task_number: "TASK-AAAA1111",
    title: "Restock napkins",
    description: null,
    source: "manual",
    priority: "normal",
    status: "open",
    due_at: null,
    assigned_staff_id: null,
    assigned_department_id: null,
    completed_at: null,
    completed_by: null,
    completion_notes: null,
    blocked_reason: null,
    related_type: null,
    related_id: null,
    is_recurring_template: false,
    recurrence_rule: null,
    parent_task_id: null,
    version: 1,
    created_at: "2026-07-30T10:00:00Z",
    updated_at: "2026-07-30T10:00:00Z",
    ...overrides,
  };
}

const EMPTY_LIST: PaginatedResponse<Task> = {
  data: [],
  pagination: { page: 1, page_size: 25, total: 0 },
  meta: { request_id: "test" },
};

const TWO_TASKS: PaginatedResponse<Task> = {
  data: [
    makeTask({ id: "1", title: "Restock napkins" }),
    makeTask({ id: "2", task_number: "TASK-BBBB2222", title: "Deep-clean fryer", status: "blocked" }),
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

function mockStaffList() {
  vi.spyOn(useStaffModule, "useStaffList").mockReturnValue({
    data: { data: [] },
    isLoading: false,
  } as unknown as ReturnType<typeof useStaffModule.useStaffList>);
}

function mockTaskList(list: PaginatedResponse<Task>) {
  vi.spyOn(useTasksModule, "useTaskList").mockReturnValue({
    data: list,
    isLoading: false,
    isError: false,
    refetch: vi.fn(),
  } as unknown as ReturnType<typeof useTasksModule.useTaskList>);
}

describe("TasksView", () => {
  beforeEach(() => {
    mockStaffList();
  });

  it("renders a real (non-empty) task list without throwing", () => {
    mockCurrentUser(["tasks.view", "tasks.create"]);
    mockTaskList(TWO_TASKS);
    renderWithQueryClient(<TasksView />);
    expect(screen.getByText("Restock napkins")).toBeInTheDocument();
    expect(screen.getByText("Deep-clean fryer")).toBeInTheDocument();
  });

  it("shows the create button for a user with tasks.create", () => {
    mockCurrentUser(["tasks.view", "tasks.create"]);
    mockTaskList(EMPTY_LIST);
    renderWithQueryClient(<TasksView />);
    expect(screen.getByRole("button", { name: /new task/i })).toBeInTheDocument();
  });

  it("hides the create button for a user without tasks.create", () => {
    mockCurrentUser(["tasks.view"]);
    mockTaskList(EMPTY_LIST);
    renderWithQueryClient(<TasksView />);
    expect(screen.queryByRole("button", { name: /new task/i })).not.toBeInTheDocument();
  });

  it("shows the empty state when there are no tasks", () => {
    mockCurrentUser(["tasks.view"]);
    mockTaskList(EMPTY_LIST);
    renderWithQueryClient(<TasksView />);
    expect(screen.getByText(/no tasks match these filters/i)).toBeInTheDocument();
  });
});
