"use client";

import { useState } from "react";
import type { TaskStatus } from "@rkpr/contracts";

import { useAssignTask, useTaskDetail, useTransitionTask } from "@/lib/hooks/use-tasks";
import { useStaffList } from "@/lib/hooks/use-staff";
import { hasPermission, useCurrentUser } from "@/lib/hooks/use-current-user";
import { TASK_PRIORITY_TONES, TASK_STATUS_TONES, formatDateTime, humanize } from "@/lib/crm-display";
import { ApiError } from "@/lib/api/errors";
import { Drawer } from "@/components/modals/drawer";
import { StatusBadge } from "@/components/status-badge";
import { CardSkeleton } from "@/components/skeletons/card-skeleton";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";

const TRANSITIONS: Record<TaskStatus, TaskStatus[]> = {
  open: ["in_progress", "blocked", "completed", "cancelled"],
  in_progress: ["blocked", "completed", "cancelled", "open"],
  blocked: ["in_progress", "open", "cancelled"],
  completed: ["open"],
  cancelled: ["open"],
};
const UNASSIGNED = "__unassigned";

export function TaskDetailDrawer({
  taskId,
  onOpenChange,
}: {
  taskId: string | null;
  onOpenChange: (open: boolean) => void;
}) {
  const { data: currentUser } = useCurrentUser();
  const { data: task, isLoading } = useTaskDetail(taskId ?? undefined);
  const { data: staff } = useStaffList({ page: 1, pageSize: 100, accountStatus: "active" });
  const transition = useTransitionTask(taskId ?? "");
  const assign = useAssignTask(taskId ?? "");

  const [blockedReason, setBlockedReason] = useState("");
  const [completionNotes, setCompletionNotes] = useState("");
  const [error, setError] = useState<string | null>(null);

  const canUpdate = hasPermission(currentUser, "tasks.update");
  const canAssign = hasPermission(currentUser, "tasks.assign");

  async function applyTransition(target: TaskStatus) {
    setError(null);
    try {
      await transition.mutateAsync({
        target_status: target,
        blocked_reason: target === "blocked" ? blockedReason.trim() : undefined,
        completion_notes: target === "completed" ? completionNotes.trim() : undefined,
      });
      setBlockedReason("");
      setCompletionNotes("");
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "The task status could not be changed.");
    }
  }

  async function handleAssign(staffId: string) {
    setError(null);
    try {
      await assign.mutateAsync({ assigned_staff_id: staffId === UNASSIGNED ? null : staffId });
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "The task could not be assigned.");
    }
  }

  return (
    <Drawer
      open={taskId !== null}
      onOpenChange={onOpenChange}
      title={task ? task.title : "Task"}
      description={task ? task.task_number : undefined}
    >
      {isLoading || !task ? (
        <CardSkeleton />
      ) : (
        <div className="flex flex-col gap-4 py-2">
          <div className="flex gap-2">
            <StatusBadge label={humanize(task.priority)} tone={TASK_PRIORITY_TONES[task.priority]} />
            <StatusBadge label={humanize(task.status)} tone={TASK_STATUS_TONES[task.status]} />
          </div>

          {task.description && <p className="text-sm whitespace-pre-wrap">{task.description}</p>}

          <dl className="grid grid-cols-2 gap-3 text-sm">
            <div>
              <dt className="text-muted-foreground text-xs">Source</dt>
              <dd>{humanize(task.source)}</dd>
            </div>
            <div>
              <dt className="text-muted-foreground text-xs">Due</dt>
              <dd>{formatDateTime(task.due_at)}</dd>
            </div>
          </dl>

          {task.blocked_reason && (
            <p className="text-muted-foreground text-sm">Blocked: {task.blocked_reason}</p>
          )}
          {task.completion_notes && (
            <p className="text-muted-foreground text-sm">Completion notes: {task.completion_notes}</p>
          )}

          {canAssign && (
            <div>
              <p className="mb-1.5 text-sm font-medium">Assigned to</p>
              <Select
                value={task.assigned_staff_id ?? UNASSIGNED}
                onValueChange={(value) => void handleAssign(value)}
                disabled={assign.isPending}
              >
                <SelectTrigger>
                  <SelectValue placeholder="Unassigned" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value={UNASSIGNED}>Unassigned</SelectItem>
                  {(staff?.data ?? []).map((member) => (
                    <SelectItem key={member.id} value={member.id}>
                      {member.display_name}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
          )}

          {canUpdate && TRANSITIONS[task.status].length > 0 && (
            <div className="flex flex-col gap-2">
              <p className="text-sm font-medium">Change status</p>
              {TRANSITIONS[task.status].includes("blocked") && (
                <Textarea
                  placeholder="Reason if blocking…"
                  rows={2}
                  value={blockedReason}
                  onChange={(e) => setBlockedReason(e.target.value)}
                />
              )}
              {TRANSITIONS[task.status].includes("completed") && (
                <Textarea
                  placeholder="Completion notes (optional)…"
                  rows={2}
                  value={completionNotes}
                  onChange={(e) => setCompletionNotes(e.target.value)}
                />
              )}
              <div className="flex flex-wrap gap-2">
                {TRANSITIONS[task.status].map((target) => (
                  <Button
                    key={target}
                    size="sm"
                    variant={target === "cancelled" ? "destructive" : "default"}
                    disabled={
                      transition.isPending || (target === "blocked" && !blockedReason.trim())
                    }
                    onClick={() => void applyTransition(target)}
                  >
                    {humanize(target)}
                  </Button>
                ))}
              </div>
            </div>
          )}

          {error && (
            <p role="alert" className="text-destructive text-sm">
              {error}
            </p>
          )}
        </div>
      )}
    </Drawer>
  );
}
