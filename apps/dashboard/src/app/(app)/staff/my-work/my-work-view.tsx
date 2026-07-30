"use client";

import { useState } from "react";

import { useCurrentUser } from "@/lib/hooks/use-current-user";
import {
  useAvailabilityWindows,
  useCreateAvailabilityWindow,
  useLeaveRequests,
  useLeaveTypes,
  useShiftList,
  useSubmitLeaveRequest,
  useTrainingAssignments,
  useWithdrawLeaveRequest,
} from "@/lib/hooks/use-staff-operations";
import {
  LEAVE_STATUS_TONES,
  SHIFT_STATUS_TONES,
  TRAINING_ASSIGNMENT_STATUS_TONES,
  formatDate,
  formatDateTime,
  humanize,
} from "@/lib/crm-display";
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

export function MyWorkView() {
  const { data: currentUser } = useCurrentUser();
  const staffId = currentUser?.id;

  const { data: shifts } = useShiftList({ staffUserId: staffId });
  const { data: leaveTypes } = useLeaveTypes();
  const { data: leaveRequests } = useLeaveRequests({ staffUserId: staffId });
  const { data: trainingAssignments } = useTrainingAssignments({ staffUserId: staffId });
  const { data: availability } = useAvailabilityWindows(staffId);

  const submitLeave = useSubmitLeaveRequest();
  const withdrawLeave = useWithdrawLeaveRequest();
  const createAvailability = useCreateAvailabilityWindow(staffId ?? "");

  const [leaveTypeId, setLeaveTypeId] = useState("");
  const [startDate, setStartDate] = useState("");
  const [endDate, setEndDate] = useState("");
  const [error, setError] = useState<string | null>(null);

  const [availabilityDay, setAvailabilityDay] = useState("1");

  if (!staffId) {
    return <div className="p-6 text-sm text-zinc-500">Loading…</div>;
  }

  return (
    <div className="flex flex-1 flex-col gap-6 p-6">
      <PageHeader title="My work" description="Your own schedule, leave, training, and availability." />

      {error && <p className="text-sm text-red-600">{error}</p>}

      <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
        <SectionCard title="Upcoming shifts">
          <ul className="flex flex-col gap-2 text-sm">
            {(shifts ?? []).map((shift) => (
              <li key={shift.id} className="flex items-center justify-between gap-2">
                <span>
                  {formatDate(shift.shift_date)} · {formatDateTime(shift.start_at)} –{" "}
                  {formatDateTime(shift.end_at)}
                </span>
                <StatusBadge label={humanize(shift.status)} tone={SHIFT_STATUS_TONES[shift.status]} />
              </li>
            ))}
            {!shifts?.length && <li className="text-muted-foreground">No shifts scheduled.</li>}
          </ul>
        </SectionCard>

        <SectionCard title="My training">
          <ul className="flex flex-col gap-2 text-sm">
            {(trainingAssignments ?? []).map((assignment) => (
              <li key={assignment.id} className="flex items-center justify-between gap-2">
                <span>Due {formatDate(assignment.due_at)}</span>
                <StatusBadge
                  label={humanize(assignment.status)}
                  tone={TRAINING_ASSIGNMENT_STATUS_TONES[assignment.status]}
                />
              </li>
            ))}
            {!trainingAssignments?.length && (
              <li className="text-muted-foreground">No training assigned.</li>
            )}
          </ul>
        </SectionCard>

        <SectionCard
          title="My leave"
          description="Submit a new request or withdraw a pending one."
        >
          <div className="mb-3 flex flex-wrap items-end gap-2">
            <Select value={leaveTypeId} onValueChange={setLeaveTypeId}>
              <SelectTrigger className="w-40">
                <SelectValue placeholder="Leave type" />
              </SelectTrigger>
              <SelectContent>
                {(leaveTypes ?? []).map((type) => (
                  <SelectItem key={type.id} value={type.id}>
                    {type.name}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
            <Input type="date" value={startDate} onChange={(e) => setStartDate(e.target.value)} />
            <Input type="date" value={endDate} onChange={(e) => setEndDate(e.target.value)} />
            <Button
              size="sm"
              disabled={!leaveTypeId || !startDate || !endDate || submitLeave.isPending}
              onClick={() =>
                submitLeave.mutate(
                  { leave_type_id: leaveTypeId, start_date: startDate, end_date: endDate },
                  {
                    onSuccess: () => {
                      setStartDate("");
                      setEndDate("");
                      setError(null);
                    },
                    onError: (err) =>
                      setError(err instanceof ApiError ? err.message : "Could not submit leave request."),
                  },
                )
              }
            >
              Request
            </Button>
          </div>
          <ul className="flex flex-col gap-2 text-sm">
            {(leaveRequests ?? []).map((request) => (
              <li key={request.id} className="flex items-center justify-between gap-2">
                <span>
                  {formatDate(request.start_date)} – {formatDate(request.end_date)}
                </span>
                <div className="flex items-center gap-2">
                  <StatusBadge
                    label={humanize(request.status)}
                    tone={LEAVE_STATUS_TONES[request.status]}
                  />
                  {(request.status === "draft" || request.status === "submitted") && (
                    <Button
                      size="sm"
                      variant="ghost"
                      disabled={withdrawLeave.isPending}
                      onClick={() =>
                        withdrawLeave.mutate(request.id, {
                          onError: (err) =>
                            setError(err instanceof ApiError ? err.message : "Could not withdraw request."),
                        })
                      }
                    >
                      Withdraw
                    </Button>
                  )}
                </div>
              </li>
            ))}
            {!leaveRequests?.length && (
              <li className="text-muted-foreground">No leave requests yet.</li>
            )}
          </ul>
        </SectionCard>

        <SectionCard title="My availability" description="Recurring weekly availability windows.">
          <div className="mb-3 flex items-end gap-2">
            <Select value={availabilityDay} onValueChange={setAvailabilityDay}>
              <SelectTrigger className="w-40">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {["Sunday", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"].map(
                  (day, index) => (
                    <SelectItem key={day} value={String(index)}>
                      {day}
                    </SelectItem>
                  ),
                )}
              </SelectContent>
            </Select>
            <Button
              size="sm"
              disabled={createAvailability.isPending}
              onClick={() =>
                createAvailability.mutate(
                  { availability_type: "available", day_of_week: Number(availabilityDay) },
                  { onError: (err) => setError(err instanceof ApiError ? err.message : "Could not save.") },
                )
              }
            >
              Add
            </Button>
          </div>
          <ul className="flex flex-col gap-2 text-sm">
            {(availability ?? []).map((window) => (
              <li key={window.id} className="flex items-center justify-between gap-2">
                <span>
                  {window.day_of_week !== null
                    ? [
                        "Sunday",
                        "Monday",
                        "Tuesday",
                        "Wednesday",
                        "Thursday",
                        "Friday",
                        "Saturday",
                      ][window.day_of_week]
                    : formatDate(window.specific_date)}
                </span>
                <StatusBadge label={humanize(window.availability_type)} tone="neutral" />
              </li>
            ))}
            {!availability?.length && (
              <li className="text-muted-foreground">No availability recorded.</li>
            )}
          </ul>
        </SectionCard>
      </div>
    </div>
  );
}
