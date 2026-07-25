"use client";

import { useMemo, useState } from "react";
import Link from "next/link";
import {
  flexRender,
  getCoreRowModel,
  useReactTable,
  type ColumnDef,
} from "@tanstack/react-table";
import type { StaffUserListItem } from "@rkpr/contracts";

import { useStaffList, useDepartments } from "@/lib/hooks/use-staff";
import { hasPermission, useCurrentUser } from "@/lib/hooks/use-current-user";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { InviteStaffForm } from "./invite-staff-form";

const ACCOUNT_STATUS_OPTIONS = ["invited", "active", "suspended", "disabled", "locked", "archived"];
const PAGE_SIZE = 25;

const columns: ColumnDef<StaffUserListItem>[] = [
  {
    header: "Name",
    accessorKey: "display_name",
    cell: ({ row }) => (
      <Link href={`/staff/${row.original.id}`} className="font-medium hover:underline">
        {row.original.display_name}
      </Link>
    ),
  },
  { header: "Employee code", accessorKey: "employee_code" },
  { header: "Email", accessorKey: "email" },
  { header: "Job title", accessorKey: "job_title" },
  {
    header: "Status",
    accessorKey: "account_status",
    cell: ({ getValue }) => (
      <span className="rounded-full bg-zinc-100 px-2 py-0.5 text-xs capitalize dark:bg-zinc-800">
        {getValue<string>()}
      </span>
    ),
  },
];

export function StaffDirectory() {
  const { data: currentUser } = useCurrentUser();
  const [page, setPage] = useState(1);
  const [search, setSearch] = useState("");
  const [accountStatus, setAccountStatus] = useState("");
  const [showInvite, setShowInvite] = useState(false);

  const { data, isLoading, isError } = useStaffList({
    page,
    pageSize: PAGE_SIZE,
    search: search || undefined,
    accountStatus: accountStatus || undefined,
  });
  const { data: departments } = useDepartments();

  const table = useReactTable({
    data: data?.data ?? [],
    columns,
    getCoreRowModel: getCoreRowModel(),
  });

  const totalPages = useMemo(
    () => (data ? Math.max(1, Math.ceil(data.pagination.total / PAGE_SIZE)) : 1),
    [data],
  );

  const canManage = hasPermission(currentUser, "staff.manage");

  return (
    <div className="flex flex-1 flex-col gap-4 p-6">
      <div className="flex items-center justify-between">
        <h1 className="text-lg font-semibold">Staff & HR</h1>
        <div className="flex gap-2">
          <Button variant="outline" asChild>
            <Link href="/staff/roles">Roles & permissions</Link>
          </Button>
          {canManage && (
            <Button onClick={() => setShowInvite((v) => !v)}>
              {showInvite ? "Close" : "Invite staff member"}
            </Button>
          )}
        </div>
      </div>

      {showInvite && (
        <InviteStaffForm
          departments={departments ?? []}
          onDone={() => setShowInvite(false)}
        />
      )}

      <div className="flex flex-wrap items-center gap-3">
        <Input
          placeholder="Search by name or email…"
          value={search}
          onChange={(e) => {
            setSearch(e.target.value);
            setPage(1);
          }}
          className="max-w-xs"
        />
        <select
          className="h-9 rounded-md border border-zinc-300 bg-transparent px-2 text-sm dark:border-zinc-700"
          value={accountStatus}
          onChange={(e) => {
            setAccountStatus(e.target.value);
            setPage(1);
          }}
        >
          <option value="">All statuses</option>
          {ACCOUNT_STATUS_OPTIONS.map((status) => (
            <option key={status} value={status}>
              {status}
            </option>
          ))}
        </select>
      </div>

      {isError && (
        <p className="text-sm text-red-600">Could not load the staff directory. Try again.</p>
      )}

      <div className="overflow-x-auto rounded-md border border-black/10 dark:border-white/15">
        <table className="w-full text-sm">
          <thead className="bg-zinc-50 dark:bg-zinc-900">
            {table.getHeaderGroups().map((headerGroup) => (
              <tr key={headerGroup.id}>
                {headerGroup.headers.map((header) => (
                  <th key={header.id} className="px-3 py-2 text-left font-medium">
                    {flexRender(header.column.columnDef.header, header.getContext())}
                  </th>
                ))}
              </tr>
            ))}
          </thead>
          <tbody>
            {isLoading ? (
              <tr>
                <td colSpan={columns.length} className="px-3 py-6 text-center text-zinc-500">
                  Loading…
                </td>
              </tr>
            ) : table.getRowModel().rows.length === 0 ? (
              <tr>
                <td colSpan={columns.length} className="px-3 py-6 text-center text-zinc-500">
                  No staff members match these filters.
                </td>
              </tr>
            ) : (
              table.getRowModel().rows.map((row) => (
                <tr key={row.id} className="border-t border-black/5 dark:border-white/10">
                  {row.getVisibleCells().map((cell) => (
                    <td key={cell.id} className="px-3 py-2">
                      {flexRender(cell.column.columnDef.cell, cell.getContext())}
                    </td>
                  ))}
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>

      <div className="flex items-center justify-between text-sm text-zinc-500">
        <span>
          Page {page} of {totalPages} · {data?.pagination.total ?? 0} total
        </span>
        <div className="flex gap-2">
          <Button
            variant="outline"
            size="sm"
            disabled={page <= 1}
            onClick={() => setPage((p) => Math.max(1, p - 1))}
          >
            Previous
          </Button>
          <Button
            variant="outline"
            size="sm"
            disabled={page >= totalPages}
            onClick={() => setPage((p) => p + 1)}
          >
            Next
          </Button>
        </div>
      </div>
    </div>
  );
}
