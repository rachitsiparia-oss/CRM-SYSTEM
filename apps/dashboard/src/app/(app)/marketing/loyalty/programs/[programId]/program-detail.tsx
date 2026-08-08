"use client";

import { useMemo, useState } from "react";
import Link from "next/link";
import type { ColumnDef } from "@tanstack/react-table";
import type { LoyaltyProgramStatus, LoyaltyTier } from "@rkpr/contracts";

import {
  useLoyaltyPrograms,
  useLoyaltyTiers,
  useTransitionLoyaltyProgram,
} from "@/lib/hooks/use-loyalty";
import { hasPermission, useCurrentUser } from "@/lib/hooks/use-current-user";
import { LOYALTY_PROGRAM_STATUS_TONES, formatMinorUnits, humanize } from "@/lib/crm-display";
import { ApiError } from "@/lib/api/errors";
import { StatusBadge } from "@/components/status-badge";
import { Button } from "@/components/ui/button";
import { DataTable } from "@/components/data-table/data-table";
import { SectionCard } from "@/components/section-card";
import { ErrorState } from "@/components/error-state";
import { Plus } from "lucide-react";
import { CreateTierModal } from "./create-tier-modal";

const PROGRAM_TRANSITIONS: Record<LoyaltyProgramStatus, LoyaltyProgramStatus[]> = {
  draft: ["active", "archived"],
  active: ["paused", "archived"],
  paused: ["active", "archived"],
  archived: [],
};

export function ProgramDetail({ programId }: { programId: string }) {
  const { data: currentUser } = useCurrentUser();
  const { data: programs, isLoading, isError, refetch } = useLoyaltyPrograms();
  const { data: tiers, isLoading: tiersLoading } = useLoyaltyTiers(programId);
  const transitionProgram = useTransitionLoyaltyProgram(programId);

  const [error, setError] = useState<string | null>(null);
  const [showCreateTier, setShowCreateTier] = useState(false);

  const program = programs?.find((p) => p.id === programId);
  const canManage = hasPermission(currentUser, "loyalty.manage");
  const canManageTiers = hasPermission(currentUser, "loyalty.tiers.manage");

  const tierColumns = useMemo<ColumnDef<LoyaltyTier, unknown>[]>(
    () => [
      {
        id: "name",
        header: "Tier",
        enableSorting: false,
        cell: ({ row }) => (
          <div className="flex flex-col">
            <span className="font-medium">{row.original.name}</span>
            <span className="text-muted-foreground text-xs">{row.original.code}</span>
          </div>
        ),
      },
      {
        id: "rank",
        header: "Rank",
        enableSorting: false,
        cell: ({ row }) => <span className="text-sm">{row.original.rank}</span>,
      },
      {
        id: "qualification",
        header: "Qualification",
        enableSorting: false,
        cell: ({ row }) => (
          <span className="text-sm">
            {humanize(row.original.qualification_metric)} ≥ {row.original.threshold}
          </span>
        ),
      },
      {
        id: "multiplier",
        header: "Points multiplier",
        enableSorting: false,
        cell: ({ row }) => <span className="text-sm">{row.original.points_multiplier}×</span>,
      },
      {
        id: "status",
        header: "Active",
        enableSorting: false,
        cell: ({ row }) => (
          <StatusBadge
            label={row.original.is_active ? "Active" : "Inactive"}
            tone={row.original.is_active ? "success" : "neutral"}
          />
        ),
      },
    ],
    [],
  );

  if (isLoading) return <div className="p-6 text-sm text-muted-foreground">Loading…</div>;
  if (isError || !program) {
    return (
      <div className="p-6">
        <ErrorState title="Could not load this program" onRetry={() => void refetch()} />
      </div>
    );
  }

  const availableTransitions = PROGRAM_TRANSITIONS[program.status];

  return (
    <div className="flex flex-1 flex-col gap-6 p-6">
      <div>
        <Link href="/marketing/loyalty" className="text-sm text-muted-foreground hover:underline">
          ← Loyalty
        </Link>
        <div className="mt-2 flex flex-wrap items-center gap-3">
          <h1 className="text-lg font-semibold">{program.name}</h1>
          <StatusBadge
            label={humanize(program.status)}
            tone={LOYALTY_PROGRAM_STATUS_TONES[program.status]}
          />
        </div>
        <p className="text-muted-foreground text-sm">{program.code}</p>
      </div>

      {error && <p className="text-sm text-destructive">{error}</p>}

      {canManage && availableTransitions.length > 0 && (
        <div className="flex flex-wrap gap-2">
          {availableTransitions.map((target) => (
            <Button
              key={target}
              size="sm"
              variant={target === "archived" ? "outline" : "default"}
              disabled={transitionProgram.isPending}
              onClick={() =>
                transitionProgram.mutate(target, {
                  onError: (err) =>
                    setError(err instanceof ApiError ? err.message : "That action could not be completed."),
                })
              }
            >
              Move to {humanize(target)}
            </Button>
          ))}
        </div>
      )}

      <SectionCard
        title="Program configuration"
        description="Earn and redemption rules — display only, the backend owns every calculation."
      >
        <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
          <div>
            <p className="text-muted-foreground text-xs">Earn rate</p>
            <p className="text-sm font-medium">
              {program.points_per_currency_unit} {program.points_display_name} /{" "}
              {formatMinorUnits(program.currency_unit_minor)}
            </p>
          </div>
          <div>
            <p className="text-muted-foreground text-xs">Redemption value</p>
            <p className="text-sm font-medium">
              {program.redemption_points_per_unit} pts = {formatMinorUnits(program.redemption_value_minor)}
            </p>
          </div>
          <div>
            <p className="text-muted-foreground text-xs">Minimum redemption</p>
            <p className="text-sm font-medium">{program.minimum_redemption_points} pts</p>
          </div>
          <div>
            <p className="text-muted-foreground text-xs">Points expiry</p>
            <p className="text-sm font-medium">
              {program.points_expiry_days ? `${program.points_expiry_days} days` : "Never"}
            </p>
          </div>
        </div>
        {program.terms_summary && (
          <p className="text-muted-foreground mt-3 text-sm">{program.terms_summary}</p>
        )}
      </SectionCard>

      <SectionCard
        title="Tiers"
        description="Qualification thresholds and benefits, ordered by rank."
        actions={
          canManageTiers ? (
            <Button size="sm" onClick={() => setShowCreateTier(true)}>
              <Plus className="size-4" />
              New tier
            </Button>
          ) : undefined
        }
      >
        <DataTable
          columns={tierColumns}
          data={tiers ?? []}
          getRowId={(row) => row.id}
          loading={tiersLoading}
          emptyTitle="No tiers configured"
          emptyDescription="Create the first tier to start segmenting members by spend or activity."
        />
      </SectionCard>

      <CreateTierModal programId={programId} open={showCreateTier} onOpenChange={setShowCreateTier} />
    </div>
  );
}
