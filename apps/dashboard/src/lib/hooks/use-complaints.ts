"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import type {
  Complaint,
  ComplaintAnalytics,
  ComplaintAssignInput,
  ComplaintCreateInput,
  ComplaintEscalateInput,
  ComplaintEscalation,
  ComplaintFollowUp,
  ComplaintLink,
  ComplaintLinkCreateInput,
  ComplaintNote,
  ComplaintTransitionInput,
  ComplaintUpdateInput,
  DataResponse,
  FollowUpCompleteInput,
  FollowUpCreateInput,
  NoteCreateInput,
  PaginatedResponse,
  RootCauseUpdateInput,
  SlaPolicy,
  SlaPolicyCreateInput,
  SlaPolicyUpdateInput,
  TimelineEntry,
} from "@rkpr/contracts";
import { apiFetchClient } from "@/lib/api/browser";

const BASE = "/api/v1/complaints";

export interface ComplaintListParams {
  page: number;
  pageSize: number;
  status?: string;
  severity?: string;
  category?: string;
  assignedStaffId?: string;
  assignedDepartmentId?: string;
  customerId?: string;
}

export function useComplaintList(params: ComplaintListParams) {
  const query = new URLSearchParams({
    page: String(params.page),
    page_size: String(params.pageSize),
  });
  if (params.status) query.set("status", params.status);
  if (params.severity) query.set("severity", params.severity);
  if (params.category) query.set("category", params.category);
  if (params.assignedStaffId) query.set("assigned_staff_id", params.assignedStaffId);
  if (params.assignedDepartmentId)
    query.set("assigned_department_id", params.assignedDepartmentId);
  if (params.customerId) query.set("customer_id", params.customerId);

  return useQuery({
    queryKey: ["complaints", "list", params],
    queryFn: () => apiFetchClient<PaginatedResponse<Complaint>>(`${BASE}?${query.toString()}`),
    placeholderData: (previous) => previous,
  });
}

export function useComplaintDetail(complaintId: string | undefined) {
  return useQuery({
    queryKey: ["complaints", complaintId],
    queryFn: () => apiFetchClient<DataResponse<Complaint>>(`${BASE}/${complaintId}`),
    select: (response) => response.data,
    enabled: !!complaintId,
  });
}

export function useComplaintTimeline(complaintId: string | undefined) {
  return useQuery({
    queryKey: ["complaints", complaintId, "timeline"],
    queryFn: () =>
      apiFetchClient<DataResponse<TimelineEntry[]>>(`${BASE}/${complaintId}/timeline`),
    select: (response) => response.data,
    enabled: !!complaintId,
  });
}

export function useComplaintAnalytics() {
  return useQuery({
    queryKey: ["complaints", "analytics"],
    queryFn: () => apiFetchClient<DataResponse<ComplaintAnalytics>>(`${BASE}/analytics`),
    select: (response) => response.data,
  });
}

function useInvalidateComplaint(complaintId?: string) {
  const queryClient = useQueryClient();
  return () => {
    queryClient.invalidateQueries({ queryKey: ["complaints", "list"] });
    queryClient.invalidateQueries({ queryKey: ["complaints", "analytics"] });
    if (complaintId) {
      queryClient.invalidateQueries({ queryKey: ["complaints", complaintId] });
      queryClient.invalidateQueries({ queryKey: ["complaints", complaintId, "timeline"] });
    }
  };
}

export function useCreateComplaint() {
  const invalidate = useInvalidateComplaint();
  return useMutation({
    mutationFn: (input: ComplaintCreateInput) =>
      apiFetchClient<DataResponse<Complaint>>(BASE, { method: "POST", body: input }),
    onSuccess: invalidate,
  });
}

export function useUpdateComplaint(complaintId: string) {
  const invalidate = useInvalidateComplaint(complaintId);
  return useMutation({
    mutationFn: (input: ComplaintUpdateInput) =>
      apiFetchClient<DataResponse<Complaint>>(`${BASE}/${complaintId}`, {
        method: "PATCH",
        body: input,
      }),
    onSuccess: invalidate,
  });
}

export function useTransitionComplaint(complaintId: string) {
  const invalidate = useInvalidateComplaint(complaintId);
  return useMutation({
    mutationFn: (input: ComplaintTransitionInput) =>
      apiFetchClient<DataResponse<Complaint>>(`${BASE}/${complaintId}/transition`, {
        method: "POST",
        body: input,
      }),
    onSuccess: invalidate,
  });
}

export function useAssignComplaint(complaintId: string) {
  const invalidate = useInvalidateComplaint(complaintId);
  return useMutation({
    mutationFn: (input: ComplaintAssignInput) =>
      apiFetchClient<DataResponse<Complaint>>(`${BASE}/${complaintId}/assign`, {
        method: "POST",
        body: input,
      }),
    onSuccess: invalidate,
  });
}

export function useEscalateComplaint(complaintId: string) {
  const invalidate = useInvalidateComplaint(complaintId);
  return useMutation({
    mutationFn: (input: ComplaintEscalateInput) =>
      apiFetchClient<DataResponse<ComplaintEscalation>>(`${BASE}/${complaintId}/escalate`, {
        method: "POST",
        body: input,
      }),
    onSuccess: invalidate,
  });
}

export function useUpdateComplaintRootCause(complaintId: string) {
  const invalidate = useInvalidateComplaint(complaintId);
  return useMutation({
    mutationFn: (input: RootCauseUpdateInput) =>
      apiFetchClient<DataResponse<Complaint>>(`${BASE}/${complaintId}/root-cause`, {
        method: "POST",
        body: input,
      }),
    onSuccess: invalidate,
  });
}

export function useAddComplaintNote(complaintId: string) {
  const invalidate = useInvalidateComplaint(complaintId);
  return useMutation({
    mutationFn: (input: NoteCreateInput) =>
      apiFetchClient<DataResponse<ComplaintNote>>(`${BASE}/${complaintId}/notes`, {
        method: "POST",
        body: input,
      }),
    onSuccess: invalidate,
  });
}

export function useScheduleComplaintFollowUp(complaintId: string) {
  const invalidate = useInvalidateComplaint(complaintId);
  return useMutation({
    mutationFn: (input: FollowUpCreateInput) =>
      apiFetchClient<DataResponse<ComplaintFollowUp>>(`${BASE}/${complaintId}/follow-ups`, {
        method: "POST",
        body: input,
      }),
    onSuccess: invalidate,
  });
}

export function useCompleteComplaintFollowUp(complaintId: string, followUpId: string) {
  const invalidate = useInvalidateComplaint(complaintId);
  return useMutation({
    mutationFn: (input: FollowUpCompleteInput) =>
      apiFetchClient<DataResponse<ComplaintFollowUp>>(
        `${BASE}/follow-ups/${followUpId}/complete`,
        { method: "POST", body: input },
      ),
    onSuccess: invalidate,
  });
}

export function useLinkComplaint(complaintId: string) {
  const invalidate = useInvalidateComplaint(complaintId);
  return useMutation({
    mutationFn: (input: ComplaintLinkCreateInput) =>
      apiFetchClient<DataResponse<ComplaintLink>>(`${BASE}/${complaintId}/links`, {
        method: "POST",
        body: input,
      }),
    onSuccess: invalidate,
  });
}

// --- SLA policies ---------------------------------------------------------

export function useSlaPolicyList(isActive?: boolean) {
  const query = new URLSearchParams();
  if (isActive !== undefined) query.set("is_active", String(isActive));
  const suffix = query.toString() ? `?${query.toString()}` : "";
  return useQuery({
    queryKey: ["complaints", "sla-policies", isActive],
    queryFn: () =>
      apiFetchClient<DataResponse<SlaPolicy[]>>(`${BASE}/sla-policies${suffix}`),
    select: (response) => response.data,
  });
}

function useInvalidateSlaPolicies() {
  const queryClient = useQueryClient();
  return () => queryClient.invalidateQueries({ queryKey: ["complaints", "sla-policies"] });
}

export function useCreateSlaPolicy() {
  const invalidate = useInvalidateSlaPolicies();
  return useMutation({
    mutationFn: (input: SlaPolicyCreateInput) =>
      apiFetchClient<DataResponse<SlaPolicy>>(`${BASE}/sla-policies`, {
        method: "POST",
        body: input,
      }),
    onSuccess: invalidate,
  });
}

export function useUpdateSlaPolicy(policyId: string) {
  const invalidate = useInvalidateSlaPolicies();
  return useMutation({
    mutationFn: (input: SlaPolicyUpdateInput) =>
      apiFetchClient<DataResponse<SlaPolicy>>(`${BASE}/sla-policies/${policyId}`, {
        method: "PATCH",
        body: input,
      }),
    onSuccess: invalidate,
  });
}

export function useRunSlaEscalations() {
  const invalidate = useInvalidateComplaint();
  return useMutation({
    mutationFn: () =>
      apiFetchClient<DataResponse<{ escalations_created: number }>>(
        `${BASE}/sla/run-escalations`,
        { method: "POST" },
      ),
    onSuccess: invalidate,
  });
}
