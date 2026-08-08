"use client";

import { useState } from "react";

import { useCreateLeaveType, useDecideLeaveRequest, useLeaveRequests, useLeaveTypes } from "@/lib/hooks/use-staff-operations";
import { useStaffList } from "@/lib/hooks/use-staff";
import { hasPermission, useCurrentUser } from "@/lib/hooks/use-current-user";
import { LEAVE_STATUS_TONES, formatDate, humanize } from "@/lib/crm-display";
import { ApiError } from "@/lib/api/errors";
import { PageHeader } from "@/components/page-header";
import { SectionCard } from "@/components/section-card";
import { StatusBadge } from "@/components/status-badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";

const ALL = "__all";
const STATUSES = ["draft", "submitted", "approved", "rejected", "cancelled", "withdrawn"];

export function LeaveView() {
  const { data: currentUser } = useCurrentUser();
  const canDecide = hasPermission(currentUser, "staff.leave.approve");
  const canManageTypes = canDecide;

  const [statusFilter, setStatusFilter] = useState("submitted");
  const [error, setError] = useState<string | null>(null);

  const { data: staffPage } = useStaffList({ page: 1, pageSize: 100 });
  const staffOptions = staffPage?.data ?? [];

  const { data: requests, isLoading } = useLeaveRequests({
    status: statusFilter === ALL ? undefined : statusFilter,
  });
  const { data: leaveTypes } = useLeaveTypes();

  const decideRequest = useDecideLeaveRequest();
  const createLeaveType = useCreateLeaveType();

  const [typeName, setTypeName] = useState("");
  const [typeCode, setTypeCode] = useState("");

  const staffName = (id: string) =>
    staffOptions.find((s) => s.id === id)?.display_name ?? "Unknown staff";
  const leaveTypeName = (id: string) => leaveTypes?.find((t) => t.id === id)?.name ?? "Leave";

  return (
    <div className="flex flex-1 flex-col gap-6 p-6">
      <PageHeader title="Leave" description="Leave requests and leave type configuration." />

      {error && <p className="text-sm text-destructive">{error}</p>}

      <Tabs defaultValue="requests">
        <TabsList>
          <TabsTrigger value="requests">Requests</TabsTrigger>
          <TabsTrigger value="types">Leave types</TabsTrigger>
        </TabsList>

        <TabsContent value="requests" className="flex flex-col gap-4 pt-4">
          <div className="w-48">
            <Select value={statusFilter} onValueChange={setStatusFilter}>
              <SelectTrigger aria-label="Filter by status">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value={ALL}>All statuses</SelectItem>
                {STATUSES.map((status) => (
                  <SelectItem key={status} value={status}>
                    {humanize(status)}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          <SectionCard title="Leave requests">
            <ul className="flex flex-col gap-2 text-sm">
              {isLoading && <li className="text-muted-foreground">Loading…</li>}
              {(requests ?? []).map((request) => (
                <li key={request.id} className="flex items-center justify-between gap-2">
                  <span>
                    {staffName(request.staff_user_id)} · {leaveTypeName(request.leave_type_id)} ·{" "}
                    {formatDate(request.start_date)} – {formatDate(request.end_date)}
                  </span>
                  <div className="flex items-center gap-2">
                    <StatusBadge
                      label={humanize(request.status)}
                      tone={LEAVE_STATUS_TONES[request.status]}
                    />
                    {canDecide && request.status === "submitted" && (
                      <>
                        <Button
                          size="sm"
                          variant="outline"
                          disabled={decideRequest.isPending}
                          onClick={() =>
                            decideRequest.mutate(
                              { requestId: request.id, approve: true },
                              {
                                onError: (err) =>
                                  setError(err instanceof ApiError ? err.message : "Could not decide request."),
                              },
                            )
                          }
                        >
                          Approve
                        </Button>
                        <Button
                          size="sm"
                          variant="ghost"
                          disabled={decideRequest.isPending}
                          onClick={() =>
                            decideRequest.mutate(
                              { requestId: request.id, approve: false },
                              {
                                onError: (err) =>
                                  setError(err instanceof ApiError ? err.message : "Could not decide request."),
                              },
                            )
                          }
                        >
                          Reject
                        </Button>
                      </>
                    )}
                  </div>
                </li>
              ))}
              {!isLoading && !requests?.length && (
                <li className="text-muted-foreground">No leave requests found.</li>
              )}
            </ul>
          </SectionCard>
        </TabsContent>

        <TabsContent value="types" className="flex flex-col gap-4 pt-4">
          <SectionCard title="Leave types">
            {canManageTypes && (
              <div className="mb-3 flex items-end gap-2">
                <Input placeholder="Name" value={typeName} onChange={(e) => setTypeName(e.target.value)} />
                <Input placeholder="Code" value={typeCode} onChange={(e) => setTypeCode(e.target.value)} />
                <Button
                  size="sm"
                  disabled={!typeName || !typeCode || createLeaveType.isPending}
                  onClick={() =>
                    createLeaveType.mutate(
                      { name: typeName, code: typeCode },
                      {
                        onSuccess: () => {
                          setTypeName("");
                          setTypeCode("");
                        },
                        onError: (err) =>
                          setError(err instanceof ApiError ? err.message : "Could not create leave type."),
                      },
                    )
                  }
                >
                  Add type
                </Button>
              </div>
            )}
            <ul className="flex flex-col gap-2 text-sm">
              {(leaveTypes ?? []).map((type) => (
                <li key={type.id} className="flex items-center justify-between gap-2">
                  <span>
                    {type.name} <span className="text-muted-foreground">({type.code})</span>
                  </span>
                  <span className="text-muted-foreground text-xs">{type.is_paid ? "Paid" : "Unpaid"}</span>
                </li>
              ))}
              {!leaveTypes?.length && <li className="text-muted-foreground">No leave types yet.</li>}
            </ul>
          </SectionCard>
        </TabsContent>
      </Tabs>
    </div>
  );
}
