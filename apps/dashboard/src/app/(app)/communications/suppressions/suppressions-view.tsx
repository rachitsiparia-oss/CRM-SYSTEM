"use client";

import { useMemo, useState } from "react";
import type { ColumnDef } from "@tanstack/react-table";
import type { CommunicationSuppression } from "@rkpr/contracts";
import { Plus } from "lucide-react";

import {
  useLiftSuppression,
  useSuppressions,
} from "@/lib/hooks/use-communications";
import { hasPermission, useCurrentUser } from "@/lib/hooks/use-current-user";
import { formatDateTime, humanize } from "@/lib/crm-display";
import { PageHeader } from "@/components/page-header";
import { DataTable } from "@/components/data-table/data-table";
import { StatusBadge } from "@/components/status-badge";
import { Button } from "@/components/ui/button";
import { SuppressionCreateModal } from "./suppression-create-modal";

export function SuppressionsView() {
  const { data: currentUser } = useCurrentUser();
  const [showCreate, setShowCreate] = useState(false);
  const { data, isLoading } = useSuppressions(true);
  const liftSuppression = useLiftSuppression();

  const canManage = hasPermission(currentUser, "communications.suppressions.manage");

  const columns = useMemo<ColumnDef<CommunicationSuppression, unknown>[]>(
    () => [
      {
        id: "destination",
        header: "Destination",
        enableSorting: false,
        cell: ({ row }) => (
          <div className="flex flex-col">
            <span className="text-sm">{row.original.destination_value}</span>
            <span className="text-muted-foreground text-xs">
              {humanize(row.original.destination_type)}
            </span>
          </div>
        ),
      },
      {
        id: "reason",
        header: "Reason",
        enableSorting: false,
        cell: ({ row }) => <span className="text-sm">{humanize(row.original.reason)}</span>,
      },
      {
        id: "scope",
        header: "Scope",
        enableSorting: false,
        cell: ({ row }) => (
          <StatusBadge label={humanize(row.original.scope)} tone="neutral" />
        ),
      },
      {
        id: "created_at",
        header: "Suppressed since",
        enableSorting: false,
        cell: ({ row }) => <span className="text-sm">{formatDateTime(row.original.created_at)}</span>,
      },
      {
        id: "actions",
        header: "",
        enableSorting: false,
        cell: ({ row }) =>
          canManage ? (
            <Button
              size="sm"
              variant="outline"
              disabled={liftSuppression.isPending}
              onClick={() => void liftSuppression.mutateAsync(row.original.id)}
            >
              Lift
            </Button>
          ) : null,
      },
    ],
    [canManage, liftSuppression],
  );

  return (
    <div className="flex flex-1 flex-col gap-4 p-6">
      <PageHeader
        title="Suppression list"
        description="Destinations that must never receive an outbound message — bounces, complaints, and manual blocks."
        actions={
          canManage ? (
            <Button onClick={() => setShowCreate(true)}>
              <Plus className="size-4" />
              Add suppression
            </Button>
          ) : null
        }
      />

      <DataTable
        columns={columns}
        data={data?.data ?? []}
        getRowId={(row) => row.id}
        loading={isLoading}
        emptyTitle="No active suppressions"
        emptyDescription="Destinations you block or that bounce will appear here."
      />

      <SuppressionCreateModal open={showCreate} onOpenChange={setShowCreate} />
    </div>
  );
}
