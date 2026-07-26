import type {
  CustomerStatus,
  FollowUpStatus,
  LeadPriority,
  LeadStatus,
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
