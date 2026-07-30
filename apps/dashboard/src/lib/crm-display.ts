import type {
  AdjustmentDirection,
  BatchStatus,
  ConversationPriority,
  ConversationStatus,
  CountStatus,
  CustomerStatus,
  FollowUpStatus,
  FoodType,
  LeadPriority,
  LeadStatus,
  NotificationPriority,
  OrderStatus,
  PaymentStatus,
  ReceiptStatus,
  ReservationStatus,
  ScheduledMessageStatus,
  StockStatus,
  TableStatus,
  TaskPriority,
  TaskStatus,
  TransferStatus,
  WaitlistStatus,
} from "@rkpr/contracts";

import type { StatusTone } from "@/components/status-badge";

/** Display-only rupee formatting from the authoritative integer minor units
 * the API returns. The backend owns every monetary calculation and rounding
 * rule (CLAUDE.md section 7); this only renders what it was given. */
export function formatMinorUnits(minor: number | null | undefined): string {
  if (minor === null || minor === undefined) return "—";
  return new Intl.NumberFormat("en-IN", {
    style: "currency",
    currency: "INR",
    minimumFractionDigits: 2,
  }).format(minor / 100);
}

/** Timestamps arrive as UTC ISO strings and are displayed in the
 * restaurant's configured timezone — CLAUDE.md section 7. */
export function formatDateTime(iso: string | null | undefined): string {
  if (!iso) return "—";
  return new Intl.DateTimeFormat("en-IN", {
    dateStyle: "medium",
    timeStyle: "short",
    timeZone: "Asia/Kolkata",
  }).format(new Date(iso));
}

export function formatDate(iso: string | null | undefined): string {
  if (!iso) return "—";
  return new Intl.DateTimeFormat("en-IN", {
    dateStyle: "medium",
    timeZone: "Asia/Kolkata",
  }).format(new Date(iso));
}

/** Turns a snake_case enum value into human-readable text. Enum values come
 * from the backend's closed CHECK-constrained lists, so this never has to
 * cope with arbitrary input. */
export function humanize(value: string | null | undefined): string {
  if (!value) return "—";
  return value.replace(/_/g, " ").replace(/^./, (c) => c.toUpperCase());
}

export const CUSTOMER_STATUS_TONES: Record<CustomerStatus, StatusTone> = {
  active: "success",
  inactive: "neutral",
  blacklisted: "danger",
  archived: "neutral",
  merged: "info",
};

export const LEAD_STATUS_TONES: Record<LeadStatus, StatusTone> = {
  new: "info",
  contacted: "info",
  qualified: "info",
  interested: "info",
  follow_up_scheduled: "warning",
  proposal_shared: "info",
  negotiating: "warning",
  won: "success",
  lost: "danger",
  closed: "neutral",
};

export const LEAD_PRIORITY_TONES: Record<LeadPriority, StatusTone> = {
  low: "neutral",
  normal: "neutral",
  high: "warning",
  urgent: "danger",
};

export const FOLLOW_UP_STATUS_TONES: Record<FollowUpStatus, StatusTone> = {
  scheduled: "info",
  due: "warning",
  completed: "success",
  cancelled: "neutral",
  missed: "danger",
};

/** A follow-up is overdue when its scheduled time has passed and it is still
 * open — the same rule the API's `overdue_follow_up` filter applies
 * server-side (CORE_CRM_MODULES.md section 5.10). Recomputed here only so a
 * row can be visually flagged without a second request. */
export function isOverdue(scheduledAt: string | null | undefined): boolean {
  if (!scheduledAt) return false;
  return new Date(scheduledAt).getTime() < Date.now();
}

export const FOOD_TYPE_TONES: Record<FoodType, StatusTone> = {
  vegetarian: "success",
  non_vegetarian: "danger",
};

export const PRODUCT_ACTIVE_TONE: Record<"active" | "inactive", StatusTone> = {
  active: "success",
  inactive: "neutral",
};

export const PRODUCT_AVAILABILITY_TONE: Record<"available" | "unavailable", StatusTone> = {
  available: "success",
  unavailable: "warning",
};

export const ORDER_STATUS_TONES: Record<OrderStatus, StatusTone> = {
  draft: "neutral",
  pending_confirmation: "warning",
  confirmed: "info",
  preparing: "info",
  ready: "success",
  completed: "success",
  cancelled: "danger",
};

export const PAYMENT_STATUS_TONES: Record<PaymentStatus, StatusTone> = {
  pending: "warning",
  partial: "warning",
  paid: "success",
  refunded: "info",
  failed: "danger",
};

// --- Phase 8: Inventory ---

/** Inventory quantities arrive as exact-decimal strings (the backend's
 * `Qty` type — CLAUDE.md section 7's money rule applied to quantities).
 * This only formats what the server already computed for display; never
 * parse a quantity string back into a number for arithmetic. */
export function formatQuantity(value: string | null | undefined, unitSymbol?: string): string {
  if (value === null || value === undefined) return "—";
  const trimmed = value.includes(".") ? value.replace(/\.?0+$/, "") : value;
  return unitSymbol ? `${trimmed} ${unitSymbol}` : trimmed;
}

export const STOCK_STATUS_TONES: Record<StockStatus, StatusTone> = {
  in_stock: "success",
  low_stock: "warning",
  critical_stock: "danger",
  out_of_stock: "danger",
  reserved: "info",
  quarantined: "warning",
  expired: "danger",
  damaged: "danger",
  under_count_review: "warning",
  discontinued: "neutral",
};

export const RECEIPT_STATUS_TONES: Record<ReceiptStatus, StatusTone> = {
  draft: "neutral",
  posted: "success",
  reversed: "danger",
};

export const TRANSFER_STATUS_TONES: Record<TransferStatus, StatusTone> = {
  draft: "neutral",
  posted: "success",
  reversed: "danger",
};

export const COUNT_STATUS_TONES: Record<CountStatus, StatusTone> = {
  draft: "neutral",
  in_progress: "info",
  submitted: "warning",
  approved: "success",
  cancelled: "danger",
};

export const BATCH_STATUS_TONES: Record<BatchStatus, StatusTone> = {
  active: "success",
  depleted: "neutral",
  quarantined: "warning",
  expired: "danger",
  damaged: "danger",
};

export const ADJUSTMENT_DIRECTION_TONES: Record<AdjustmentDirection, StatusTone> = {
  increase: "success",
  decrease: "warning",
};

// --- Phase 9: Reservations, Tables & Calendar Management ---

export const RESERVATION_STATUS_TONES: Record<ReservationStatus, StatusTone> = {
  requested: "neutral",
  pending_review: "warning",
  needs_clarification: "warning",
  approved: "info",
  rejected: "danger",
  confirmation_sending: "info",
  confirmed: "success",
  reminder_scheduled: "info",
  arrived: "info",
  seated: "success",
  completed: "success",
  no_show: "danger",
  cancelled_by_customer: "neutral",
  cancelled_by_restaurant: "neutral",
  expired: "neutral",
};

export const TABLE_STATUS_TONES: Record<TableStatus, StatusTone> = {
  available: "success",
  reserved: "info",
  occupied: "warning",
  cleaning: "neutral",
  blocked: "danger",
  maintenance: "danger",
  merged: "neutral",
};

export const WAITLIST_STATUS_TONES: Record<WaitlistStatus, StatusTone> = {
  waiting: "warning",
  notified: "info",
  promoted: "success",
  cancelled: "neutral",
  expired: "neutral",
};

// --- Phase 10: Communication Hub, Operational Tasks & Notifications ---

export const CONVERSATION_STATUS_TONES: Record<ConversationStatus, StatusTone> = {
  open: "info",
  pending: "warning",
  waiting_on_customer: "warning",
  waiting_on_staff: "danger",
  snoozed: "neutral",
  resolved: "success",
  closed: "neutral",
  spam: "neutral",
};

export const CONVERSATION_PRIORITY_TONES: Record<ConversationPriority, StatusTone> = {
  low: "neutral",
  normal: "info",
  high: "warning",
  urgent: "danger",
};

export const SCHEDULED_MESSAGE_STATUS_TONES: Record<ScheduledMessageStatus, StatusTone> = {
  scheduled: "info",
  processing: "warning",
  sent: "success",
  cancelled: "neutral",
  failed: "danger",
};

export const TASK_STATUS_TONES: Record<TaskStatus, StatusTone> = {
  open: "info",
  in_progress: "warning",
  blocked: "danger",
  completed: "success",
  cancelled: "neutral",
};

export const TASK_PRIORITY_TONES: Record<TaskPriority, StatusTone> = {
  low: "neutral",
  normal: "info",
  high: "warning",
  urgent: "danger",
};

export const NOTIFICATION_PRIORITY_TONES: Record<NotificationPriority, StatusTone> = {
  low: "neutral",
  normal: "info",
  high: "warning",
  urgent: "danger",
};

/** Reservation `start_time`/`end_time` arrive as "HH:MM:SS" (no date, no
 * timezone conversion needed — it is already the restaurant's own local
 * wall-clock booking time, not a UTC instant). */
export function formatTime(value: string | null | undefined): string {
  if (!value) return "—";
  const [hoursStr, minutesStr = "00"] = value.split(":");
  const hours = Number(hoursStr);
  const period = hours >= 12 ? "PM" : "AM";
  const displayHours = hours % 12 === 0 ? 12 : hours % 12;
  return `${displayHours}:${minutesStr.padStart(2, "0")} ${period}`;
}
