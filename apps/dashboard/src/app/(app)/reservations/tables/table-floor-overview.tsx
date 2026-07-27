"use client";

import { useMemo, useState } from "react";
import Link from "next/link";
import { Plus } from "lucide-react";

import { useDiningAreas, useTables } from "@/lib/hooks/use-reservations";
import { hasPermission, useCurrentUser } from "@/lib/hooks/use-current-user";
import { TABLE_STATUS_TONES, humanize } from "@/lib/crm-display";
import { PageHeader } from "@/components/page-header";
import { SectionCard } from "@/components/section-card";
import { StatusBadge } from "@/components/status-badge";
import { EmptyState } from "@/components/empty-state";
import { CardSkeleton } from "@/components/skeletons/card-skeleton";
import { Button } from "@/components/ui/button";
import { TableCreateModal } from "./table-create-modal";

export function TableFloorOverview() {
  const { data: currentUser } = useCurrentUser();
  const { data: diningAreas } = useDiningAreas();
  const { data: tables, isLoading } = useTables();
  const [showCreate, setShowCreate] = useState(false);

  const canManage = hasPermission(currentUser, "reservations.tables.manage");

  const tablesByArea = useMemo(() => {
    const map = new Map<string, typeof tables>();
    for (const table of tables ?? []) {
      const list = map.get(table.dining_area_id) ?? [];
      list.push(table);
      map.set(table.dining_area_id, list);
    }
    return map;
  }, [tables]);

  return (
    <div className="flex flex-1 flex-col gap-4 p-6">
      <PageHeader
        title="Tables & Floor"
        description="Live table status across every dining area — the current floor layout."
        actions={
          canManage ? (
            <Button onClick={() => setShowCreate(true)}>
              <Plus className="size-4" />
              New table
            </Button>
          ) : null
        }
      />

      {isLoading ? (
        <CardSkeleton />
      ) : !tables || tables.length === 0 ? (
        <EmptyState title="No tables yet" description="Create the first table to start building the floor." />
      ) : (
        (diningAreas ?? []).map((area) => {
          const areaTables = tablesByArea.get(area.id) ?? [];
          if (areaTables.length === 0) return null;
          return (
            <SectionCard key={area.id} title={area.name} description={`${areaTables.length} table(s)`}>
              <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-4">
                {areaTables.map((table) => (
                  <Link
                    key={table.id}
                    href={`/reservations/tables/${table.id}`}
                    className="hover:border-primary flex flex-col gap-1 rounded-md border p-3"
                  >
                    <span className="text-sm font-medium">{table.table_number}</span>
                    <span className="text-muted-foreground text-xs">seats {table.capacity}</span>
                    <StatusBadge
                      label={humanize(table.status)}
                      tone={TABLE_STATUS_TONES[table.status]}
                      className="mt-1 w-fit"
                    />
                  </Link>
                ))}
              </div>
            </SectionCard>
          );
        })
      )}

      <TableCreateModal open={showCreate} onOpenChange={setShowCreate} />
    </div>
  );
}
