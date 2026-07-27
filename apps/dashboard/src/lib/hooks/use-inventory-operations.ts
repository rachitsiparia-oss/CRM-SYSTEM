"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import type {
  Adjustment,
  AdjustmentCreateInput,
  DataResponse,
  PaginatedResponse,
  Receipt,
  ReceiptCreateInput,
  ReceiptItem,
  ReceiptItemCreateInput,
  ReceiptListItem,
  ReceiptReverseInput,
  StockCount,
  StockCountCreateInput,
  StockCountLine,
  StockCountLineRecordInput,
  StockCountListItem,
  Transfer,
  TransferCreateInput,
  TransferItem,
  TransferItemCreateInput,
  TransferListItem,
  TransferReverseInput,
  Wastage,
  WastageCreateInput,
} from "@rkpr/contracts";
import { apiFetchClient } from "@/lib/api/browser";

function useInvalidateInventory() {
  const queryClient = useQueryClient();
  return (extra: unknown[] = []) => {
    queryClient.invalidateQueries({ queryKey: ["inventory", "items"] });
    queryClient.invalidateQueries({ queryKey: ["inventory", "dashboard-stats"] });
    queryClient.invalidateQueries({ queryKey: ["inventory", "movements"] });
    for (const key of extra) queryClient.invalidateQueries({ queryKey: key as unknown[] });
  };
}

// --- Receipts ---

export function useInventoryReceipts(page: number, pageSize: number, status?: string) {
  const query = new URLSearchParams({ page: String(page), page_size: String(pageSize) });
  if (status) query.set("status", status);
  return useQuery({
    queryKey: ["inventory", "receipts", "list", page, pageSize, status],
    queryFn: () =>
      apiFetchClient<PaginatedResponse<ReceiptListItem>>(
        `/api/v1/inventory/receipts?${query.toString()}`,
      ),
    placeholderData: (previous) => previous,
  });
}

export function useInventoryReceipt(receiptId: string | undefined) {
  return useQuery({
    queryKey: ["inventory", "receipts", receiptId],
    queryFn: () => apiFetchClient<DataResponse<Receipt>>(`/api/v1/inventory/receipts/${receiptId}`),
    select: (response) => response.data,
    enabled: !!receiptId,
  });
}

export function useCreateInventoryReceipt() {
  const invalidate = useInvalidateInventory();
  return useMutation({
    mutationFn: (input: ReceiptCreateInput) =>
      apiFetchClient<DataResponse<Receipt>>("/api/v1/inventory/receipts", {
        method: "POST",
        body: input,
      }),
    onSuccess: () => invalidate([["inventory", "receipts"]]),
  });
}

export function useAddReceiptItem(receiptId: string) {
  const invalidate = useInvalidateInventory();
  return useMutation({
    mutationFn: (input: ReceiptItemCreateInput) =>
      apiFetchClient<DataResponse<ReceiptItem>>(`/api/v1/inventory/receipts/${receiptId}/items`, {
        method: "POST",
        body: input,
      }),
    onSuccess: () => invalidate([["inventory", "receipts", receiptId]]),
  });
}

export function usePostInventoryReceipt(receiptId: string) {
  const invalidate = useInvalidateInventory();
  return useMutation({
    mutationFn: () =>
      apiFetchClient<DataResponse<Receipt>>(`/api/v1/inventory/receipts/${receiptId}/post`, {
        method: "POST",
      }),
    onSuccess: () => invalidate([["inventory", "receipts"]]),
  });
}

export function useReverseInventoryReceipt(receiptId: string) {
  const invalidate = useInvalidateInventory();
  return useMutation({
    mutationFn: (input: ReceiptReverseInput) =>
      apiFetchClient<DataResponse<Receipt>>(`/api/v1/inventory/receipts/${receiptId}/reverse`, {
        method: "POST",
        body: input,
      }),
    onSuccess: () => invalidate([["inventory", "receipts"]]),
  });
}

// --- Adjustments ---

export function useInventoryAdjustments(page: number, pageSize: number, itemId?: string) {
  const query = new URLSearchParams({ page: String(page), page_size: String(pageSize) });
  if (itemId) query.set("inventory_item_id", itemId);
  return useQuery({
    queryKey: ["inventory", "adjustments", "list", page, pageSize, itemId],
    queryFn: () =>
      apiFetchClient<PaginatedResponse<Adjustment>>(
        `/api/v1/inventory/adjustments?${query.toString()}`,
      ),
    placeholderData: (previous) => previous,
  });
}

export function useCreateInventoryAdjustment() {
  const invalidate = useInvalidateInventory();
  return useMutation({
    mutationFn: (input: AdjustmentCreateInput) =>
      apiFetchClient<DataResponse<Adjustment>>("/api/v1/inventory/adjustments", {
        method: "POST",
        body: input,
      }),
    onSuccess: () => invalidate([["inventory", "adjustments"]]),
  });
}

// --- Wastage ---

export function useInventoryWastage(page: number, pageSize: number, itemId?: string) {
  const query = new URLSearchParams({ page: String(page), page_size: String(pageSize) });
  if (itemId) query.set("inventory_item_id", itemId);
  return useQuery({
    queryKey: ["inventory", "wastage", "list", page, pageSize, itemId],
    queryFn: () =>
      apiFetchClient<PaginatedResponse<Wastage>>(`/api/v1/inventory/wastage?${query.toString()}`),
    placeholderData: (previous) => previous,
  });
}

export function useCreateInventoryWastage() {
  const invalidate = useInvalidateInventory();
  return useMutation({
    mutationFn: (input: WastageCreateInput) =>
      apiFetchClient<DataResponse<Wastage>>("/api/v1/inventory/wastage", {
        method: "POST",
        body: input,
      }),
    onSuccess: () => invalidate([["inventory", "wastage"]]),
  });
}

// --- Transfers ---

export function useInventoryTransfers(page: number, pageSize: number, status?: string) {
  const query = new URLSearchParams({ page: String(page), page_size: String(pageSize) });
  if (status) query.set("status", status);
  return useQuery({
    queryKey: ["inventory", "transfers", "list", page, pageSize, status],
    queryFn: () =>
      apiFetchClient<PaginatedResponse<TransferListItem>>(
        `/api/v1/inventory/transfers?${query.toString()}`,
      ),
    placeholderData: (previous) => previous,
  });
}

export function useInventoryTransfer(transferId: string | undefined) {
  return useQuery({
    queryKey: ["inventory", "transfers", transferId],
    queryFn: () =>
      apiFetchClient<DataResponse<Transfer>>(`/api/v1/inventory/transfers/${transferId}`),
    select: (response) => response.data,
    enabled: !!transferId,
  });
}

export function useCreateInventoryTransfer() {
  const invalidate = useInvalidateInventory();
  return useMutation({
    mutationFn: (input: TransferCreateInput) =>
      apiFetchClient<DataResponse<Transfer>>("/api/v1/inventory/transfers", {
        method: "POST",
        body: input,
      }),
    onSuccess: () => invalidate([["inventory", "transfers"]]),
  });
}

export function useAddTransferItem(transferId: string) {
  const invalidate = useInvalidateInventory();
  return useMutation({
    mutationFn: (input: TransferItemCreateInput) =>
      apiFetchClient<DataResponse<TransferItem>>(
        `/api/v1/inventory/transfers/${transferId}/items`,
        { method: "POST", body: input },
      ),
    onSuccess: () => invalidate([["inventory", "transfers", transferId]]),
  });
}

export function usePostInventoryTransfer(transferId: string) {
  const invalidate = useInvalidateInventory();
  return useMutation({
    mutationFn: () =>
      apiFetchClient<DataResponse<Transfer>>(`/api/v1/inventory/transfers/${transferId}/post`, {
        method: "POST",
      }),
    onSuccess: () => invalidate([["inventory", "transfers"]]),
  });
}

export function useReverseInventoryTransfer(transferId: string) {
  const invalidate = useInvalidateInventory();
  return useMutation({
    mutationFn: (input: TransferReverseInput) =>
      apiFetchClient<DataResponse<Transfer>>(`/api/v1/inventory/transfers/${transferId}/reverse`, {
        method: "POST",
        body: input,
      }),
    onSuccess: () => invalidate([["inventory", "transfers"]]),
  });
}

// --- Stock counts ---

export function useInventoryStockCounts(
  page: number,
  pageSize: number,
  status?: string,
  locationId?: string,
) {
  const query = new URLSearchParams({ page: String(page), page_size: String(pageSize) });
  if (status) query.set("status", status);
  if (locationId) query.set("storage_location_id", locationId);
  return useQuery({
    queryKey: ["inventory", "counts", "list", page, pageSize, status, locationId],
    queryFn: () =>
      apiFetchClient<PaginatedResponse<StockCountListItem>>(
        `/api/v1/inventory/counts?${query.toString()}`,
      ),
    placeholderData: (previous) => previous,
  });
}

export function useInventoryStockCount(countId: string | undefined) {
  return useQuery({
    queryKey: ["inventory", "counts", countId],
    queryFn: () => apiFetchClient<DataResponse<StockCount>>(`/api/v1/inventory/counts/${countId}`),
    select: (response) => response.data,
    enabled: !!countId,
  });
}

export function useCreateInventoryStockCount() {
  const invalidate = useInvalidateInventory();
  return useMutation({
    mutationFn: (input: StockCountCreateInput) =>
      apiFetchClient<DataResponse<StockCount>>("/api/v1/inventory/counts", {
        method: "POST",
        body: input,
      }),
    onSuccess: () => invalidate([["inventory", "counts"]]),
  });
}

export function useStartInventoryStockCount(countId: string) {
  const invalidate = useInvalidateInventory();
  return useMutation({
    mutationFn: () =>
      apiFetchClient<DataResponse<StockCount>>(`/api/v1/inventory/counts/${countId}/start`, {
        method: "POST",
      }),
    onSuccess: () => invalidate([["inventory", "counts", countId]]),
  });
}

export function useRecordStockCountLine(countId: string, lineId: string) {
  const invalidate = useInvalidateInventory();
  return useMutation({
    mutationFn: (input: StockCountLineRecordInput) =>
      apiFetchClient<DataResponse<StockCountLine>>(
        `/api/v1/inventory/counts/${countId}/lines/${lineId}`,
        { method: "PATCH", body: input },
      ),
    onSuccess: () => invalidate([["inventory", "counts", countId]]),
  });
}

export function useSubmitInventoryStockCount(countId: string) {
  const invalidate = useInvalidateInventory();
  return useMutation({
    mutationFn: () =>
      apiFetchClient<DataResponse<StockCount>>(`/api/v1/inventory/counts/${countId}/submit`, {
        method: "POST",
      }),
    onSuccess: () => invalidate([["inventory", "counts", countId]]),
  });
}

export function useApproveInventoryStockCount(countId: string) {
  const invalidate = useInvalidateInventory();
  return useMutation({
    mutationFn: () =>
      apiFetchClient<DataResponse<StockCount>>(`/api/v1/inventory/counts/${countId}/approve`, {
        method: "POST",
      }),
    onSuccess: () => invalidate([["inventory", "counts", countId]]),
  });
}

export function useCancelInventoryStockCount(countId: string) {
  const invalidate = useInvalidateInventory();
  return useMutation({
    mutationFn: () =>
      apiFetchClient<DataResponse<StockCount>>(`/api/v1/inventory/counts/${countId}/cancel`, {
        method: "POST",
      }),
    onSuccess: () => invalidate([["inventory", "counts", countId]]),
  });
}
