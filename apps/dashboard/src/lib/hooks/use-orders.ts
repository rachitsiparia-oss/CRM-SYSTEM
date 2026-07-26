"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import type {
  CustomerListItem,
  DataResponse,
  Order,
  OrderChargeInput,
  OrderCreateInput,
  OrderDashboardStats,
  OrderDiscountInput,
  OrderItemInput,
  OrderListItem,
  OrderNote,
  OrderPayment,
  OrderStatusHistoryEntry,
  OrderTaxInput,
  OrderTimelineEntry,
  OrderUpdateInput,
  PaginatedResponse,
} from "@rkpr/contracts";
import { apiFetchClient } from "@/lib/api/browser";

export interface OrderListParams {
  page: number;
  pageSize: number;
  search?: string;
  orderStatus?: string;
  source?: string;
  orderType?: string;
  paymentStatus?: string;
  assignedStaffId?: string;
  dateFrom?: string;
  dateTo?: string;
  minAmountMinor?: number;
  maxAmountMinor?: number;
  sort?: string;
}

export function useOrderDashboardStats() {
  return useQuery({
    queryKey: ["orders", "dashboard-stats"],
    queryFn: () =>
      apiFetchClient<DataResponse<OrderDashboardStats>>("/api/v1/orders/dashboard/stats"),
    select: (response) => response.data,
    // Refresh periodically so the dashboard stays current during a shift
    // without requiring a manual reload — this is a live operational view.
    refetchInterval: 60_000,
  });
}

export function useOrderList(params: OrderListParams) {
  const query = new URLSearchParams({
    page: String(params.page),
    page_size: String(params.pageSize),
  });
  if (params.search) query.set("search", params.search);
  if (params.orderStatus) query.set("order_status", params.orderStatus);
  if (params.source) query.set("source", params.source);
  if (params.orderType) query.set("order_type", params.orderType);
  if (params.paymentStatus) query.set("payment_status", params.paymentStatus);
  if (params.assignedStaffId) query.set("assigned_staff_id", params.assignedStaffId);
  if (params.dateFrom) query.set("date_from", params.dateFrom);
  if (params.dateTo) query.set("date_to", params.dateTo);
  if (params.minAmountMinor !== undefined) query.set("min_amount_minor", String(params.minAmountMinor));
  if (params.maxAmountMinor !== undefined) query.set("max_amount_minor", String(params.maxAmountMinor));
  if (params.sort) query.set("sort", params.sort);

  return useQuery({
    queryKey: ["orders", "list", params],
    queryFn: () =>
      apiFetchClient<PaginatedResponse<OrderListItem>>(`/api/v1/orders?${query.toString()}`),
    placeholderData: (previous) => previous,
  });
}

export function useOrderDetail(orderId: string | undefined) {
  return useQuery({
    queryKey: ["orders", orderId],
    queryFn: () => apiFetchClient<DataResponse<Order>>(`/api/v1/orders/${orderId}`),
    select: (response) => response.data,
    enabled: !!orderId,
  });
}

export function useSearchOrderCustomers(query: string) {
  return useQuery({
    queryKey: ["orders", "search-customers", query],
    queryFn: () =>
      apiFetchClient<DataResponse<CustomerListItem[]>>(
        `/api/v1/orders/search-customers?q=${encodeURIComponent(query)}`,
      ),
    select: (response) => response.data,
    enabled: query.length > 0,
  });
}

function useInvalidateOrder(orderId?: string) {
  const queryClient = useQueryClient();
  return () => {
    queryClient.invalidateQueries({ queryKey: ["orders"] });
    if (orderId) queryClient.invalidateQueries({ queryKey: ["orders", orderId] });
  };
}

export interface CreateOrderInput {
  customerId?: string | null;
  leadId?: string | null;
  source: string;
  orderType: string;
  assignedStaffId?: string | null;
  items: OrderItemInput[];
  discounts?: OrderDiscountInput[];
  taxes?: OrderTaxInput[];
  charges?: OrderChargeInput[];
  internalNotes?: string | null;
  customerNotes?: string | null;
  estimatedCompletionTime?: string | null;
  idempotencyKey: string;
}

export function useCreateOrder() {
  const invalidate = useInvalidateOrder();
  return useMutation({
    mutationFn: (input: CreateOrderInput) => {
      const body: OrderCreateInput = {
        customer_id: input.customerId ?? null,
        lead_id: input.leadId ?? null,
        source: input.source as OrderCreateInput["source"],
        order_type: input.orderType as OrderCreateInput["order_type"],
        assigned_staff_id: input.assignedStaffId ?? null,
        items: input.items,
        discounts: input.discounts ?? [],
        taxes: input.taxes ?? [],
        charges: input.charges ?? [],
        internal_notes: input.internalNotes ?? null,
        customer_notes: input.customerNotes ?? null,
        estimated_completion_time: input.estimatedCompletionTime ?? null,
        idempotency_key: input.idempotencyKey,
      };
      return apiFetchClient<DataResponse<Order>>("/api/v1/orders", { method: "POST", body });
    },
    onSuccess: invalidate,
  });
}

export function useUpdateOrder(orderId: string) {
  const invalidate = useInvalidateOrder(orderId);
  return useMutation({
    mutationFn: (input: OrderUpdateInput) =>
      apiFetchClient<DataResponse<Order>>(`/api/v1/orders/${orderId}`, {
        method: "PATCH",
        body: input,
      }),
    onSuccess: invalidate,
  });
}

/** Only transitions app.orders.states allows will succeed. Cancelling
 * requires orders.cancel and completing requires orders.complete on top of
 * the baseline orders.transition permission — the backend enforces both;
 * this hook just surfaces whatever error comes back. */
export function useTransitionOrder(orderId: string) {
  const invalidate = useInvalidateOrder(orderId);
  return useMutation({
    mutationFn: (input: { newStatus: string; reason?: string }) =>
      apiFetchClient<DataResponse<Order>>(`/api/v1/orders/${orderId}/transition`, {
        method: "POST",
        body: { new_status: input.newStatus, reason: input.reason ?? null },
      }),
    onSuccess: invalidate,
  });
}

export function useAssignOrder(orderId: string) {
  const invalidate = useInvalidateOrder(orderId);
  return useMutation({
    mutationFn: (assignedStaffId: string) =>
      apiFetchClient<DataResponse<Order>>(`/api/v1/orders/${orderId}/assign`, {
        method: "POST",
        body: { assigned_staff_id: assignedStaffId },
      }),
    onSuccess: invalidate,
  });
}

export function useOrderTimeline(orderId: string | undefined) {
  return useQuery({
    queryKey: ["orders", orderId, "timeline"],
    queryFn: () =>
      apiFetchClient<PaginatedResponse<OrderTimelineEntry>>(
        `/api/v1/orders/${orderId}/timeline?page=1&page_size=50`,
      ),
    select: (response) => response.data,
    enabled: !!orderId,
  });
}

export function useOrderStatusHistory(orderId: string | undefined) {
  return useQuery({
    queryKey: ["orders", orderId, "status-history"],
    queryFn: () =>
      apiFetchClient<DataResponse<OrderStatusHistoryEntry[]>>(
        `/api/v1/orders/${orderId}/status-history`,
      ),
    select: (response) => response.data,
    enabled: !!orderId,
  });
}

export function useOrderPayments(orderId: string | undefined) {
  return useQuery({
    queryKey: ["orders", orderId, "payments"],
    queryFn: () =>
      apiFetchClient<DataResponse<OrderPayment[]>>(`/api/v1/orders/${orderId}/payments`),
    select: (response) => response.data,
    enabled: !!orderId,
  });
}

function useInvalidatePayments(orderId: string) {
  const queryClient = useQueryClient();
  return () => {
    queryClient.invalidateQueries({ queryKey: ["orders", orderId, "payments"] });
    queryClient.invalidateQueries({ queryKey: ["orders", orderId, "timeline"] });
    queryClient.invalidateQueries({ queryKey: ["orders", orderId] });
  };
}

export function useAddOrderPayment(orderId: string) {
  const invalidate = useInvalidatePayments(orderId);
  return useMutation({
    mutationFn: (input: {
      method: string;
      status?: string;
      amountMinor: number;
      reference?: string;
      notes?: string;
    }) =>
      apiFetchClient<DataResponse<OrderPayment>>(`/api/v1/orders/${orderId}/payments`, {
        method: "POST",
        body: {
          method: input.method,
          status: input.status ?? "paid",
          amount_minor: input.amountMinor,
          reference: input.reference ?? null,
          notes: input.notes ?? null,
        },
      }),
    onSuccess: invalidate,
  });
}

export function useUpdateOrderPaymentStatus(orderId: string) {
  const invalidate = useInvalidatePayments(orderId);
  return useMutation({
    mutationFn: (input: { paymentId: string; status: string }) =>
      apiFetchClient<DataResponse<OrderPayment>>(
        `/api/v1/orders/${orderId}/payments/${input.paymentId}`,
        { method: "PATCH", body: { status: input.status } },
      ),
    onSuccess: invalidate,
  });
}

export function useOrderNotes(orderId: string | undefined) {
  return useQuery({
    queryKey: ["orders", orderId, "notes"],
    queryFn: () => apiFetchClient<DataResponse<OrderNote[]>>(`/api/v1/orders/${orderId}/notes`),
    select: (response) => response.data,
    enabled: !!orderId,
  });
}

export function useAddOrderNote(orderId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (input: { content: string; isInternal?: boolean }) =>
      apiFetchClient<DataResponse<OrderNote>>(`/api/v1/orders/${orderId}/notes`, {
        method: "POST",
        body: { content: input.content, is_internal: input.isInternal ?? true },
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["orders", orderId, "notes"] });
      queryClient.invalidateQueries({ queryKey: ["orders", orderId, "timeline"] });
    },
  });
}
