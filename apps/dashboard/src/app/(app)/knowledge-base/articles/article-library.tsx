"use client";

import { useMemo, useState } from "react";
import type { ColumnDef } from "@tanstack/react-table";
import type { KnowledgeArticle } from "@rkpr/contracts";
import { Plus } from "lucide-react";

import { useArticleList } from "@/lib/hooks/use-knowledge";
import { useDebouncedValue } from "@/lib/hooks/use-debounced-value";
import { hasPermission, useCurrentUser } from "@/lib/hooks/use-current-user";
import { ARTICLE_STATUS_TONES, formatDateTime, humanize } from "@/lib/crm-display";
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
import Link from "next/link";
import { CreateArticleModal } from "./create-article-modal";

const PAGE_SIZE = 25;
const ALL = "__all";
const STATUSES = ["draft", "in_review", "changes_requested", "approved", "published", "superseded", "archived"];

export function ArticleLibrary() {
  const { data: currentUser } = useCurrentUser();
  const [page, setPage] = useState(1);
  const [searchInput, setSearchInput] = useState("");
  const [status, setStatus] = useState(ALL);
  const [showCreate, setShowCreate] = useState(false);

  const search = useDebouncedValue(searchInput);
  const canCreate = hasPermission(currentUser, "knowledge.create");

  const { data, isLoading, isError, refetch } = useArticleList({
    page,
    pageSize: PAGE_SIZE,
    status: status === ALL ? undefined : status,
  });

  const filteredRows = useMemo(() => {
    const rows = data?.data ?? [];
    if (!search) return rows;
    const lower = search.toLowerCase();
    return rows.filter(
      (row) =>
        row.title.toLowerCase().includes(lower) || row.article_number.toLowerCase().includes(lower),
    );
  }, [data, search]);

  const columns = useMemo<ColumnDef<KnowledgeArticle, unknown>[]>(
    () => [
      {
        id: "title",
        header: "Article",
        enableSorting: false,
        cell: ({ row }) => (
          <Link
            href={`/knowledge-base/articles/${row.original.id}`}
            className="font-medium hover:underline"
          >
            <div className="flex flex-col">
              <span>{row.original.title}</span>
              <span className="text-muted-foreground text-xs">{row.original.article_number}</span>
            </div>
          </Link>
        ),
      },
      {
        id: "article_type",
        header: "Type",
        enableSorting: false,
        cell: ({ row }) => <span className="text-sm">{humanize(row.original.article_type)}</span>,
      },
      {
        id: "status",
        header: "Status",
        enableSorting: false,
        cell: ({ row }) => (
          <StatusBadge
            label={humanize(row.original.status)}
            tone={ARTICLE_STATUS_TONES[row.original.status]}
          />
        ),
      },
      {
        id: "version",
        header: "Latest version",
        enableSorting: false,
        cell: ({ row }) => <span className="text-sm">v{row.original.latest_version_number}</span>,
      },
      {
        id: "updated_at",
        header: "Updated",
        enableSorting: false,
        cell: ({ row }) => (
          <span className="text-sm">{formatDateTime(row.original.updated_at)}</span>
        ),
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
        title="Article library"
        description="Every SOP, policy, procedure, checklist, and reference document."
        actions={
          canCreate ? (
            <Button onClick={() => setShowCreate(true)}>
              <Plus className="size-4" />
              New article
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
        searchPlaceholder="Search title or article number…"
        hasActiveFilters={!!search || status !== ALL}
        onReset={() => {
          setSearchInput("");
          setStatus(ALL);
          setPage(1);
        }}
        filters={
          <Select
            value={status}
            onValueChange={(value) => {
              setStatus(value);
              setPage(1);
            }}
          >
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
        <ErrorState title="Could not load articles" onRetry={() => void refetch()} />
      ) : (
        <DataTable
          columns={columns}
          data={filteredRows}
          getRowId={(row) => row.id}
          loading={isLoading}
          emptyTitle="No articles match these filters"
          emptyDescription={
            search || status !== ALL
              ? "Try clearing the filters."
              : "Create the first knowledge article to get started."
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

      <CreateArticleModal open={showCreate} onOpenChange={setShowCreate} />
    </div>
  );
}
