"use client";

import { useMemo, type ReactNode } from "react";
import {
  flexRender,
  getCoreRowModel,
  useReactTable,
  type ColumnDef,
  type OnChangeFn,
  type RowSelectionState,
  type SortingState,
} from "@tanstack/react-table";
import { ArrowDown, ArrowUp, ArrowUpDown } from "lucide-react";

import { cn } from "@/lib/utils";
import { Checkbox } from "@/components/ui/checkbox";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { Skeleton } from "@/components/ui/skeleton";
import { EmptyState } from "@/components/empty-state";
import { DataTableColumnToggle } from "./data-table-column-toggle";
import { DataTablePagination, type DataTablePaginationProps } from "./data-table-pagination";

export interface DataTableProps<TData> {
  columns: ColumnDef<TData, unknown>[];
  data: TData[];
  getRowId?: (row: TData) => string;
  loading?: boolean;
  loadingRowCount?: number;
  emptyTitle?: string;
  emptyDescription?: string;

  /** Server-side sorting only — this table never sorts an already-fetched
   * page client-side (DATABASE_AND_API.md section 19.6, explicit sort
   * allowlists are enforced by the API, not guessed here). */
  sorting?: SortingState;
  onSortingChange?: OnChangeFn<SortingState>;

  enableRowSelection?: boolean;
  rowSelection?: RowSelectionState;
  onRowSelectionChange?: OnChangeFn<RowSelectionState>;
  bulkActions?: (selectedRowIds: string[]) => ReactNode;

  enableColumnResizing?: boolean;
  enableColumnVisibility?: boolean;
  stickyHeader?: boolean;

  pagination?: DataTablePaginationProps;
  className?: string;
}

/** The one generic enterprise table this project uses — every future
 * module composes this rather than hand-rolling its own <table>
 * (ARCHITECTURE_AND_TECH_STACK.md section 6.6). Sorting and pagination are
 * both server-driven by design; this component never assumes it holds a
 * complete dataset to paginate or sort client-side. */
export function DataTable<TData>({
  columns,
  data,
  getRowId,
  loading,
  loadingRowCount = 8,
  emptyTitle = "No results",
  emptyDescription,
  sorting,
  onSortingChange,
  enableRowSelection,
  rowSelection,
  onRowSelectionChange,
  bulkActions,
  enableColumnResizing,
  enableColumnVisibility,
  stickyHeader,
  pagination,
  className,
}: DataTableProps<TData>) {
  const effectiveColumns = useMemo<ColumnDef<TData, unknown>[]>(() => {
    if (!enableRowSelection) return columns;
    const selectionColumn: ColumnDef<TData, unknown> = {
      id: "__select",
      size: 36,
      enableHiding: false,
      enableResizing: false,
      header: ({ table }) => (
        <Checkbox
          checked={
            table.getIsAllPageRowsSelected() ||
            (table.getIsSomePageRowsSelected() && "indeterminate")
          }
          onCheckedChange={(value) => table.toggleAllPageRowsSelected(!!value)}
          aria-label="Select all rows on this page"
        />
      ),
      cell: ({ row }) => (
        <Checkbox
          checked={row.getIsSelected()}
          onCheckedChange={(value) => row.toggleSelected(!!value)}
          aria-label="Select row"
        />
      ),
    };
    return [selectionColumn, ...columns];
  }, [columns, enableRowSelection]);

  const table = useReactTable({
    data,
    columns: effectiveColumns,
    getCoreRowModel: getCoreRowModel(),
    getRowId,
    manualSorting: true,
    manualPagination: true,
    enableRowSelection,
    enableColumnResizing,
    columnResizeMode: "onChange",
    state: {
      sorting,
      // Listing `rowSelection` in this controlled `state` object at all
      // marks it as externally controlled to TanStack Table, regardless of
      // whether the caller actually passed one — table.getState().rowSelection
      // then stays `undefined` instead of falling back to TanStack's own
      // default `{}`, and any row.getIsSelected() call throws. Every caller
      // that doesn't use row selection (the common case) hit this the
      // moment real data with at least one row rendered.
      rowSelection: rowSelection ?? {},
    },
    onSortingChange,
    onRowSelectionChange,
  });

  const selectedRowIds = Object.keys(rowSelection ?? {}).filter((id) => rowSelection?.[id]);

  return (
    <div className={cn("flex flex-col gap-2", className)}>
      {(enableColumnVisibility || (enableRowSelection && selectedRowIds.length > 0)) && (
        <div className="flex items-center justify-between gap-2">
          <div>
            {enableRowSelection && selectedRowIds.length > 0 && (
              <div className="flex items-center gap-2">
                <span className="text-muted-foreground text-sm">
                  {selectedRowIds.length} selected
                </span>
                {bulkActions?.(selectedRowIds)}
              </div>
            )}
          </div>
          {enableColumnVisibility && <DataTableColumnToggle table={table} />}
        </div>
      )}

      <div className="overflow-hidden rounded-2xl border border-border/60">
        <div className={cn(stickyHeader && "max-h-[70vh] overflow-y-auto")}>
          <Table style={{ width: enableColumnResizing ? table.getTotalSize() : undefined }}>
            <TableHeader className={cn(stickyHeader && "bg-card sticky top-0 z-10")}>
              {table.getHeaderGroups().map((headerGroup) => (
                <TableRow key={headerGroup.id}>
                  {headerGroup.headers.map((header) => {
                    const canSort = header.column.columnDef.enableSorting !== false && onSortingChange;
                    const sortDirection = header.column.getIsSorted();
                    return (
                      <TableHead
                        key={header.id}
                        style={{
                          width: enableColumnResizing ? header.getSize() : undefined,
                          position: "relative",
                        }}
                      >
                        {header.isPlaceholder ? null : canSort ? (
                          <button
                            type="button"
                            className="flex items-center gap-1 select-none"
                            onClick={header.column.getToggleSortingHandler()}
                          >
                            {flexRender(header.column.columnDef.header, header.getContext())}
                            {sortDirection === "asc" ? (
                              <ArrowUp className="size-3.5" />
                            ) : sortDirection === "desc" ? (
                              <ArrowDown className="size-3.5" />
                            ) : (
                              <ArrowUpDown className="text-muted-foreground/50 size-3.5" />
                            )}
                          </button>
                        ) : (
                          flexRender(header.column.columnDef.header, header.getContext())
                        )}
                        {enableColumnResizing && header.column.getCanResize() && (
                          <div
                            onMouseDown={header.getResizeHandler()}
                            onTouchStart={header.getResizeHandler()}
                            className="hover:bg-primary/50 absolute top-0 right-0 h-full w-1 cursor-col-resize touch-none select-none"
                          />
                        )}
                      </TableHead>
                    );
                  })}
                </TableRow>
              ))}
            </TableHeader>
            <TableBody>
              {loading ? (
                Array.from({ length: loadingRowCount }).map((_, rowIndex) => (
                  <TableRow key={rowIndex}>
                    {effectiveColumns.map((_, colIndex) => (
                      <TableCell key={colIndex}>
                        <Skeleton className="h-5 w-full" />
                      </TableCell>
                    ))}
                  </TableRow>
                ))
              ) : table.getRowModel().rows.length === 0 ? (
                <TableRow>
                  <TableCell colSpan={effectiveColumns.length} className="p-0">
                    <EmptyState
                      title={emptyTitle}
                      description={emptyDescription}
                      className="border-none"
                    />
                  </TableCell>
                </TableRow>
              ) : (
                table.getRowModel().rows.map((row) => (
                  <TableRow key={row.id} data-state={row.getIsSelected() ? "selected" : undefined}>
                    {row.getVisibleCells().map((cell) => (
                      <TableCell
                        key={cell.id}
                        style={{ width: enableColumnResizing ? cell.column.getSize() : undefined }}
                      >
                        {flexRender(cell.column.columnDef.cell, cell.getContext())}
                      </TableCell>
                    ))}
                  </TableRow>
                ))
              )}
            </TableBody>
          </Table>
        </div>
      </div>

      {pagination && <DataTablePagination {...pagination} />}
    </div>
  );
}
