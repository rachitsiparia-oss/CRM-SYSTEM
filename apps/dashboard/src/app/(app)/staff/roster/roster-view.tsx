"use client";

import { useState } from "react";

import {
  useCreateShiftTemplate,
  useDecideShiftChangeRequest,
  usePublishShift,
  useShiftChangeRequests,
  useShiftList,
  useShiftTemplates,
} from "@/lib/hooks/use-staff-operations";
import { useStaffList } from "@/lib/hooks/use-staff";
import { hasPermission, useCurrentUser } from "@/lib/hooks/use-current-user";
import { SHIFT_STATUS_TONES, formatDate, formatDateTime, humanize } from "@/lib/crm-display";
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

export function RosterView() {
  const { data: currentUser } = useCurrentUser();
  const canManage = hasPermission(currentUser, "staff.shifts.manage");

  const [staffFilter, setStaffFilter] = useState(ALL);
  const [error, setError] = useState<string | null>(null);

  const { data: staffPage } = useStaffList({ page: 1, pageSize: 100 });
  const staffOptions = staffPage?.data ?? [];

  const { data: shifts, isLoading: shiftsLoading } = useShiftList({
    staffUserId: staffFilter === ALL ? undefined : staffFilter,
  });
  const { data: templates } = useShiftTemplates();
  const { data: changeRequests } = useShiftChangeRequests();

  const publishShift = usePublishShift();
  const decideChangeRequest = useDecideShiftChangeRequest();
  const createTemplate = useCreateShiftTemplate();

  const [templateName, setTemplateName] = useState("");
  const [templateStart, setTemplateStart] = useState("09:00");
  const [templateEnd, setTemplateEnd] = useState("17:00");

  const staffName = (id: string) =>
    staffOptions.find((s) => s.id === id)?.display_name ?? "Unknown staff";

  return (
    <div className="flex flex-1 flex-col gap-6 p-6">
      <PageHeader title="Shifts & roster" description="Shift templates, published roster, and change requests." />

      {error && <p className="text-sm text-red-600">{error}</p>}

      <Tabs defaultValue="roster">
        <TabsList>
          <TabsTrigger value="roster">Roster</TabsTrigger>
          <TabsTrigger value="templates">Templates</TabsTrigger>
          <TabsTrigger value="requests">Change requests</TabsTrigger>
        </TabsList>

        <TabsContent value="roster" className="flex flex-col gap-4 pt-4">
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

          <SectionCard title="Shifts">
            <ul className="flex flex-col gap-2 text-sm">
              {shiftsLoading && <li className="text-muted-foreground">Loading…</li>}
              {(shifts ?? []).map((shift) => (
                <li key={shift.id} className="flex items-center justify-between gap-2">
                  <span>
                    {staffName(shift.staff_user_id)} · {formatDate(shift.shift_date)} ·{" "}
                    {formatDateTime(shift.start_at)} – {formatDateTime(shift.end_at)}
                  </span>
                  <div className="flex items-center gap-2">
                    <StatusBadge label={humanize(shift.status)} tone={SHIFT_STATUS_TONES[shift.status]} />
                    {canManage && !shift.is_published && (
                      <Button
                        size="sm"
                        variant="outline"
                        disabled={publishShift.isPending}
                        onClick={() =>
                          publishShift.mutate(shift.id, {
                            onError: (err) =>
                              setError(err instanceof ApiError ? err.message : "Could not publish shift."),
                          })
                        }
                      >
                        Publish
                      </Button>
                    )}
                  </div>
                </li>
              ))}
              {!shiftsLoading && !shifts?.length && (
                <li className="text-muted-foreground">No shifts found.</li>
              )}
            </ul>
          </SectionCard>
        </TabsContent>

        <TabsContent value="templates" className="flex flex-col gap-4 pt-4">
          <SectionCard title="Shift templates" description="Reusable start/end time patterns.">
            {canManage && (
              <div className="mb-3 flex flex-wrap items-end gap-2">
                <Input
                  placeholder="Template name"
                  value={templateName}
                  onChange={(e) => setTemplateName(e.target.value)}
                  className="w-48"
                />
                <Input
                  type="time"
                  value={templateStart}
                  onChange={(e) => setTemplateStart(e.target.value)}
                />
                <Input type="time" value={templateEnd} onChange={(e) => setTemplateEnd(e.target.value)} />
                <Button
                  size="sm"
                  disabled={!templateName || createTemplate.isPending}
                  onClick={() =>
                    createTemplate.mutate(
                      { name: templateName, start_time: templateStart, end_time: templateEnd },
                      {
                        onSuccess: () => setTemplateName(""),
                        onError: (err) =>
                          setError(err instanceof ApiError ? err.message : "Could not create template."),
                      },
                    )
                  }
                >
                  Add template
                </Button>
              </div>
            )}
            <ul className="flex flex-col gap-2 text-sm">
              {(templates ?? []).map((template) => (
                <li key={template.id} className="flex items-center justify-between gap-2">
                  <span>{template.name}</span>
                  <span className="text-muted-foreground">
                    {template.start_time} – {template.end_time}
                  </span>
                </li>
              ))}
              {!templates?.length && <li className="text-muted-foreground">No templates yet.</li>}
            </ul>
          </SectionCard>
        </TabsContent>

        <TabsContent value="requests" className="flex flex-col gap-4 pt-4">
          <SectionCard title="Shift change requests">
            <ul className="flex flex-col gap-2 text-sm">
              {(changeRequests ?? []).map((request) => (
                <li key={request.id} className="flex items-center justify-between gap-2">
                  <span>
                    {humanize(request.request_type)}
                    {request.reason ? ` — ${request.reason}` : ""}
                  </span>
                  <div className="flex items-center gap-2">
                    <StatusBadge label={humanize(request.status)} tone="neutral" />
                    {canManage && request.status === "pending" && (
                      <>
                        <Button
                          size="sm"
                          variant="outline"
                          disabled={decideChangeRequest.isPending}
                          onClick={() =>
                            decideChangeRequest.mutate(
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
                          disabled={decideChangeRequest.isPending}
                          onClick={() =>
                            decideChangeRequest.mutate(
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
              {!changeRequests?.length && (
                <li className="text-muted-foreground">No change requests.</li>
              )}
            </ul>
          </SectionCard>
        </TabsContent>
      </Tabs>
    </div>
  );
}
