"use client";

import { useState } from "react";
import type { Conversation, ConversationPriority } from "@rkpr/contracts";

import {
  useAssignConversation,
  useSetConversationPriority,
} from "@/lib/hooks/use-communications";
import { useStaffList } from "@/lib/hooks/use-staff";
import { hasPermission, useCurrentUser } from "@/lib/hooks/use-current-user";
import { humanize } from "@/lib/crm-display";
import { ApiError } from "@/lib/api/errors";
import { SectionCard } from "@/components/section-card";
import { FormField } from "@/components/forms/form-field";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";

const UNASSIGNED = "__unassigned";
const PRIORITIES: ConversationPriority[] = ["low", "normal", "high", "urgent"];

export function ConversationAssignControl({ conversation }: { conversation: Conversation }) {
  const { data: currentUser } = useCurrentUser();
  const canAssign = hasPermission(currentUser, "communications.assign");
  const canManagePriority = hasPermission(currentUser, "communications.priority.manage");

  const { data: staff } = useStaffList({ page: 1, pageSize: 100, accountStatus: "active" });
  const assign = useAssignConversation(conversation.id);
  const setPriority = useSetConversationPriority(conversation.id);
  const [error, setError] = useState<string | null>(null);

  async function handleAssign(staffId: string) {
    setError(null);
    try {
      await assign.mutateAsync({ assignee_id: staffId === UNASSIGNED ? null : staffId });
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "This conversation could not be assigned.");
    }
  }

  async function handlePriority(priority: ConversationPriority) {
    setError(null);
    try {
      await setPriority.mutateAsync({ priority });
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "The priority could not be changed.");
    }
  }

  return (
    <SectionCard title="Assignment & priority">
      <div className="flex flex-wrap gap-4">
        <FormField label="Assigned to" htmlFor="conversation-assignee" className="min-w-56">
          <Select
            value={conversation.assigned_staff_id ?? UNASSIGNED}
            onValueChange={(value) => void handleAssign(value)}
            disabled={!canAssign || assign.isPending}
          >
            <SelectTrigger id="conversation-assignee">
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

        <FormField label="Priority" htmlFor="conversation-priority" className="min-w-40">
          <Select
            value={conversation.priority}
            onValueChange={(value) => void handlePriority(value as ConversationPriority)}
            disabled={!canManagePriority || setPriority.isPending}
          >
            <SelectTrigger id="conversation-priority">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              {PRIORITIES.map((priority) => (
                <SelectItem key={priority} value={priority}>
                  {humanize(priority)}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </FormField>
      </div>
      {error && (
        <p role="alert" className="text-destructive mt-3 text-sm">
          {error}
        </p>
      )}
    </SectionCard>
  );
}
