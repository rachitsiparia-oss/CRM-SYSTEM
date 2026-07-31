"use client";

import { useMemo, useState } from "react";
import type { ColumnDef } from "@tanstack/react-table";
import type { LoyaltyProgram } from "@rkpr/contracts";
import { Award, Plus, Users } from "lucide-react";
import Link from "next/link";

import { useLoyaltyAnalytics, useLoyaltyPrograms } from "@/lib/hooks/use-loyalty";
import { hasPermission, useCurrentUser } from "@/lib/hooks/use-current-user";
import { LOYALTY_PROGRAM_STATUS_TONES, formatMinorUnits, humanize } from "@/lib/crm-display";
import { PageHeader } from "@/components/page-header";
import { StatCard } from "@/components/stat-card";
import { DataTable } from "@/components/data-table/data-table";
import { ErrorState } from "@/components/error-state";
import { StatusBadge } from "@/components/status-badge";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { CreateProgramModal } from "./create-program-modal";

export function LoyaltyDashboard() {
  const { data: currentUser } = useCurrentUser();
  const [showCreate, setShowCreate] = useState(false);

  const { data: programs, isLoading, isError, refetch } = useLoyaltyPrograms();
  const { data: analytics, isLoading: analyticsLoading } = useLoyaltyAnalytics();

  const canManage = hasPermission(currentUser, "loyalty.manage");

  const columns = useMemo<ColumnDef<LoyaltyProgram, unknown>[]>(
    () => [
      {
        id: "name",
        header: "Program",
        enableSorting: false,
        cell: ({ row }) => (
          <Link
            href={`/marketing/loyalty/programs/${row.original.id}`}
            className="font-medium hover:underline"
          >
            <div className="flex flex-col">
              <span className="flex items-center gap-2">
                {row.original.name}
                {row.original.is_default && (
                  <Badge variant="secondary" className="text-xs">
                    Default
                  </Badge>
                )}
              </span>
              <span className="text-muted-foreground text-xs">{row.original.code}</span>
            </div>
          </Link>
        ),
      },
      {
        id: "status",
        header: "Status",
        enableSorting: false,
        cell: ({ row }) => (
          <StatusBadge
            label={humanize(row.original.status)}
            tone={LOYALTY_PROGRAM_STATUS_TONES[row.original.status]}
          />
        ),
      },
      {
        id: "earn_rate",
        header: "Earn rate",
        enableSorting: false,
        cell: ({ row }) => (
          <span className="text-sm">
            {row.original.points_per_currency_unit} {row.original.points_display_name} per{" "}
            {formatMinorUnits(row.original.currency_unit_minor)}
          </span>
        ),
      },
      {
        id: "redemption",
        header: "Redemption value",
        enableSorting: false,
        cell: ({ row }) => (
          <span className="text-sm">
            {row.original.redemption_points_per_unit} pts ={" "}
            {formatMinorUnits(row.original.redemption_value_minor)}
          </span>
        ),
      },
      {
        id: "min_redeem",
        header: "Min. redemption",
        enableSorting: false,
        cell: ({ row }) => <span className="text-sm">{row.original.minimum_redemption_points} pts</span>,
      },
    ],
    [],
  );

  return (
    <div className="flex flex-1 flex-col gap-6 p-6">
      <PageHeader
        title="Loyalty"
        description="Programs, tiers, member accounts, and the points ledger."
        actions={
          <div className="flex flex-wrap gap-2">
            <Button variant="outline" asChild>
              <Link href="/marketing/loyalty/accounts">
                <Users className="size-4" />
                Member accounts
              </Link>
            </Button>
            {canManage && (
              <Button onClick={() => setShowCreate(true)}>
                <Plus className="size-4" />
                New program
              </Button>
            )}
          </div>
        }
      />

      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <StatCard
          label="Active members"
          value={analytics?.active_members ?? 0}
          icon={Users}
          loading={analyticsLoading}
        />
        <StatCard
          label="Points issued (30d)"
          value={analytics?.points_issued_30d ?? 0}
          icon={Award}
          loading={analyticsLoading}
        />
        <StatCard
          label="Points redeemed (30d)"
          value={analytics?.points_redeemed_30d ?? 0}
          icon={Award}
          loading={analyticsLoading}
        />
        <StatCard
          label="Outstanding points liability"
          value={formatMinorUnits(analytics?.outstanding_points_liability_minor)}
          icon={Award}
          loading={analyticsLoading}
        />
      </div>

      {isError ? (
        <ErrorState title="Could not load loyalty programs" onRetry={() => void refetch()} />
      ) : (
        <DataTable
          columns={columns}
          data={programs ?? []}
          getRowId={(row) => row.id}
          loading={isLoading}
          emptyTitle="No loyalty programs yet"
          emptyDescription="Create the first loyalty program to start enrolling members."
        />
      )}

      <CreateProgramModal open={showCreate} onOpenChange={setShowCreate} />
    </div>
  );
}
