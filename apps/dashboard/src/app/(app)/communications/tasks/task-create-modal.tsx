"use client";

import { useState } from "react";
import type { TaskPriority, TaskSource } from "@rkpr/contracts";

import { useCreateTask } from "@/lib/hooks/use-tasks";
import { useStaffList } from "@/lib/hooks/use-staff";
import { humanize } from "@/lib/crm-display";
import { ApiError } from "@/lib/api/errors";
import { Modal } from "@/components/modals/modal";
import { FormField } from "@/components/forms/form-field";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";

const SOURCES: TaskSource[] = [
  "manual",
  "reservation_followup",
  "order_issue",
  "lead_followup",
  "inventory_alert",
  "system",
];
const PRIORITIES: TaskPriority[] = ["low", "normal", "high", "urgent"];
const UNASSIGNED = "__unassigned";

export function TaskCreateModal({
  open,
  onOpenChange,
}: {
  open: boolean;
  onOpenChange: (open: boolean) => void;
}) {
  const createTask = useCreateTask();
  const { data: staff } = useStaffList({ page: 1, pageSize: 100, accountStatus: "active" });

  const [title, setTitle] = useState("");
  const [description, setDescription] = useState("");
  const [source, setSource] = useState<TaskSource>("manual");
  const [priority, setPriority] = useState<TaskPriority>("normal");
  const [dueAt, setDueAt] = useState("");
  const [assignedStaffId, setAssignedStaffId] = useState(UNASSIGNED);
  const [error, setError] = useState<string | null>(null);

  function reset() {
    setTitle("");
    setDescription("");
    setSource("manual");
    setPriority("normal");
    setDueAt("");
    setAssignedStaffId(UNASSIGNED);
    setError(null);
  }

  async function handleSubmit() {
    setError(null);
    try {
      await createTask.mutateAsync({
        title: title.trim(),
        description: description.trim() || null,
        source,
        priority,
        due_at: dueAt ? new Date(dueAt).toISOString() : null,
        assigned_staff_id: assignedStaffId === UNASSIGNED ? null : assignedStaffId,
      });
      reset();
      onOpenChange(false);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "The task could not be created.");
    }
  }

  return (
    <Modal
      open={open}
      onOpenChange={(next) => {
        if (!next) reset();
        onOpenChange(next);
      }}
      title="New task"
      footer={
        <>
          <Button variant="outline" onClick={() => onOpenChange(false)}>
            Cancel
          </Button>
          <Button disabled={!title.trim() || createTask.isPending} onClick={() => void handleSubmit()}>
            {createTask.isPending ? "Creating…" : "Create task"}
          </Button>
        </>
      }
    >
      <div className="flex flex-col gap-3">
        <FormField label="Title" htmlFor="task-title">
          <Input id="task-title" value={title} onChange={(e) => setTitle(e.target.value)} />
        </FormField>
        <FormField label="Description" htmlFor="task-description">
          <Textarea
            id="task-description"
            rows={3}
            value={description}
            onChange={(e) => setDescription(e.target.value)}
          />
        </FormField>
        <FormField label="Source" htmlFor="task-source">
          <Select value={source} onValueChange={(value) => setSource(value as TaskSource)}>
            <SelectTrigger id="task-source">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              {SOURCES.map((s) => (
                <SelectItem key={s} value={s}>
                  {humanize(s)}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </FormField>
        <FormField label="Priority" htmlFor="task-priority">
          <Select value={priority} onValueChange={(value) => setPriority(value as TaskPriority)}>
            <SelectTrigger id="task-priority">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              {PRIORITIES.map((p) => (
                <SelectItem key={p} value={p}>
                  {humanize(p)}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </FormField>
        <FormField label="Due at (optional)" htmlFor="task-due-at">
          <Input id="task-due-at" type="datetime-local" value={dueAt} onChange={(e) => setDueAt(e.target.value)} />
        </FormField>
        <FormField label="Assign to (optional)" htmlFor="task-assignee">
          <Select value={assignedStaffId} onValueChange={setAssignedStaffId}>
            <SelectTrigger id="task-assignee">
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
        </FormField>
        {error && (
          <p role="alert" className="text-destructive text-sm">
            {error}
          </p>
        )}
      </div>
    </Modal>
  );
}
