"use client";

import { useMemo, useState } from "react";
import type { ColumnDef } from "@tanstack/react-table";
import type { ReferralProgram } from "@rkpr/contracts";
import { Plus, Users } from "lucide-react";
import Link from "next/link";

import { useReferralPrograms } from "@/lib/hooks/use-referrals";
import { useDebouncedValue } from "@/lib/hooks/use-debounced-value";
import { hasPermission, useCurrentUser } from "@/lib/hooks/use-current-user";
import { REFERRAL_PROGRAM_STATUS_TONES, formatDateTime, formatMinorUnits, humanize } from "@/lib/crm-display";
import { PageHeader } from "@/components/page-header";
import { FilterBar } from "@/components/filter-bar";
import { DataTable } from "@/components/data-table/data-table";
import { ErrorState } from "@/components/error-state";
import { StatusBadge } from "@/components/status-badge";
import { Button } from "@/components/ui/button";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { CreateReferralProgramModal } from "./create-referral-program-modal";

const ALL = "__all";
const STATUSES = ["draft", "active", "paused", "archived"];

function rewardSummary(program: ReferralProgram): string {
  const unit = program.reward_ledger === "loyalty_points" ? "pts" : "credit";
  if (program.reward_ledger === "internal_credit") {
    return `${formatMinorUnits(program.referrer_reward_amount)} / ${formatMinorUnits(program.referee_reward_amount)}`;
  }
  return `${program.referrer_reward_amount} ${unit} / ${program.referee_reward_amount} ${unit}`;
}

export function ReferralLibrary() {
  const { data: currentUser } = useCurrentUser();
  const [searchInput, setSearchInput] = useState("");
  const [status, setStatus] = useState(ALL);
  const [showCreate, setShowCreate] = useState(false);

  const search = useDebouncedValue(searchInput);
  const canManage = hasPermission(currentUser, "referrals.manage");

  const { data: programs, isLoading, isError, refetch } = useReferralPrograms();

  const filteredRows = useMemo(() => {
    const rows = programs ?? [];
    return rows.filter((row) => {
      if (status !== ALL && row.status !== status) return false;
      if (!search) return true;
      const lower = search.toLowerCase();
      return row.name.toLowerCase().includes(lower) || row.code.toLowerCase().includes(lower);
    });
  }, [programs, search, status]);

  const columns = useMemo<ColumnDef<ReferralProgram, unknown>[]>(
    () => [
      {
        id: "name",
        header: "Program",
        enableSorting: false,
        cell: ({ row }) => (
          <Link
            href={`/marketing/referrals/${row.original.id}`}
            className="font-medium hover:underline"
          >
            <div className="flex flex-col">
              <span>{row.original.name}</span>
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
            tone={REFERRAL_PROGRAM_STATUS_TONES[row.original.status]}
          />
        ),
      },
      {
        id: "reward_ledger",
        header: "Reward ledger",
        enableSorting: false,
        cell: ({ row }) => <span className="text-sm">{humanize(row.original.reward_ledger)}</span>,
      },
      {
        id: "rewards",
        header: "Referrer / referee reward",
        enableSorting: false,
        cell: ({ row }) => <span className="text-sm">{rewardSummary(row.original)}</span>,
      },
      {
        id: "reward_hold_days",
        header: "Hold days",
        enableSorting: false,
        cell: ({ row }) => <span className="text-sm">{row.original.reward_hold_days}</span>,
      },
      {
        id: "updated_at",
        header: "Updated",
        enableSorting: false,
        cell: ({ row }) => <span className="text-sm">{formatDateTime(row.original.updated_at)}</span>,
      },
    ],
    [],
  );

  return (
    <div className="flex flex-1 flex-col gap-4 p-6">
      <PageHeader
        title="Referral programs"
        description="Configure referrer/referee rewards and issue referral codes."
        actions={
          <div className="flex flex-wrap gap-2">
            <Button variant="outline" asChild>
              <Link href="/marketing/referrals/relationships">
                <Users className="size-4" />
                Relationships
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

      <FilterBar
        search={searchInput}
        onSearchChange={setSearchInput}
        searchPlaceholder="Search name or code…"
        hasActiveFilters={!!search || status !== ALL}
        onReset={() => {
          setSearchInput("");
          setStatus(ALL);
        }}
        filters={
          <Select value={status} onValueChange={setStatus}>
            <SelectTrigger className="w-44" aria-label="Filter by status">
              <SelectValue placeholder="Status" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value={ALL}>All statuses</SelectItem>
              {STATUSES.map((s) => (
                <SelectItem key={s} value={s}>
                  {humanize(s)}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        }
      />

      {isError ? (
        <ErrorState title="Could not load referral programs" onRetry={() => void refetch()} />
      ) : (
        <DataTable
          columns={columns}
          data={filteredRows}
          getRowId={(row) => row.id}
          loading={isLoading}
          emptyTitle="No referral programs match these filters"
          emptyDescription={
            search || status !== ALL
              ? "Try clearing the filters."
              : "Create the first referral program to get started."
          }
        />
      )}

      <CreateReferralProgramModal open={showCreate} onOpenChange={setShowCreate} />
    </div>
  );
}
