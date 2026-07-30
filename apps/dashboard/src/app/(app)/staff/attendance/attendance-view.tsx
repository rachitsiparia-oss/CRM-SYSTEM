"use client";

import { useState } from "react";

import type { AttendanceStatus } from "@rkpr/contracts";

import { useAttendanceList, useRecordAttendance } from "@/lib/hooks/use-staff-operations";
import { useStaffList } from "@/lib/hooks/use-staff";
import { hasPermission, useCurrentUser } from "@/lib/hooks/use-current-user";
import { ATTENDANCE_STATUS_TONES, formatDate, formatDateTime, humanize } from "@/lib/crm-display";
import { ApiError } from "@/lib/api/errors";
import { PageHeader } from "@/components/page-header";
import { SectionCard } from "@/components/section-card";
import { StatusBadge } from "@/components/status-badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";

const ALL = "__all";
const ATTENDANCE_STATUSES = ["present", "absent", "late", "half_day", "on_leave", "holiday"];

export function AttendanceView() {
  const { data: currentUser } = useCurrentUser();
  const canManage = hasPermission(currentUser, "staff.attendance.manage");

  const [staffFilter, setStaffFilter] = useState(ALL);
  const [error, setError] = useState<string | null>(null);

  const { data: staffPage } = useStaffList({ page: 1, pageSize: 100 });
  const staffOptions = staffPage?.data ?? [];

  const { data: records, isLoading } = useAttendanceList({
    staffUserId: staffFilter === ALL ? undefined : staffFilter,
  });
  const recordAttendance = useRecordAttendance();

  const [formStaffId, setFormStaffId] = useState("");
  const [formDate, setFormDate] = useState("");
  const [formStatus, setFormStatus] = useState("present");

  const staffName = (id: string) =>
    staffOptions.find((s) => s.id === id)?.display_name ?? "Unknown staff";

  return (
    <div className="flex flex-1 flex-col gap-6 p-6">
      <PageHeader title="Attendance" description="Manual and roster-derived attendance records." />

      {error && <p className="text-sm text-red-600">{error}</p>}

      <div className="w-56">
        <Select value={staffFilter} onValueChange={setStaffFilter}>
          <SelectTrigger aria-label="Filter by staff member">
            <SelectValue placeholder="All staff" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value={ALL}>All staff</SelectItem>
            {staffOptions.map((s) => (
              <SelectItem key={s.id} value={s.id}>
                {s.display_name}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>

      {canManage && (
        <SectionCard title="Record attendance">
          <div className="flex flex-wrap items-end gap-2">
            <Select value={formStaffId} onValueChange={setFormStaffId}>
              <SelectTrigger className="w-48" aria-label="Staff member">
                <SelectValue placeholder="Staff member" />
              </SelectTrigger>
              <SelectContent>
                {staffOptions.map((s) => (
                  <SelectItem key={s.id} value={s.id}>
                    {s.display_name}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
            <Input type="date" value={formDate} onChange={(e) => setFormDate(e.target.value)} />
            <Select value={formStatus} onValueChange={setFormStatus}>
              <SelectTrigger className="w-40" aria-label="Status">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {ATTENDANCE_STATUSES.map((status) => (
                  <SelectItem key={status} value={status}>
                    {humanize(status)}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
            <Button
              size="sm"
              disabled={!formStaffId || !formDate || recordAttendance.isPending}
              onClick={() =>
                recordAttendance.mutate(
                  {
                    staff_user_id: formStaffId,
                    attendance_date: formDate,
                    status: formStatus as AttendanceStatus,
                  },
                  {
                    onSuccess: () => setFormDate(""),
                    onError: (err) =>
                      setError(err instanceof ApiError ? err.message : "Could not record attendance."),
                  },
                )
              }
            >
              Record
            </Button>
          </div>
        </SectionCard>
      )}

      <SectionCard title="Records">
        <ul className="flex flex-col gap-2 text-sm">
          {isLoading && <li className="text-muted-foreground">Loading…</li>}
          {(records ?? []).map((record) => (
            <li key={record.id} className="flex items-center justify-between gap-2">
              <span>
                {staffName(record.staff_user_id)} · {formatDate(record.attendance_date)}
                {record.actual_check_in_at ? ` · in ${formatDateTime(record.actual_check_in_at)}` : ""}
                {record.actual_check_out_at ? ` · out ${formatDateTime(record.actual_check_out_at)}` : ""}
              </span>
              <div className="flex items-center gap-2">
                {record.late_minutes > 0 && (
                  <span className="text-muted-foreground text-xs">{record.late_minutes}m late</span>
                )}
                <StatusBadge
                  label={humanize(record.status)}
                  tone={ATTENDANCE_STATUS_TONES[record.status]}
                />
              </div>
            </li>
          ))}
          {!isLoading && !records?.length && (
            <li className="text-muted-foreground">No attendance records found.</li>
          )}
        </ul>
      </SectionCard>
    </div>
  );
}
