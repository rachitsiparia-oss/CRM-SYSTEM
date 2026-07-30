"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import type {
  DataResponse,
  PaginatedResponse,
  Task,
  TaskAssignInput,
  TaskCreateInput,
  TaskTransitionInput,
  TaskUpdateInput,
} from "@rkpr/contracts";
import { apiFetchClient } from "@/lib/api/browser";

const BASE = "/api/v1/tasks";

export interface TaskListParams {
  page: number;
  pageSize: number;
  taskStatus?: string;
  priority?: string;
  assignedStaffId?: string;
  view?: "mine" | "due_today" | "overdue" | "blocked";
  search?: string;
}

export function useTaskList(params: TaskListParams) {
  const query = new URLSearchParams({
    page: String(params.page),
    page_size: String(params.pageSize),
  });
  if (params.taskStatus) query.set("task_status", params.taskStatus);
  if (params.priority) query.set("priority", params.priority);
  if (params.assignedStaffId) query.set("assigned_staff_id", params.assignedStaffId);
  if (params.view) query.set("view", params.view);
  if (params.search) query.set("search", params.search);

  return useQuery({
    queryKey: ["tasks", "list", params],
    queryFn: () => apiFetchClient<PaginatedResponse<Task>>(`${BASE}?${query.toString()}`),
    placeholderData: (previous) => previous,
  });
}

export function useTaskDetail(taskId: string | undefined) {
  return useQuery({
    queryKey: ["tasks", taskId],
    queryFn: () => apiFetchClient<DataResponse<Task>>(`${BASE}/${taskId}`),
    select: (response) => response.data,
    enabled: !!taskId,
  });
}

function useInvalidateTasks(taskId?: string) {
  const queryClient = useQueryClient();
  return () => {
    queryClient.invalidateQueries({ queryKey: ["tasks"] });
    if (taskId) queryClient.invalidateQueries({ queryKey: ["tasks", taskId] });
  };
}

export function useCreateTask() {
  const invalidate = useInvalidateTasks();
  return useMutation({
    mutationFn: (input: TaskCreateInput) =>
      apiFetchClient<DataResponse<Task>>(BASE, { method: "POST", body: input }),
    onSuccess: invalidate,
  });
}

export function useUpdateTask(taskId: string) {
  const invalidate = useInvalidateTasks(taskId);
  return useMutation({
    mutationFn: (input: TaskUpdateInput) =>
      apiFetchClient<DataResponse<Task>>(`${BASE}/${taskId}`, { method: "PATCH", body: input }),
    onSuccess: invalidate,
  });
}

export function useTransitionTask(taskId: string) {
  const invalidate = useInvalidateTasks(taskId);
  return useMutation({
    mutationFn: (input: TaskTransitionInput) =>
      apiFetchClient<DataResponse<Task>>(`${BASE}/${taskId}/transition`, {
        method: "POST",
        body: input,
      }),
    onSuccess: invalidate,
  });
}

export function useAssignTask(taskId: string) {
  const invalidate = useInvalidateTasks(taskId);
  return useMutation({
    mutationFn: (input: TaskAssignInput) =>
      apiFetchClient<DataResponse<Task>>(`${BASE}/${taskId}/assign`, {
        method: "POST",
        body: input,
      }),
    onSuccess: invalidate,
  });
}

export function useCancelTask() {
  const invalidate = useInvalidateTasks();
  return useMutation({
    mutationFn: (taskId: string) =>
      apiFetchClient<DataResponse<Task>>(`${BASE}/${taskId}`, { method: "DELETE" }),
    onSuccess: invalidate,
  });
}
