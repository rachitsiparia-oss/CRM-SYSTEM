"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import type {
  BusinessHours,
  BusinessHoursUpdateInput,
  CustomerReservationStats,
  DataResponse,
  DiningArea,
  DiningAreaCreateInput,
  DiningAreaUpdateInput,
  HolidayCalendarCreateInput,
  HolidayCalendarEntry,
  HolidayCalendarUpdateInput,
  PaginatedResponse,
  Reservation,
  ReservationApprovalInput,
  ReservationCreateInput,
  ReservationDashboardStats,
  ReservationNote,
  ReservationNoteInput,
  ReservationPolicies,
  ReservationPoliciesUpdateInput,
  ReservationSettings,
  ReservationSettingsUpdateInput,
  ReservationStatusHistoryEntry,
  ReservationTableAssignment,
  ReservationTimelineEntry,
  ReservationUpdateInput,
  RestaurantTable,
  RestaurantTableCreateInput,
  RestaurantTableUpdateInput,
  TableBlock,
  TableBlockCreateInput,
  Waitlist,
  WaitlistCreateInput,
  WalkInCreateInput,
} from "@rkpr/contracts";
import { apiFetchClient } from "@/lib/api/browser";

const BASE = "/api/v1/reservations";

// --- Reservations ------------------------------------------------------------

export interface ReservationListParams {
  page: number;
  pageSize: number;
  search?: string;
  reservationStatus?: string;
  source?: string;
  customerId?: string;
  diningAreaId?: string;
  dateFrom?: string;
  dateTo?: string;
}

export function useReservationList(params: ReservationListParams) {
  const query = new URLSearchParams({
    page: String(params.page),
    page_size: String(params.pageSize),
  });
  if (params.search) query.set("search", params.search);
  if (params.reservationStatus) query.set("reservation_status", params.reservationStatus);
  if (params.source) query.set("source", params.source);
  if (params.customerId) query.set("customer_id", params.customerId);
  if (params.diningAreaId) query.set("dining_area_id", params.diningAreaId);
  if (params.dateFrom) query.set("date_from", params.dateFrom);
  if (params.dateTo) query.set("date_to", params.dateTo);

  return useQuery({
    queryKey: ["reservations", "list", params],
    queryFn: () => apiFetchClient<PaginatedResponse<Reservation>>(`${BASE}?${query.toString()}`),
    placeholderData: (previous) => previous,
  });
}

export function useReservationDetail(reservationId: string | undefined) {
  return useQuery({
    queryKey: ["reservations", reservationId],
    queryFn: () => apiFetchClient<DataResponse<Reservation>>(`${BASE}/${reservationId}`),
    select: (response) => response.data,
    enabled: !!reservationId,
  });
}

export function useReservationDashboardStats(targetDate: string) {
  return useQuery({
    queryKey: ["reservations", "dashboard-stats", targetDate],
    queryFn: () =>
      apiFetchClient<DataResponse<ReservationDashboardStats>>(
        `${BASE}/dashboard/stats?target_date=${targetDate}`,
      ),
    select: (response) => response.data,
    refetchInterval: 60_000,
  });
}

export function useCustomerReservationStats(customerId: string | undefined) {
  return useQuery({
    queryKey: ["reservations", "customer-stats", customerId],
    queryFn: () =>
      apiFetchClient<DataResponse<CustomerReservationStats>>(
        `${BASE}/customers/${customerId}/stats`,
      ),
    select: (response) => response.data,
    enabled: !!customerId,
  });
}

function useInvalidateReservation(reservationId?: string) {
  const queryClient = useQueryClient();
  return () => {
    queryClient.invalidateQueries({ queryKey: ["reservations"] });
    if (reservationId) queryClient.invalidateQueries({ queryKey: ["reservations", reservationId] });
  };
}

export function useCreateReservation() {
  const invalidate = useInvalidateReservation();
  return useMutation({
    mutationFn: (input: ReservationCreateInput) =>
      apiFetchClient<DataResponse<Reservation>>(BASE, { method: "POST", body: input }),
    onSuccess: invalidate,
  });
}

export function useCreateWalkIn() {
  const invalidate = useInvalidateReservation();
  return useMutation({
    mutationFn: (input: WalkInCreateInput) =>
      apiFetchClient<DataResponse<Reservation>>(`${BASE}/walk-in`, {
        method: "POST",
        body: input,
      }),
    onSuccess: invalidate,
  });
}

export function useUpdateReservation(reservationId: string) {
  const invalidate = useInvalidateReservation(reservationId);
  return useMutation({
    mutationFn: (input: ReservationUpdateInput) =>
      apiFetchClient<DataResponse<Reservation>>(`${BASE}/${reservationId}`, {
        method: "PATCH",
        body: input,
      }),
    onSuccess: invalidate,
  });
}

/** Only transitions app.reservations.states allows will succeed — the
 * backend enforces the state machine and per-target permissions; this hook
 * just surfaces whatever error comes back. */
export function useTransitionReservation(reservationId: string) {
  const invalidate = useInvalidateReservation(reservationId);
  return useMutation({
    mutationFn: (input: { newStatus: string; reason?: string }) =>
      apiFetchClient<DataResponse<Reservation>>(`${BASE}/${reservationId}/transition`, {
        method: "POST",
        body: { new_status: input.newStatus, reason: input.reason ?? null },
      }),
    onSuccess: invalidate,
  });
}

export function useDecideReservationApproval(reservationId: string) {
  const invalidate = useInvalidateReservation(reservationId);
  return useMutation({
    mutationFn: (input: ReservationApprovalInput) =>
      apiFetchClient<DataResponse<Reservation>>(`${BASE}/${reservationId}/approval`, {
        method: "POST",
        body: input,
      }),
    onSuccess: invalidate,
  });
}

export function useAssignReservationTables(reservationId: string) {
  const invalidate = useInvalidateReservation(reservationId);
  return useMutation({
    mutationFn: (tableIds: string[]) =>
      apiFetchClient<DataResponse<ReservationTableAssignment[]>>(
        `${BASE}/${reservationId}/assign-tables`,
        { method: "POST", body: { table_ids: tableIds } },
      ),
    onSuccess: invalidate,
  });
}

export function useUnassignReservationTables(reservationId: string) {
  const invalidate = useInvalidateReservation(reservationId);
  return useMutation({
    mutationFn: (releaseTables: boolean = true) =>
      apiFetchClient<DataResponse<{ ok: boolean }>>(
        `${BASE}/${reservationId}/unassign-tables?release_tables=${releaseTables}`,
        { method: "POST" },
      ),
    onSuccess: invalidate,
  });
}

export function useLinkReservationOrder(reservationId: string) {
  const invalidate = useInvalidateReservation(reservationId);
  return useMutation({
    mutationFn: (orderId: string) =>
      apiFetchClient<DataResponse<Reservation>>(`${BASE}/${reservationId}/link-order`, {
        method: "POST",
        body: { order_id: orderId },
      }),
    onSuccess: invalidate,
  });
}

export function useReservationTimeline(reservationId: string | undefined) {
  return useQuery({
    queryKey: ["reservations", reservationId, "timeline"],
    queryFn: () =>
      apiFetchClient<PaginatedResponse<ReservationTimelineEntry>>(
        `${BASE}/${reservationId}/timeline?page=1&page_size=50`,
      ),
    select: (response) => response.data,
    enabled: !!reservationId,
  });
}

export function useReservationStatusHistory(reservationId: string | undefined) {
  return useQuery({
    queryKey: ["reservations", reservationId, "status-history"],
    queryFn: () =>
      apiFetchClient<DataResponse<ReservationStatusHistoryEntry[]>>(
        `${BASE}/${reservationId}/status-history`,
      ),
    select: (response) => response.data,
    enabled: !!reservationId,
  });
}

export function useReservationNotes(reservationId: string | undefined) {
  return useQuery({
    queryKey: ["reservations", reservationId, "notes"],
    queryFn: () =>
      apiFetchClient<DataResponse<ReservationNote[]>>(`${BASE}/${reservationId}/notes`),
    select: (response) => response.data,
    enabled: !!reservationId,
  });
}

export function useAddReservationNote(reservationId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (input: ReservationNoteInput) =>
      apiFetchClient<DataResponse<ReservationNote>>(`${BASE}/${reservationId}/notes`, {
        method: "POST",
        body: input,
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["reservations", reservationId, "notes"] });
      queryClient.invalidateQueries({ queryKey: ["reservations", reservationId, "timeline"] });
    },
  });
}

// --- Availability --------------------------------------------------------

export interface AvailabilityParams {
  targetDate: string;
  startTime: string;
  endTime?: string;
  partySize: number;
  diningAreaId?: string;
}

export function useAvailability(params: AvailabilityParams | undefined) {
  const query = params
    ? new URLSearchParams({
        target_date: params.targetDate,
        start_time: params.startTime,
        party_size: String(params.partySize),
        ...(params.endTime ? { end_time: params.endTime } : {}),
        ...(params.diningAreaId ? { dining_area_id: params.diningAreaId } : {}),
      })
    : undefined;

  return useQuery({
    queryKey: ["reservations", "availability", params],
    queryFn: () =>
      apiFetchClient<DataResponse<RestaurantTable[]>>(`${BASE}/availability?${query?.toString()}`),
    select: (response) => response.data,
    enabled: !!params,
  });
}

// --- Dining areas -------------------------------------------------------

export function useDiningAreas(includeArchived = false) {
  return useQuery({
    queryKey: ["reservations", "dining-areas", includeArchived],
    queryFn: () =>
      apiFetchClient<DataResponse<DiningArea[]>>(
        `${BASE}/dining-areas?include_archived=${includeArchived}`,
      ),
    select: (response) => response.data,
  });
}

function useInvalidateDiningAreas() {
  const queryClient = useQueryClient();
  return () => queryClient.invalidateQueries({ queryKey: ["reservations", "dining-areas"] });
}

export function useCreateDiningArea() {
  const invalidate = useInvalidateDiningAreas();
  return useMutation({
    mutationFn: (input: DiningAreaCreateInput) =>
      apiFetchClient<DataResponse<DiningArea>>(`${BASE}/dining-areas`, {
        method: "POST",
        body: input,
      }),
    onSuccess: invalidate,
  });
}

export function useUpdateDiningArea(diningAreaId: string) {
  const invalidate = useInvalidateDiningAreas();
  return useMutation({
    mutationFn: (input: DiningAreaUpdateInput) =>
      apiFetchClient<DataResponse<DiningArea>>(`${BASE}/dining-areas/${diningAreaId}`, {
        method: "PATCH",
        body: input,
      }),
    onSuccess: invalidate,
  });
}

export function useArchiveDiningArea(diningAreaId: string) {
  const invalidate = useInvalidateDiningAreas();
  return useMutation({
    mutationFn: (reason: string) =>
      apiFetchClient<DataResponse<{ ok: boolean }>>(`${BASE}/dining-areas/${diningAreaId}`, {
        method: "DELETE",
        body: { reason },
      }),
    onSuccess: invalidate,
  });
}

export function useRestoreDiningArea(diningAreaId: string) {
  const invalidate = useInvalidateDiningAreas();
  return useMutation({
    mutationFn: () =>
      apiFetchClient<DataResponse<DiningArea>>(`${BASE}/dining-areas/${diningAreaId}/restore`, {
        method: "POST",
      }),
    onSuccess: invalidate,
  });
}

// --- Tables --------------------------------------------------------------

export interface TableListParams {
  diningAreaId?: string;
  tableStatus?: string;
  includeArchived?: boolean;
}

export function useTables(params: TableListParams = {}) {
  const query = new URLSearchParams();
  if (params.diningAreaId) query.set("dining_area_id", params.diningAreaId);
  if (params.tableStatus) query.set("table_status", params.tableStatus);
  query.set("include_archived", String(params.includeArchived ?? false));

  return useQuery({
    queryKey: ["reservations", "tables", params],
    queryFn: () => apiFetchClient<DataResponse<RestaurantTable[]>>(`${BASE}/tables?${query}`),
    select: (response) => response.data,
  });
}

export function useTableDetail(tableId: string | undefined) {
  return useQuery({
    queryKey: ["reservations", "tables", tableId],
    queryFn: () => apiFetchClient<DataResponse<RestaurantTable>>(`${BASE}/tables/${tableId}`),
    select: (response) => response.data,
    enabled: !!tableId,
  });
}

function useInvalidateTables(tableId?: string) {
  const queryClient = useQueryClient();
  return () => {
    queryClient.invalidateQueries({ queryKey: ["reservations", "tables"] });
    if (tableId) queryClient.invalidateQueries({ queryKey: ["reservations", "tables", tableId] });
  };
}

export function useCreateTable() {
  const invalidate = useInvalidateTables();
  return useMutation({
    mutationFn: (input: RestaurantTableCreateInput) =>
      apiFetchClient<DataResponse<RestaurantTable>>(`${BASE}/tables`, {
        method: "POST",
        body: input,
      }),
    onSuccess: invalidate,
  });
}

export function useUpdateTable(tableId: string) {
  const invalidate = useInvalidateTables(tableId);
  return useMutation({
    mutationFn: (input: RestaurantTableUpdateInput) =>
      apiFetchClient<DataResponse<RestaurantTable>>(`${BASE}/tables/${tableId}`, {
        method: "PATCH",
        body: input,
      }),
    onSuccess: invalidate,
  });
}

export function useTransitionTableStatus(tableId: string) {
  const invalidate = useInvalidateTables(tableId);
  return useMutation({
    mutationFn: (input: { newStatus: string; reason?: string }) =>
      apiFetchClient<DataResponse<RestaurantTable>>(`${BASE}/tables/${tableId}/status`, {
        method: "POST",
        body: { new_status: input.newStatus, reason: input.reason ?? null },
      }),
    onSuccess: invalidate,
  });
}

export function useMergeTables(tableId: string) {
  const invalidate = useInvalidateTables(tableId);
  return useMutation({
    mutationFn: (input: { secondaryTableIds: string[]; reason?: string }) =>
      apiFetchClient<DataResponse<RestaurantTable[]>>(`${BASE}/tables/${tableId}/merge`, {
        method: "POST",
        body: { secondary_table_ids: input.secondaryTableIds, reason: input.reason ?? null },
      }),
    onSuccess: invalidate,
  });
}

export function useSplitTables(tableId: string) {
  const invalidate = useInvalidateTables(tableId);
  return useMutation({
    mutationFn: (reason?: string) =>
      apiFetchClient<DataResponse<RestaurantTable[]>>(`${BASE}/tables/${tableId}/split`, {
        method: "POST",
        body: { reason: reason ?? null },
      }),
    onSuccess: invalidate,
  });
}

export function useTableBlocks(tableId: string | undefined, activeOnly = true) {
  return useQuery({
    queryKey: ["reservations", "tables", tableId, "blocks", activeOnly],
    queryFn: () =>
      apiFetchClient<DataResponse<TableBlock[]>>(
        `${BASE}/tables/${tableId}/blocks?active_only=${activeOnly}`,
      ),
    select: (response) => response.data,
    enabled: !!tableId,
  });
}

export function useCreateTableBlock(tableId: string) {
  const invalidate = useInvalidateTables(tableId);
  return useMutation({
    mutationFn: (input: TableBlockCreateInput) =>
      apiFetchClient<DataResponse<TableBlock>>(`${BASE}/tables/${tableId}/blocks`, {
        method: "POST",
        body: input,
      }),
    onSuccess: invalidate,
  });
}

export function useReleaseTableBlock(tableId: string) {
  const invalidate = useInvalidateTables(tableId);
  return useMutation({
    mutationFn: (blockId: string) =>
      apiFetchClient<DataResponse<TableBlock>>(
        `${BASE}/tables/${tableId}/blocks/${blockId}/release`,
        { method: "POST" },
      ),
    onSuccess: invalidate,
  });
}

// --- Waitlist ----------------------------------------------------------

export function useWaitlist(waitlistStatus?: string) {
  const query = waitlistStatus ? `?waitlist_status=${waitlistStatus}` : "";
  return useQuery({
    queryKey: ["reservations", "waitlist", waitlistStatus],
    queryFn: () => apiFetchClient<PaginatedResponse<Waitlist>>(`${BASE}/waitlist${query}`),
  });
}

function useInvalidateWaitlist() {
  const queryClient = useQueryClient();
  return () => queryClient.invalidateQueries({ queryKey: ["reservations", "waitlist"] });
}

export function useAddToWaitlist() {
  const invalidate = useInvalidateWaitlist();
  return useMutation({
    mutationFn: (input: WaitlistCreateInput) =>
      apiFetchClient<DataResponse<Waitlist>>(`${BASE}/waitlist`, { method: "POST", body: input }),
    onSuccess: invalidate,
  });
}

export function useNotifyWaitlistEntry() {
  const invalidate = useInvalidateWaitlist();
  return useMutation({
    mutationFn: (entryId: string) =>
      apiFetchClient<DataResponse<Waitlist>>(`${BASE}/waitlist/${entryId}/notify`, {
        method: "POST",
      }),
    onSuccess: invalidate,
  });
}

export function usePromoteWaitlistEntry() {
  const invalidate = useInvalidateWaitlist();
  return useMutation({
    mutationFn: (input: { entryId: string; reservationId: string }) =>
      apiFetchClient<DataResponse<Waitlist>>(`${BASE}/waitlist/${input.entryId}/promote`, {
        method: "POST",
        body: { reservation_id: input.reservationId },
      }),
    onSuccess: invalidate,
  });
}

export function useCancelWaitlistEntry() {
  const invalidate = useInvalidateWaitlist();
  return useMutation({
    mutationFn: (input: { entryId: string; reason?: string }) =>
      apiFetchClient<DataResponse<Waitlist>>(`${BASE}/waitlist/${input.entryId}/cancel`, {
        method: "POST",
        body: { reason: input.reason ?? null },
      }),
    onSuccess: invalidate,
  });
}

// --- Business hours, holidays, policies, settings --------------------------

export function useBusinessHours() {
  return useQuery({
    queryKey: ["reservations", "business-hours"],
    queryFn: () => apiFetchClient<DataResponse<BusinessHours[]>>(`${BASE}/business-hours`),
    select: (response) => response.data,
  });
}

export function useUpdateBusinessHours(dayOfWeek: number) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (input: BusinessHoursUpdateInput) =>
      apiFetchClient<DataResponse<BusinessHours>>(`${BASE}/business-hours/${dayOfWeek}`, {
        method: "PATCH",
        body: input,
      }),
    onSuccess: () =>
      queryClient.invalidateQueries({ queryKey: ["reservations", "business-hours"] }),
  });
}

export function useHolidays(dateFrom?: string, dateTo?: string) {
  const query = new URLSearchParams();
  if (dateFrom) query.set("date_from", dateFrom);
  if (dateTo) query.set("date_to", dateTo);
  return useQuery({
    queryKey: ["reservations", "holidays", dateFrom, dateTo],
    queryFn: () => apiFetchClient<DataResponse<HolidayCalendarEntry[]>>(`${BASE}/holidays?${query}`),
    select: (response) => response.data,
  });
}

function useInvalidateHolidays() {
  const queryClient = useQueryClient();
  return () => queryClient.invalidateQueries({ queryKey: ["reservations", "holidays"] });
}

export function useCreateHoliday() {
  const invalidate = useInvalidateHolidays();
  return useMutation({
    mutationFn: (input: HolidayCalendarCreateInput) =>
      apiFetchClient<DataResponse<HolidayCalendarEntry>>(`${BASE}/holidays`, {
        method: "POST",
        body: input,
      }),
    onSuccess: invalidate,
  });
}

export function useUpdateHoliday(holidayId: string) {
  const invalidate = useInvalidateHolidays();
  return useMutation({
    mutationFn: (input: HolidayCalendarUpdateInput) =>
      apiFetchClient<DataResponse<HolidayCalendarEntry>>(`${BASE}/holidays/${holidayId}`, {
        method: "PATCH",
        body: input,
      }),
    onSuccess: invalidate,
  });
}

export function useArchiveHoliday(holidayId: string) {
  const invalidate = useInvalidateHolidays();
  return useMutation({
    mutationFn: (reason: string) =>
      apiFetchClient<DataResponse<{ ok: boolean }>>(`${BASE}/holidays/${holidayId}`, {
        method: "DELETE",
        body: { reason },
      }),
    onSuccess: invalidate,
  });
}

export function useReservationPolicies() {
  return useQuery({
    queryKey: ["reservations", "policies"],
    queryFn: () => apiFetchClient<DataResponse<ReservationPolicies>>(`${BASE}/policies`),
    select: (response) => response.data,
  });
}

export function useUpdateReservationPolicies() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (input: ReservationPoliciesUpdateInput) =>
      apiFetchClient<DataResponse<ReservationPolicies>>(`${BASE}/policies`, {
        method: "PATCH",
        body: input,
      }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["reservations", "policies"] }),
  });
}

export function useReservationSettings() {
  return useQuery({
    queryKey: ["reservations", "settings"],
    queryFn: () => apiFetchClient<DataResponse<ReservationSettings>>(`${BASE}/settings`),
    select: (response) => response.data,
  });
}

export function useUpdateReservationSettings() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (input: ReservationSettingsUpdateInput) =>
      apiFetchClient<DataResponse<ReservationSettings>>(`${BASE}/settings`, {
        method: "PATCH",
        body: input,
      }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["reservations", "settings"] }),
  });
}
