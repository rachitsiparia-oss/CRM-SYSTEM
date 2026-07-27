"use client";

import Link from "next/link";
import { ArrowLeft } from "lucide-react";

import {
  useInventoryItem,
  useInventoryItemBalances,
  useInventoryItemBatches,
  useInventoryItemMovements,
} from "@/lib/hooks/use-inventory-items";
import {
  useInventoryCategories,
  useInventoryLocations,
  useInventorySuppliers,
  useInventoryUnits,
} from "@/lib/hooks/use-inventory-reference";
import { hasPermission, useCurrentUser } from "@/lib/hooks/use-current-user";
import {
  BATCH_STATUS_TONES,
  STOCK_STATUS_TONES,
  formatDate,
  formatDateTime,
  formatMinorUnits,
  formatQuantity,
  humanize,
} from "@/lib/crm-display";
import { PageHeader } from "@/components/page-header";
import { PageSkeleton } from "@/components/skeletons/page-skeleton";
import { ErrorState } from "@/components/error-state";
import { EmptyState } from "@/components/empty-state";
import { StatusBadge } from "@/components/status-badge";
import { SectionCard } from "@/components/section-card";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { useState } from "react";

function Field({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <dt className="text-muted-foreground text-xs">{label}</dt>
      <dd className="text-sm">{value}</dd>
    </div>
  );
}

export function InventoryItemDetail({ itemId }: { itemId: string }) {
  const { data: currentUser } = useCurrentUser();
  const { data: item, isLoading, isError, refetch } = useInventoryItem(itemId);
  const { data: categories } = useInventoryCategories(true);
  const { data: units } = useInventoryUnits();
  const { data: locations } = useInventoryLocations(true);
  const { data: suppliersPage } = useInventorySuppliers({ pageSize: 100 });
  const { data: balances } = useInventoryItemBalances(itemId);
  const { data: batches } = useInventoryItemBatches(itemId, true);
  const [movementsPage, setMovementsPage] = useState(1);
  const { data: movements } = useInventoryItemMovements(itemId, movementsPage, 25);

  const canViewCost = hasPermission(currentUser, "inventory.cost.view");

  if (isLoading) {
    return (
      <div className="flex-1 p-6">
        <PageSkeleton />
      </div>
    );
  }

  if (isError || !item) {
    return (
      <div className="flex-1 p-6">
        <ErrorState
          variant="404"
          title="Inventory item not found"
          description="This item may not exist, or you may not have access to it."
          onRetry={() => void refetch()}
        />
      </div>
    );
  }

  const categoryName = categories?.find((c) => c.id === item.category_id)?.name ?? "—";
  const baseUnit = units?.find((u) => u.id === item.base_unit_id);
  const locationName = (id: string | null) =>
    locations?.find((l) => l.id === id)?.name ?? "—";
  const supplierName = (id: string | null) =>
    suppliersPage?.data.find((s) => s.id === id)?.name ?? "—";

  return (
    <div className="flex flex-1 flex-col gap-6 p-6">
      <div>
        <Link
          href="/inventory/items"
          className="text-muted-foreground inline-flex items-center gap-1 text-sm hover:underline"
        >
          <ArrowLeft className="size-3.5" />
          Inventory items
        </Link>
      </div>

      <PageHeader
        title={item.name}
        description={`${item.item_code} · ${categoryName}`}
        actions={
          <StatusBadge
            label={humanize(item.stock_status)}
            tone={STOCK_STATUS_TONES[item.stock_status]}
          />
        }
      />

      <Tabs defaultValue="overview">
        <TabsList>
          <TabsTrigger value="overview">Overview</TabsTrigger>
          <TabsTrigger value="locations">Stock by Location</TabsTrigger>
          <TabsTrigger value="batches">Batches</TabsTrigger>
          <TabsTrigger value="movements">Movements</TabsTrigger>
        </TabsList>

        <TabsContent value="overview" className="mt-4 flex flex-col gap-4">
          <SectionCard title="Stock summary">
            <dl className="grid grid-cols-2 gap-4 sm:grid-cols-4">
              <Field label="On hand" value={formatQuantity(item.current_stock, baseUnit?.symbol)} />
              <Field
                label="Reserved"
                value={formatQuantity(item.reserved_stock, baseUnit?.symbol)}
              />
              <Field
                label="Reorder level"
                value={formatQuantity(item.reorder_level, baseUnit?.symbol)}
              />
              <Field label="Target stock" value={formatQuantity(item.target_stock, baseUnit?.symbol)} />
            </dl>
          </SectionCard>

          <SectionCard title="Item details">
            <dl className="grid grid-cols-2 gap-4 sm:grid-cols-3">
              <Field label="Base unit" value={baseUnit ? `${baseUnit.name} (${baseUnit.symbol})` : "—"} />
              <Field label="Default location" value={locationName(item.default_location_id)} />
              <Field label="Preferred supplier" value={supplierName(item.preferred_supplier_id)} />
              {canViewCost && (
                <Field
                  label="Standard cost"
                  value={
                    item.standard_cost_minor !== null
                      ? `${formatMinorUnits(item.standard_cost_minor)} / ${baseUnit?.symbol ?? "unit"}`
                      : "—"
                  }
                />
              )}
              {canViewCost && (
                <Field
                  label="Latest purchase cost"
                  value={
                    item.latest_purchase_cost_minor !== null
                      ? formatMinorUnits(item.latest_purchase_cost_minor)
                      : "—"
                  }
                />
              )}
              <Field label="Lead time" value={item.lead_time_days ? `${item.lead_time_days} days` : "—"} />
              <Field label="Shelf life" value={item.shelf_life_days ? `${item.shelf_life_days} days` : "—"} />
              <Field label="Batch tracked" value={item.requires_batch_tracking ? "Yes" : "No"} />
              <Field label="Expiry tracked" value={item.requires_expiry_tracking ? "Yes" : "No"} />
              <Field label="Perishable" value={item.is_perishable ? "Yes" : "No"} />
              <Field label="Last received" value={formatDateTime(item.last_received_at)} />
              <Field label="Last counted" value={formatDateTime(item.last_counted_at)} />
            </dl>
            {item.notes && (
              <div className="mt-4">
                <dt className="text-muted-foreground text-xs">Notes</dt>
                <dd className="text-sm">{item.notes}</dd>
              </div>
            )}
          </SectionCard>
        </TabsContent>

        <TabsContent value="locations" className="mt-4">
          <SectionCard title="Stock by location">
            {!balances || balances.length === 0 ? (
              <EmptyState title="No stock recorded" description="No balances exist for this item yet." />
            ) : (
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Location</TableHead>
                    <TableHead>On hand</TableHead>
                    <TableHead>Reserved</TableHead>
                    <TableHead>Available</TableHead>
                    <TableHead>Last movement</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {balances
                    .filter((b) => !b.batch_id)
                    .map((balance) => (
                      <TableRow key={balance.id}>
                        <TableCell>{locationName(balance.storage_location_id)}</TableCell>
                        <TableCell>{formatQuantity(balance.on_hand_quantity, baseUnit?.symbol)}</TableCell>
                        <TableCell>{formatQuantity(balance.reserved_quantity, baseUnit?.symbol)}</TableCell>
                        <TableCell>
                          {formatQuantity(
                            String(
                              Number(balance.on_hand_quantity) - Number(balance.reserved_quantity),
                            ),
                            baseUnit?.symbol,
                          )}
                        </TableCell>
                        <TableCell>{formatDateTime(balance.last_movement_at)}</TableCell>
                      </TableRow>
                    ))}
                </TableBody>
              </Table>
            )}
          </SectionCard>
        </TabsContent>

        <TabsContent value="batches" className="mt-4">
          <SectionCard title="Batches">
            {!batches || batches.length === 0 ? (
              <EmptyState
                title="No batches"
                description="This item is not batch-tracked, or no batches have been received yet."
              />
            ) : (
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Batch code</TableHead>
                    <TableHead>Location</TableHead>
                    <TableHead>Remaining</TableHead>
                    <TableHead>Received</TableHead>
                    <TableHead>Expires</TableHead>
                    <TableHead>Status</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {batches.map((batch) => (
                    <TableRow key={batch.id}>
                      <TableCell className="font-medium">{batch.batch_code}</TableCell>
                      <TableCell>{locationName(batch.storage_location_id)}</TableCell>
                      <TableCell>
                        {formatQuantity(batch.remaining_quantity, baseUnit?.symbol)} /{" "}
                        {formatQuantity(batch.received_quantity, baseUnit?.symbol)}
                      </TableCell>
                      <TableCell>{formatDateTime(batch.received_at)}</TableCell>
                      <TableCell>{formatDate(batch.expires_at)}</TableCell>
                      <TableCell>
                        <StatusBadge
                          label={humanize(batch.status)}
                          tone={BATCH_STATUS_TONES[batch.status]}
                        />
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            )}
          </SectionCard>
        </TabsContent>

        <TabsContent value="movements" className="mt-4">
          <SectionCard title="Movement history" description="Append-only — every stock change ever posted for this item.">
            {!movements || movements.data.length === 0 ? (
              <EmptyState title="No movements yet" description="Stock movements will appear here." />
            ) : (
              <>
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>Movement</TableHead>
                      <TableHead>Type</TableHead>
                      <TableHead>Quantity</TableHead>
                      <TableHead>Occurred</TableHead>
                      <TableHead>Reason</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {movements.data.map((movement) => (
                      <TableRow key={movement.id}>
                        <TableCell className="font-mono text-xs">{movement.movement_number}</TableCell>
                        <TableCell>{humanize(movement.movement_type)}</TableCell>
                        <TableCell
                          className={
                            Number(movement.quantity_delta) < 0 ? "text-destructive" : undefined
                          }
                        >
                          {formatQuantity(movement.quantity_delta, baseUnit?.symbol)}
                        </TableCell>
                        <TableCell>{formatDateTime(movement.occurred_at)}</TableCell>
                        <TableCell className="max-w-xs truncate">{movement.reason ?? "—"}</TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
                <div className="mt-3 flex items-center justify-between">
                  <span className="text-muted-foreground text-xs">
                    Page {movementsPage} of{" "}
                    {Math.max(1, Math.ceil(movements.pagination.total / 25))}
                  </span>
                  <div className="flex gap-2">
                    <button
                      type="button"
                      className="text-sm underline disabled:opacity-50"
                      disabled={movementsPage <= 1}
                      onClick={() => setMovementsPage((p) => Math.max(1, p - 1))}
                    >
                      Previous
                    </button>
                    <button
                      type="button"
                      className="text-sm underline disabled:opacity-50"
                      disabled={movementsPage * 25 >= movements.pagination.total}
                      onClick={() => setMovementsPage((p) => p + 1)}
                    >
                      Next
                    </button>
                  </div>
                </div>
              </>
            )}
          </SectionCard>
        </TabsContent>
      </Tabs>
    </div>
  );
}
