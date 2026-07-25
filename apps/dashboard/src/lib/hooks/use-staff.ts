"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import type {
  DataResponse,
  Department,
  Invitation,
  PaginatedResponse,
  StaffUserDetail,
  StaffUserListItem,
} from "@rkpr/contracts";
import { apiFetchClient } from "@/lib/api/browser";

export interface StaffListParams {
  page: number;
  pageSize: number;
  search?: string;
  accountStatus?: string;
  departmentId?: string;
}

export function useStaffList(params: StaffListParams) {
  const query = new URLSearchParams({
    page: String(params.page),
    page_size: String(params.pageSize),
  });
  if (params.search) query.set("search", params.search);
  if (params.accountStatus) query.set("account_status", params.accountStatus);
  if (params.departmentId) query.set("department_id", params.departmentId);

  return useQuery({
    queryKey: ["staff-users", params],
    queryFn: () =>
      apiFetchClient<PaginatedResponse<StaffUserListItem>>(
        `/api/v1/staff-users?${query.toString()}`,
      ),
    placeholderData: (previous) => previous,
  });
}

export function useStaffDetail(staffUserId: string | undefined) {
  return useQuery({
    queryKey: ["staff-users", staffUserId],
    queryFn: () =>
      apiFetchClient<DataResponse<StaffUserDetail>>(`/api/v1/staff-users/${staffUserId}`),
    select: (response) => response.data,
    enabled: !!staffUserId,
  });
}

export function useDepartments() {
  return useQuery({
    queryKey: ["departments"],
    queryFn: () => apiFetchClient<DataResponse<Department[]>>("/api/v1/departments"),
    select: (response) => response.data,
    staleTime: 5 * 60_000,
  });
}

function useInvalidateStaff(staffUserId: string) {
  const queryClient = useQueryClient();
  return () => {
    queryClient.invalidateQueries({ queryKey: ["staff-users"] });
    queryClient.invalidateQueries({ queryKey: ["staff-users", staffUserId] });
  };
}

export function useAssignRole(staffUserId: string) {
  const invalidate = useInvalidateStaff(staffUserId);
  return useMutation({
    mutationFn: (input: { roleCode: string; reason: string }) =>
      apiFetchClient<DataResponse<StaffUserDetail>>(`/api/v1/staff-users/${staffUserId}/roles`, {
        method: "POST",
        body: { role_code: input.roleCode, reason: input.reason },
      }),
    onSuccess: invalidate,
  });
}

export function useRemoveRole(staffUserId: string) {
  const invalidate = useInvalidateStaff(staffUserId);
  return useMutation({
    mutationFn: (input: { roleCode: string; reason: string }) =>
      apiFetchClient<DataResponse<StaffUserDetail>>(
        `/api/v1/staff-users/${staffUserId}/roles/${input.roleCode}?${new URLSearchParams({ reason: input.reason }).toString()}`,
        { method: "DELETE" },
      ),
    onSuccess: invalidate,
  });
}

export function useSetAccountStatus(staffUserId: string) {
  const invalidate = useInvalidateStaff(staffUserId);
  return useMutation({
    mutationFn: (input: { action: "activate" | "deactivate"; reason: string }) =>
      apiFetchClient<DataResponse<StaffUserDetail>>(
        `/api/v1/staff-users/${staffUserId}/${input.action}`,
        { method: "POST", body: { reason: input.reason } },
      ),
    onSuccess: invalidate,
  });
}

export function useInviteStaff() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (input: {
      email: string;
      firstName: string;
      lastName?: string;
      departmentId?: string;
      roleCode: string;
    }) =>
      apiFetchClient<DataResponse<Invitation>>("/api/v1/staff-invitations", {
        method: "POST",
        body: {
          email: input.email,
          first_name: input.firstName,
          last_name: input.lastName || null,
          department_id: input.departmentId || null,
          role_code: input.roleCode,
        },
      }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["staff-users"] }),
  });
}
