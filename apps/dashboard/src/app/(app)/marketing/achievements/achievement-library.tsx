"use client";

import { useMemo, useState } from "react";
import type { ColumnDef } from "@tanstack/react-table";
import type { Achievement } from "@rkpr/contracts";
import { Plus } from "lucide-react";
import Link from "next/link";

import { useAchievementList } from "@/lib/hooks/use-achievements";
import { useDebouncedValue } from "@/lib/hooks/use-debounced-value";
import { hasPermission, useCurrentUser } from "@/lib/hooks/use-current-user";
import { formatDateTime, formatMinorUnits } from "@/lib/crm-display";
import { summarizeRuleNode } from "./condition-builder";
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
import { CreateAchievementModal } from "./create-achievement-modal";

const PAGE_SIZE = 25;
const ALL = "__all";

function rewardLabel(achievement: Achievement): string {
  if (achievement.reward_ledger === "none" || achievement.reward_amount === null) return "No reward";
  if (achievement.reward_ledger === "internal_credit") return formatMinorUnits(achievement.reward_amount);
  return `${achievement.reward_amount} pts`;
}

export function AchievementLibrary() {
  const { data: currentUser } = useCurrentUser();
  const [page, setPage] = useState(1);
  const [searchInput, setSearchInput] = useState("");
  const [activeFilter, setActiveFilter] = useState(ALL);
  const [showCreate, setShowCreate] = useState(false);

  const search = useDebouncedValue(searchInput);
  const canManage = hasPermission(currentUser, "achievements.manage");

  const { data, isLoading, isError, refetch } = useAchievementList({
    page,
    pageSize: PAGE_SIZE,
    isActive: activeFilter === ALL ? undefined : activeFilter === "active",
  });

  const filteredRows = useMemo(() => {
    const rows = data?.data ?? [];
    if (!search) return rows;
    const lower = search.toLowerCase();
    return rows.filter(
      (row) => row.name.toLowerCase().includes(lower) || row.code.toLowerCase().includes(lower),
    );
  }, [data, search]);

  const columns = useMemo<ColumnDef<Achievement, unknown>[]>(
    () => [
      {
        id: "name",
        header: "Achievement",
        enableSorting: false,
        cell: ({ row }) => (
          <Link
            href={`/marketing/achievements/${row.original.id}`}
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
        id: "condition",
        header: "Condition",
        enableSorting: false,
        cell: ({ row }) => (
          <span className="text-muted-foreground text-xs">
            {summarizeRuleNode(row.original.condition)}
          </span>
        ),
      },
      {
        id: "reward",
        header: "Reward",
        enableSorting: false,
        cell: ({ row }) => <span className="text-sm">{rewardLabel(row.original)}</span>,
      },
      {
        id: "status",
        header: "Status",
        enableSorting: false,
        cell: ({ row }) => (
          <div className="flex flex-wrap gap-1">
            <StatusBadge
              label={row.original.is_active ? "Active" : "Inactive"}
              tone={row.original.is_active ? "success" : "neutral"}
            />
            {row.original.is_hidden && <StatusBadge label="Hidden" tone="info" />}
            {row.original.is_repeatable && <StatusBadge label="Repeatable" tone="info" />}
          </div>
        ),
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

  const pageCount = useMemo(
    () => (data ? Math.max(1, Math.ceil(data.pagination.total / PAGE_SIZE)) : 0),
    [data],
  );

  return (
    <div className="flex flex-1 flex-col gap-4 p-6">
      <PageHeader
        title="Achievements"
        description="Milestone rules that automatically award customers as they cross a threshold."
        actions={
          canManage ? (
            <Button onClick={() => setShowCreate(true)}>
              <Plus className="size-4" />
              New achievement
            </Button>
          ) : null
        }
      />

      <FilterBar
        search={searchInput}
        onSearchChange={(value) => {
          setSearchInput(value);
          setPage(1);
        }}
        searchPlaceholder="Search name or code…"
        hasActiveFilters={!!search || activeFilter !== ALL}
        onReset={() => {
          setSearchInput("");
          setActiveFilter(ALL);
          setPage(1);
        }}
        filters={
          <Select
            value={activeFilter}
            onValueChange={(value) => {
              setActiveFilter(value);
              setPage(1);
            }}
          >
            <SelectTrigger className="w-40" aria-label="Filter by active state">
              <SelectValue placeholder="Active state" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value={ALL}>All</SelectItem>
              <SelectItem value="active">Active</SelectItem>
              <SelectItem value="inactive">Inactive</SelectItem>
            </SelectContent>
          </Select>
        }
      />

      {isError ? (
        <ErrorState title="Could not load achievements" onRetry={() => void refetch()} />
      ) : (
        <DataTable
          columns={columns}
          data={filteredRows}
          getRowId={(row) => row.id}
          loading={isLoading}
          emptyTitle="No achievements match these filters"
          emptyDescription={
            search || activeFilter !== ALL
              ? "Try clearing the filters."
              : "Create the first achievement to get started."
          }
          pagination={{
            pageIndex: page - 1,
            pageCount,
            total: data?.pagination.total ?? 0,
            pageSize: PAGE_SIZE,
            onPageChange: (pageIndex) => setPage(pageIndex + 1),
          }}
        />
      )}

      <CreateAchievementModal open={showCreate} onOpenChange={setShowCreate} />
    </div>
  );
}
