"use client";

import { useState } from "react";
import type { RecoveryAction } from "@rkpr/contracts";

import {
  useApproveRecoveryAction,
  useComplaintRecoveryActions,
  useExecuteRecoveryAction,
  useRejectRecoveryAction,
  useReverseRecoveryAction,
} from "@/lib/hooks/use-service-recovery";
import { hasPermission, useCurrentUser } from "@/lib/hooks/use-current-user";
import { RECOVERY_STATUS_TONES, formatDateTime, formatMinorUnits, humanize } from "@/lib/crm-display";
import { ApiError } from "@/lib/api/errors";
import { SectionCard } from "@/components/section-card";
import { StatusBadge } from "@/components/status-badge";
import { Button } from "@/components/ui/button";
import { ProposeRecoveryActionModal } from "./propose-recovery-action-modal";

export function RecoveryActionsPanel({ complaintId }: { complaintId: string }) {
  const { data: currentUser } = useCurrentUser();
  const { data } = useComplaintRecoveryActions(complaintId, { page: 1, pageSize: 20 });
  const [showPropose, setShowPropose] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const canPropose = hasPermission(currentUser, "recovery.propose");
  const canApprove = hasPermission(currentUser, "recovery.approve");
  const canReject = hasPermission(currentUser, "recovery.reject");
  const canExecute = hasPermission(currentUser, "recovery.execute");
  const canReverse = hasPermission(currentUser, "recovery.reverse");

  const actions = data?.data ?? [];

  return (
    <SectionCard
      title="Service recovery"
      description="Compensation proposed for this complaint, routed through approval and executed via the loyalty/credit/order modules."
      actions={
        canPropose ? (
          <Button size="sm" onClick={() => setShowPropose(true)}>
            Propose action
          </Button>
        ) : null
      }
    >
      {error && (
        <p role="alert" className="text-destructive mb-3 text-sm">
          {error}
        </p>
      )}
      {actions.length === 0 ? (
        <p className="text-muted-foreground text-sm">No recovery actions proposed yet.</p>
      ) : (
        <ul className="flex flex-col gap-3">
          {actions.map((action) => (
            <RecoveryActionRow
              key={action.id}
              action={action}
              complaintId={complaintId}
              canApprove={canApprove}
              canReject={canReject}
              canExecute={canExecute}
              canReverse={canReverse}
              onError={setError}
            />
          ))}
        </ul>
      )}

      <ProposeRecoveryActionModal
        complaintId={complaintId}
        open={showPropose}
        onOpenChange={setShowPropose}
      />
    </SectionCard>
  );
}

function RecoveryActionRow({
  action,
  complaintId,
  canApprove,
  canReject,
  canExecute,
  canReverse,
  onError,
}: {
  action: RecoveryAction;
  complaintId: string;
  canApprove: boolean;
  canReject: boolean;
  canExecute: boolean;
  canReverse: boolean;
  onError: (message: string) => void;
}) {
  const approve = useApproveRecoveryAction(action.id, complaintId);
  const reject = useRejectRecoveryAction(action.id, complaintId);
  const execute = useExecuteRecoveryAction(action.id, complaintId);
  const reverse = useReverseRecoveryAction(action.id, complaintId);

  const onMutationError = (err: unknown) =>
    onError(err instanceof ApiError ? err.message : "Could not update this action.");

  return (
    <li className="flex flex-col gap-2 rounded-md border p-3">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div>
          <p className="text-sm font-medium">{humanize(action.recovery_type)}</p>
          <p className="text-muted-foreground text-xs">
            {action.value_minor !== null
              ? formatMinorUnits(action.value_minor)
              : action.points !== null
                ? `${action.points} points`
                : "No value"}
          </p>
        </div>
        <StatusBadge label={humanize(action.status)} tone={RECOVERY_STATUS_TONES[action.status]} />
      </div>
      <p className="text-sm">{action.description}</p>
      <p className="text-muted-foreground text-xs">
        Proposed {formatDateTime(action.proposed_at)}
        {action.execution_reference_type &&
          ` · Executed via ${humanize(action.execution_reference_type)}`}
      </p>
      <div className="flex flex-wrap gap-2">
        {action.status === "approval_required" && canApprove && (
          <Button
            size="sm"
            variant="outline"
            onClick={() => approve.mutate(undefined, { onError: onMutationError })}
          >
            Approve
          </Button>
        )}
        {action.status === "approval_required" && canReject && (
          <Button
            size="sm"
            variant="outline"
            onClick={() =>
              reject.mutate(
                { reason: "Rejected from complaint workspace." },
                { onError: onMutationError },
              )
            }
          >
            Reject
          </Button>
        )}
        {(action.status === "proposed" || action.status === "approved") && canExecute && (
          <Button size="sm" onClick={() => execute.mutate(undefined, { onError: onMutationError })}>
            Execute
          </Button>
        )}
        {action.status === "completed" && canReverse && (
          <Button
            size="sm"
            variant="outline"
            onClick={() =>
              reverse.mutate(
                { reason: "Reversed from complaint workspace." },
                { onError: onMutationError },
              )
            }
          >
            Reverse
          </Button>
        )}
      </div>
    </li>
  );
}
