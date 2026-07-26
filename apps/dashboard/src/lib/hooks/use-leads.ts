"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import type {
  ConversionPreview,
  Customer,
  DataResponse,
  DuplicateLeadMatch,
  Lead,
  LeadActivityEntry,
  LeadFollowUp,
  LeadListItem,
  PaginatedResponse,
} from "@rkpr/contracts";
import { apiFetchClient } from "@/lib/api/browser";

export interface LeadListParams {
  page: number;
  pageSize: number;
  search?: string;
  leadStatus?: string;
  source?: string;
  priority?: string;
  unassigned?: boolean;
  overdueFollowUp?: boolean;
}

export function useLeadList(params: LeadListParams) {
  const query = new URLSearchParams({
    page: String(params.page),
    page_size: String(params.pageSize),
  });
  if (params.search) query.set("search", params.search);
  if (params.leadStatus) query.set("lead_status", params.leadStatus);
  if (params.source) query.set("source", params.source);
  if (params.priority) query.set("priority", params.priority);
  if (params.unassigned) query.set("unassigned", "true");
  if (params.overdueFollowUp) query.set("overdue_follow_up", "true");

  return useQuery({
    queryKey: ["leads", "list", params],
    queryFn: () =>
      apiFetchClient<PaginatedResponse<LeadListItem>>(`/api/v1/leads?${query.toString()}`),
    placeholderData: (previous) => previous,
  });
}

export function useLeadDetail(leadId: string | undefined) {
  return useQuery({
    queryKey: ["leads", leadId],
    queryFn: () => apiFetchClient<DataResponse<Lead>>(`/api/v1/leads/${leadId}`),
    select: (response) => response.data,
    enabled: !!leadId,
  });
}

export function useLeadDuplicates(phone: string, email: string, excludeLeadId?: string) {
  const query = new URLSearchParams();
  if (phone) query.set("phone", phone);
  if (email) query.set("email", email);
  if (excludeLeadId) query.set("exclude_lead_id", excludeLeadId);

  return useQuery({
    queryKey: ["leads", "duplicates", phone, email, excludeLeadId],
    queryFn: () =>
      apiFetchClient<DataResponse<DuplicateLeadMatch[]>>(
        `/api/v1/leads/duplicates?${query.toString()}`,
      ),
    select: (response) => response.data,
    enabled: !!(phone || email),
    retry: false,
  });
}

function useInvalidateLead(leadId?: string) {
  const queryClient = useQueryClient();
  return () => {
    queryClient.invalidateQueries({ queryKey: ["leads"] });
    if (leadId) queryClient.invalidateQueries({ queryKey: ["leads", leadId] });
  };
}

export interface CreateLeadInput {
  lead_type: string;
  display_name: string;
  organization_name?: string | null;
  contact_name?: string | null;
  phone_e164?: string | null;
  email?: string | null;
  source: string;
  campaign_reference?: string | null;
  priority: string;
  estimated_value_minor?: number | null;
  party_size?: number | null;
  requested_date?: string | null;
  description?: string | null;
}

export function useCreateLead() {
  const invalidate = useInvalidateLead();
  return useMutation({
    mutationFn: (input: CreateLeadInput) =>
      apiFetchClient<DataResponse<Lead>>("/api/v1/leads", { method: "POST", body: input }),
    onSuccess: invalidate,
  });
}

export function useUpdateLead(leadId: string) {
  const invalidate = useInvalidateLead(leadId);
  return useMutation({
    mutationFn: (input: Record<string, unknown>) =>
      apiFetchClient<DataResponse<Lead>>(`/api/v1/leads/${leadId}`, {
        method: "PATCH",
        body: input,
      }),
    onSuccess: invalidate,
  });
}

/** Only transitions the backend's state machine allows will succeed; `won`
 * is never reachable here (app/leads/states.py) — use `useConvertLead`. */
export function useTransitionLead(leadId: string) {
  const invalidate = useInvalidateLead(leadId);
  return useMutation({
    mutationFn: (input: { newStatus: string; reason?: string; lostReason?: string }) =>
      apiFetchClient<DataResponse<Lead>>(`/api/v1/leads/${leadId}/transition`, {
        method: "POST",
        body: {
          new_status: input.newStatus,
          reason: input.reason ?? null,
          lost_reason: input.lostReason ?? null,
        },
      }),
    onSuccess: invalidate,
  });
}

export function useAssignLead(leadId: string) {
  const invalidate = useInvalidateLead(leadId);
  return useMutation({
    mutationFn: (assignedStaffId: string) =>
      apiFetchClient<DataResponse<Lead>>(`/api/v1/leads/${leadId}/assign`, {
        method: "POST",
        body: { assigned_staff_id: assignedStaffId },
      }),
    onSuccess: invalidate,
  });
}

export function useSetLeadDoNotContact(leadId: string) {
  const invalidate = useInvalidateLead(leadId);
  return useMutation({
    mutationFn: (value: boolean) =>
      apiFetchClient<DataResponse<Lead>>(
        `/api/v1/leads/${leadId}/do-not-contact?value=${value ? "true" : "false"}`,
        { method: "POST" },
      ),
    onSuccess: invalidate,
  });
}

export function useArchiveLead(leadId: string) {
  const invalidate = useInvalidateLead(leadId);
  return useMutation({
    mutationFn: (reason: string) =>
      apiFetchClient<DataResponse<{ ok: boolean }>>(`/api/v1/leads/${leadId}`, {
        method: "DELETE",
        body: { reason },
      }),
    onSuccess: invalidate,
  });
}

export function useLeadTimeline(leadId: string | undefined) {
  return useQuery({
    queryKey: ["leads", leadId, "timeline"],
    queryFn: () =>
      apiFetchClient<PaginatedResponse<LeadActivityEntry>>(
        `/api/v1/leads/${leadId}/timeline?page=1&page_size=50`,
      ),
    select: (response) => response.data,
    enabled: !!leadId,
  });
}

export function useAddLeadActivity(leadId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (input: { activity_type: string; summary: string }) =>
      apiFetchClient<DataResponse<LeadActivityEntry>>(`/api/v1/leads/${leadId}/activities`, {
        method: "POST",
        body: input,
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["leads", leadId, "timeline"] });
      queryClient.invalidateQueries({ queryKey: ["leads", leadId] });
    },
  });
}

export function useLeadFollowUps(leadId: string | undefined) {
  return useQuery({
    queryKey: ["leads", leadId, "follow-ups"],
    queryFn: () =>
      apiFetchClient<DataResponse<LeadFollowUp[]>>(`/api/v1/leads/${leadId}/follow-ups`),
    select: (response) => response.data,
    enabled: !!leadId,
  });
}

function useInvalidateFollowUps(leadId: string) {
  const queryClient = useQueryClient();
  return () => {
    queryClient.invalidateQueries({ queryKey: ["leads", leadId, "follow-ups"] });
    queryClient.invalidateQueries({ queryKey: ["leads", leadId, "timeline"] });
    queryClient.invalidateQueries({ queryKey: ["leads", leadId] });
  };
}

export function useScheduleFollowUp(leadId: string) {
  const invalidate = useInvalidateFollowUps(leadId);
  return useMutation({
    mutationFn: (input: {
      scheduledAt: string;
      assignedTo: string;
      purpose?: string;
      channel?: string;
    }) =>
      apiFetchClient<DataResponse<LeadFollowUp>>(`/api/v1/leads/${leadId}/follow-ups`, {
        method: "POST",
        body: {
          scheduled_at: input.scheduledAt,
          assigned_to: input.assignedTo,
          purpose: input.purpose ?? null,
          channel: input.channel ?? null,
        },
      }),
    onSuccess: invalidate,
  });
}

export function useCompleteFollowUp(leadId: string) {
  const invalidate = useInvalidateFollowUps(leadId);
  return useMutation({
    mutationFn: (input: { followUpId: string; outcome?: string }) =>
      apiFetchClient<DataResponse<LeadFollowUp>>(
        `/api/v1/leads/${leadId}/follow-ups/${input.followUpId}/complete`,
        { method: "POST", body: { outcome: input.outcome ?? null } },
      ),
    onSuccess: invalidate,
  });
}

export function useRescheduleFollowUp(leadId: string) {
  const invalidate = useInvalidateFollowUps(leadId);
  return useMutation({
    mutationFn: (input: { followUpId: string; scheduledAt: string; reason?: string }) =>
      apiFetchClient<DataResponse<LeadFollowUp>>(
        `/api/v1/leads/${leadId}/follow-ups/${input.followUpId}/reschedule`,
        {
          method: "POST",
          body: { scheduled_at: input.scheduledAt, reason: input.reason ?? null },
        },
      ),
    onSuccess: invalidate,
  });
}

export function useConversionPreview(leadId: string | undefined, enabled: boolean) {
  return useQuery({
    queryKey: ["leads", leadId, "convert-preview"],
    queryFn: () =>
      apiFetchClient<DataResponse<ConversionPreview>>(`/api/v1/leads/${leadId}/convert/preview`),
    select: (response) => response.data,
    enabled: enabled && !!leadId,
    retry: false,
  });
}

export function useConvertLead(leadId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    // `idempotencyKey` is required: a retried conversion (double click, lost
    // response, refresh) must return the same customer instead of creating a
    // second one — CLAUDE.md section 7.
    mutationFn: (input: { idempotencyKey: string; existingCustomerId?: string | null }) =>
      apiFetchClient<DataResponse<Customer>>(`/api/v1/leads/${leadId}/convert`, {
        method: "POST",
        body: {
          idempotency_key: input.idempotencyKey,
          existing_customer_id: input.existingCustomerId ?? null,
        },
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["leads"] });
      queryClient.invalidateQueries({ queryKey: ["customers"] });
    },
  });
}
