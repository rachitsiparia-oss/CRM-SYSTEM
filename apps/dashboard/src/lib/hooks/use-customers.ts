"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import type {
  Customer,
  CustomerAddress,
  CustomerConsent,
  CustomerListItem,
  CustomerNote,
  DataResponse,
  DuplicateCustomerMatch,
  MergePreview,
  PaginatedResponse,
  Tag,
  TimelineEntry,
} from "@rkpr/contracts";
import { apiFetchClient } from "@/lib/api/browser";

export interface CustomerListParams {
  page: number;
  pageSize: number;
  search?: string;
  customerStatus?: string;
  customerSegment?: string;
  customerType?: string;
}

export function useCustomerList(params: CustomerListParams) {
  const query = new URLSearchParams({
    page: String(params.page),
    page_size: String(params.pageSize),
  });
  if (params.search) query.set("search", params.search);
  if (params.customerStatus) query.set("customer_status", params.customerStatus);
  if (params.customerSegment) query.set("customer_segment", params.customerSegment);
  if (params.customerType) query.set("customer_type", params.customerType);

  return useQuery({
    queryKey: ["customers", "list", params],
    queryFn: () =>
      apiFetchClient<PaginatedResponse<CustomerListItem>>(`/api/v1/customers?${query.toString()}`),
    placeholderData: (previous) => previous,
  });
}

export function useCustomerDetail(customerId: string | undefined) {
  return useQuery({
    queryKey: ["customers", customerId],
    queryFn: () => apiFetchClient<DataResponse<Customer>>(`/api/v1/customers/${customerId}`),
    select: (response) => response.data,
    enabled: !!customerId,
  });
}

/** Deterministic duplicate check, called as staff type a phone or email into
 * the create form — CORE_CRM_MODULES.md section 4.7. Debouncing is the
 * caller's job so this hook stays a plain query. */
export function useCustomerDuplicates(phone: string, email: string, excludeCustomerId?: string) {
  const query = new URLSearchParams();
  if (phone) query.set("phone", phone);
  if (email) query.set("email", email);
  if (excludeCustomerId) query.set("exclude_customer_id", excludeCustomerId);

  return useQuery({
    queryKey: ["customers", "duplicates", phone, email, excludeCustomerId],
    queryFn: () =>
      apiFetchClient<DataResponse<DuplicateCustomerMatch[]>>(
        `/api/v1/customers/duplicates?${query.toString()}`,
      ),
    select: (response) => response.data,
    enabled: !!(phone || email),
    retry: false,
  });
}

function useInvalidateCustomer(customerId?: string) {
  const queryClient = useQueryClient();
  return () => {
    queryClient.invalidateQueries({ queryKey: ["customers"] });
    if (customerId) queryClient.invalidateQueries({ queryKey: ["customers", customerId] });
  };
}

export interface CreateCustomerInput {
  customer_type: "individual" | "corporate";
  first_name?: string | null;
  last_name?: string | null;
  organization_name?: string | null;
  display_name?: string | null;
  primary_phone_e164?: string | null;
  primary_email?: string | null;
  customer_segment?: string | null;
  acquisition_source?: string | null;
}

export function useCreateCustomer() {
  const invalidate = useInvalidateCustomer();
  return useMutation({
    mutationFn: (input: CreateCustomerInput) =>
      apiFetchClient<DataResponse<Customer>>("/api/v1/customers", {
        method: "POST",
        body: input,
      }),
    onSuccess: invalidate,
  });
}

export function useUpdateCustomer(customerId: string) {
  const invalidate = useInvalidateCustomer(customerId);
  return useMutation({
    // `expected_version` must be included by the caller — the backend
    // returns 409 when it is stale, which the form surfaces as a
    // reload-and-retry message rather than silently overwriting.
    mutationFn: (input: Record<string, unknown>) =>
      apiFetchClient<DataResponse<Customer>>(`/api/v1/customers/${customerId}`, {
        method: "PATCH",
        body: input,
      }),
    onSuccess: invalidate,
  });
}

export function useArchiveCustomer(customerId: string) {
  const invalidate = useInvalidateCustomer(customerId);
  return useMutation({
    mutationFn: (reason: string) =>
      apiFetchClient<DataResponse<Customer>>(`/api/v1/customers/${customerId}`, {
        method: "DELETE",
        body: { reason },
      }),
    onSuccess: invalidate,
  });
}

export function useRestoreCustomer(customerId: string) {
  const invalidate = useInvalidateCustomer(customerId);
  return useMutation({
    mutationFn: () =>
      apiFetchClient<DataResponse<Customer>>(`/api/v1/customers/${customerId}/restore`, {
        method: "POST",
      }),
    onSuccess: invalidate,
  });
}

export function useAssignCustomer(customerId: string) {
  const invalidate = useInvalidateCustomer(customerId);
  return useMutation({
    mutationFn: (assignedStaffId: string | null) =>
      apiFetchClient<DataResponse<Customer>>(`/api/v1/customers/${customerId}/assign`, {
        method: "POST",
        body: { assigned_staff_id: assignedStaffId },
      }),
    onSuccess: invalidate,
  });
}

export function useCustomerTimeline(customerId: string | undefined) {
  return useQuery({
    queryKey: ["customers", customerId, "timeline"],
    queryFn: () =>
      apiFetchClient<PaginatedResponse<TimelineEntry>>(
        `/api/v1/customers/${customerId}/timeline?page=1&page_size=25`,
      ),
    select: (response) => response.data,
    enabled: !!customerId,
  });
}

export function useCustomerAddresses(customerId: string | undefined) {
  return useQuery({
    queryKey: ["customers", customerId, "addresses"],
    queryFn: () =>
      apiFetchClient<DataResponse<CustomerAddress[]>>(`/api/v1/customers/${customerId}/addresses`),
    select: (response) => response.data,
    enabled: !!customerId,
  });
}

export interface AddressInput {
  label?: string | null;
  address_line1: string;
  address_line2?: string | null;
  city: string;
  state: string;
  postal_code: string;
  country?: string;
  is_default?: boolean;
}

export function useAddCustomerAddress(customerId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (input: AddressInput) =>
      apiFetchClient<DataResponse<CustomerAddress>>(`/api/v1/customers/${customerId}/addresses`, {
        method: "POST",
        body: input,
      }),
    onSuccess: () =>
      queryClient.invalidateQueries({ queryKey: ["customers", customerId, "addresses"] }),
  });
}

export function useArchiveCustomerAddress(customerId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (addressId: string) =>
      apiFetchClient<DataResponse<{ ok: boolean }>>(
        `/api/v1/customers/${customerId}/addresses/${addressId}`,
        { method: "DELETE" },
      ),
    onSuccess: () =>
      queryClient.invalidateQueries({ queryKey: ["customers", customerId, "addresses"] }),
  });
}

/** Sensitive notes are filtered out server-side for staff without
 * `customers.notes.sensitive.read` — this hook never sees them, so there is
 * nothing to hide client-side. */
export function useCustomerNotes(customerId: string | undefined) {
  return useQuery({
    queryKey: ["customers", customerId, "notes"],
    queryFn: () =>
      apiFetchClient<DataResponse<CustomerNote[]>>(`/api/v1/customers/${customerId}/notes`),
    select: (response) => response.data,
    enabled: !!customerId,
  });
}

export function useAddCustomerNote(customerId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (input: { note_type: string; content: string; is_sensitive: boolean }) =>
      apiFetchClient<DataResponse<CustomerNote>>(`/api/v1/customers/${customerId}/notes`, {
        method: "POST",
        body: input,
      }),
    onSuccess: () =>
      queryClient.invalidateQueries({ queryKey: ["customers", customerId, "notes"] }),
  });
}

export function useCustomerTags(customerId: string | undefined) {
  return useQuery({
    queryKey: ["customers", customerId, "tags"],
    queryFn: () => apiFetchClient<DataResponse<Tag[]>>(`/api/v1/customers/${customerId}/tags`),
    select: (response) => response.data,
    enabled: !!customerId,
  });
}

export function useAddCustomerTag(customerId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (name: string) =>
      apiFetchClient<DataResponse<Tag>>(`/api/v1/customers/${customerId}/tags`, {
        method: "POST",
        body: { name },
      }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["customers", customerId, "tags"] }),
  });
}

export function useRemoveCustomerTag(customerId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (tagId: string) =>
      apiFetchClient<DataResponse<{ ok: boolean }>>(
        `/api/v1/customers/${customerId}/tags/${tagId}`,
        { method: "DELETE" },
      ),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["customers", customerId, "tags"] }),
  });
}

export function useSetCustomerConsent(customerId: string) {
  const invalidate = useInvalidateCustomer(customerId);
  return useMutation({
    mutationFn: (input: { consentType: string; status: string; source: string }) =>
      apiFetchClient<DataResponse<CustomerConsent>>(
        `/api/v1/customers/${customerId}/consents/${input.consentType}`,
        { method: "PUT", body: { status: input.status, source: input.source } },
      ),
    onSuccess: invalidate,
  });
}

export function useMergePreview(sourceId: string, survivingId: string, enabled: boolean) {
  const query = new URLSearchParams({
    source_customer_id: sourceId,
    surviving_customer_id: survivingId,
  });
  return useQuery({
    queryKey: ["customers", "merge-preview", sourceId, survivingId],
    queryFn: () =>
      apiFetchClient<DataResponse<MergePreview>>(
        `/api/v1/customers/merge/preview?${query.toString()}`,
        { method: "POST" },
      ),
    select: (response) => response.data,
    enabled: enabled && !!sourceId && !!survivingId && sourceId !== survivingId,
    retry: false,
  });
}

export function useExecuteMerge() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (input: {
      sourceCustomerId: string;
      survivingCustomerId: string;
      reason: string;
    }) =>
      apiFetchClient<DataResponse<Customer>>("/api/v1/customers/merge", {
        method: "POST",
        body: {
          source_customer_id: input.sourceCustomerId,
          surviving_customer_id: input.survivingCustomerId,
          reason: input.reason,
          field_resolutions: [],
        },
      }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["customers"] }),
  });
}
