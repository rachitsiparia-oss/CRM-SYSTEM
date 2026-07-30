"use client";

import { useMemo, useState } from "react";
import type { ColumnDef } from "@tanstack/react-table";
import type { Task } from "@rkpr/contracts";
import { Plus } from "lucide-react";

import { useTaskList } from "@/lib/hooks/use-tasks";
import { useDebouncedValue } from "@/lib/hooks/use-debounced-value";
import { hasPermission, useCurrentUser } from "@/lib/hooks/use-current-user";
import { TASK_PRIORITY_TONES, TASK_STATUS_TONES, formatDateTime, humanize } from "@/lib/crm-display";
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
import { TaskCreateModal } from "./task-create-modal";
import { TaskDetailDrawer } from "./task-detail-drawer";

const PAGE_SIZE = 25;
const ALL = "__all";
type ViewTab = "all" | "mine" | "due_today" | "overdue" | "blocked";

const VIEW_TABS: { value: ViewTab; label: string }[] = [
  { value: "all", label: "All tasks" },
  { value: "mine", label: "My tasks" },
  { value: "due_today", label: "Due today" },
  { value: "overdue", label: "Overdue" },
  { value: "blocked", label: "Blocked" },
];

export function TasksView() {
  const { data: currentUser } = useCurrentUser();
  const [page, setPage] = useState(1);
  const [searchInput, setSearchInput] = useState("");
  const [priority, setPriority] = useState(ALL);
  const [view, setView] = useState<ViewTab>("all");
  const [showCreate, setShowCreate] = useState(false);
  const [selectedTaskId, setSelectedTaskId] = useState<string | null>(null);

  const search = useDebouncedValue(searchInput);
  const canCreate = hasPermission(currentUser, "tasks.create");

  const { data, isLoading, isError, refetch } = useTaskList({
    page,
    pageSize: PAGE_SIZE,
    search: search || undefined,
    priority: priority === ALL ? undefined : priority,
    view: view === "all" ? undefined : view,
  });

  const columns = useMemo<ColumnDef<Task, unknown>[]>(
    () => [
      {
        id: "title",
        header: "Task",
        enableSorting: false,
        cell: ({ row }) => (
          <button
            className="text-left font-medium hover:underline"
            onClick={() => setSelectedTaskId(row.original.id)}
          >
            <div className="flex flex-col">
              <span>{row.original.title}</span>
              <span className="text-muted-foreground text-xs">{row.original.task_number}</span>
            </div>
          </button>
        ),
      },
      {
        id: "source",
        header: "Source",
        enableSorting: false,
        cell: ({ row }) => <span className="text-sm">{humanize(row.original.source)}</span>,
      },
      {
        id: "priority",
        header: "Priority",
        enableSorting: false,
        cell: ({ row }) => (
          <StatusBadge
            label={humanize(row.original.priority)}
            tone={TASK_PRIORITY_TONES[row.original.priority]}
          />
        ),
      },
      {
        id: "status",
        header: "Status",
        enableSorting: false,
        cell: ({ row }) => (
          <StatusBadge
            label={humanize(row.original.status)}
            tone={TASK_STATUS_TONES[row.original.status]}
          />
        ),
      },
      {
        id: "due_at",
        header: "Due",
        enableSorting: false,
        cell: ({ row }) => <span className="text-sm">{formatDateTime(row.original.due_at)}</span>,
      },
    ],
    [],
  );

  const pageCount = useMemo(
    () => (data ? Math.max(1, Math.ceil(data.pagination.total / PAGE_SIZE)) : 0),
    [data],
  );

  const hasActiveFilters = !!search || priority !== ALL;

  return (
    <div className="flex flex-1 flex-col gap-4 p-6">
      <PageHeader
        title="Tasks"
        description="Cross-module operational work — reservation follow-ups, order issues, inventory alerts, and manual to-dos."
        actions={
          canCreate ? (
            <Button onClick={() => setShowCreate(true)}>
              <Plus className="size-4" />
              New task
            </Button>
          ) : null
        }
      />

      <div className="flex flex-wrap gap-2">
        {VIEW_TABS.map((tab) => (
          <Button
            key={tab.value}
            variant={view === tab.value ? "default" : "outline"}
            size="sm"
            onClick={() => {
              setView(tab.value);
              setPage(1);
            }}
          >
            {tab.label}
          </Button>
        ))}
      </div>

      <FilterBar
        search={searchInput}
        onSearchChange={(value) => {
          setSearchInput(value);
          setPage(1);
        }}
        searchPlaceholder="Search title or task number…"
        hasActiveFilters={hasActiveFilters}
        onReset={() => {
          setSearchInput("");
          setPriority(ALL);
          setPage(1);
        }}
        filters={
          <Select
            value={priority}
            onValueChange={(value) => {
              setPriority(value);
              setPage(1);
            }}
          >
            <SelectTrigger className="w-40" aria-label="Filter by priority">
              <SelectValue placeholder="Priority" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value={ALL}>All priorities</SelectItem>
              {["low", "normal", "high", "urgent"].map((p) => (
                <SelectItem key={p} value={p}>
                  {humanize(p)}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        }
      />

      {isError ? (
        <ErrorState title="Could not load tasks" onRetry={() => void refetch()} />
      ) : (
        <DataTable
          columns={columns}
          data={data?.data ?? []}
          getRowId={(row) => row.id}
          loading={isLoading}
          emptyTitle="No tasks match these filters"
          emptyDescription={
            hasActiveFilters ? "Try clearing the filters." : "Create the first task to get started."
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

      <TaskCreateModal open={showCreate} onOpenChange={setShowCreate} />
      <TaskDetailDrawer
        taskId={selectedTaskId}
        onOpenChange={(open) => !open && setSelectedTaskId(null)}
      />
    </div>
  );
}
