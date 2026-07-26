"use client";

import { useState } from "react";
import type { Order } from "@rkpr/contracts";

import { useAssignOrder } from "@/lib/hooks/use-orders";
import { useStaffList } from "@/lib/hooks/use-staff";
import { useDebouncedValue } from "@/lib/hooks/use-debounced-value";
import { ApiError } from "@/lib/api/errors";
import { SectionCard } from "@/components/section-card";
import { SearchInput } from "@/components/forms/search-input";
import { Button } from "@/components/ui/button";

export function OrderAssignControl({ order }: { order: Order }) {
  const assignOrder = useAssignOrder(order.id);
  const [query, setQuery] = useState("");
  const [error, setError] = useState<string | null>(null);
  const debouncedQuery = useDebouncedValue(query, 300);

  const { data } = useStaffList({ page: 1, pageSize: 8, search: debouncedQuery || undefined });

  async function assign(staffUserId: string) {
    setError(null);
    try {
      await assignOrder.mutateAsync(staffUserId);
      setQuery("");
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "The order could not be assigned.");
    }
  }

  return (
    <SectionCard
      title="Assigned staff"
      description={order.assigned_staff_id ? "Assigning a new staff member replaces the current assignment." : "No staff member assigned yet."}
    >
      <div className="relative max-w-sm">
        <SearchInput value={query} onChange={setQuery} placeholder="Search staff by name…" />
        {data && data.data.length > 0 && query && (
          <ul className="bg-popover absolute z-10 mt-1 w-full rounded-md border shadow-md">
            {data.data.map((staff) => (
              <li key={staff.id}>
                <button
                  type="button"
                  className="hover:bg-muted flex w-full items-center justify-between px-3 py-2 text-left text-sm"
                  onClick={() => void assign(staff.id)}
                >
                  <span>{staff.display_name}</span>
                  <Button size="sm" variant="ghost" disabled={assignOrder.isPending} tabIndex={-1}>
                    Assign
                  </Button>
                </button>
              </li>
            ))}
          </ul>
        )}
      </div>
      {error && (
        <p role="alert" className="text-destructive mt-3 text-sm">
          {error}
        </p>
      )}
    </SectionCard>
  );
}
