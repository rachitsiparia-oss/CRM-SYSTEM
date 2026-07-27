"use client";

import { useState } from "react";
import Link from "next/link";
import { ArrowLeft } from "lucide-react";
import type { StockCountLine } from "@rkpr/contracts";

import {
  useApproveInventoryStockCount,
  useCancelInventoryStockCount,
  useInventoryStockCount,
  useRecordStockCountLine,
  useStartInventoryStockCount,
  useSubmitInventoryStockCount,
} from "@/lib/hooks/use-inventory-operations";
import { useInventoryItemList } from "@/lib/hooks/use-inventory-items";
import { useInventoryLocations } from "@/lib/hooks/use-inventory-reference";
import { hasPermission, useCurrentUser } from "@/lib/hooks/use-current-user";
import { COUNT_STATUS_TONES, formatDateTime, formatQuantity, humanize } from "@/lib/crm-display";
import { ApiError } from "@/lib/api/errors";
import { PageHeader } from "@/components/page-header";
import { PageSkeleton } from "@/components/skeletons/page-skeleton";
import { ErrorState } from "@/components/error-state";
import { EmptyState } from "@/components/empty-state";
import { StatusBadge } from "@/components/status-badge";
import { SectionCard } from "@/components/section-card";
import { ConfirmDialog } from "@/components/modals/confirm-dialog";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";

function CountLineRow({
  countId,
  line,
  itemName,
}: {
  countId: string;
  line: StockCountLine;
  itemName: string;
}) {
  const [value, setValue] = useState(line.counted_quantity ?? "");
  const [saved, setSaved] = useState(line.counted_quantity !== null);
  const recordLine = useRecordStockCountLine(countId, line.id);
  const [error, setError] = useState<string | null>(null);

  async function handleSave() {
    setError(null);
    try {
      await recordLine.mutateAsync({ counted_quantity: value });
      setSaved(true);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "The count could not be saved.");
    }
  }

  const variance =
    line.variance_quantity !== null ? Number(line.variance_quantity) : null;

  return (
    <TableRow>
      <TableCell>{itemName}</TableCell>
      <TableCell>{formatQuantity(line.system_quantity)}</TableCell>
      <TableCell>
        <div className="flex items-center gap-2">
          <Input
            className="w-28"
            inputMode="decimal"
            value={value}
            onChange={(e) => {
              setValue(e.target.value);
              setSaved(false);
            }}
          />
          <Button size="sm" variant="outline" disabled={recordLine.isPending || saved} onClick={() => void handleSave()}>
            {saved ? "Saved" : recordLine.isPending ? "Saving…" : "Save"}
          </Button>
        </div>
        {error && <p className="text-destructive mt-1 text-xs">{error}</p>}
      </TableCell>
      <TableCell className={variance !== null && variance !== 0 ? "text-destructive" : undefined}>
        {line.variance_quantity !== null ? formatQuantity(line.variance_quantity) : "—"}
      </TableCell>
    </TableRow>
  );
}

export function StockCountDetail({ countId }: { countId: string }) {
  const { data: currentUser } = useCurrentUser();
  const { data: count, isLoading, isError, refetch } = useInventoryStockCount(countId);
  const { data: locations } = useInventoryLocations();
  const { data: items } = useInventoryItemList({ page: 1, pageSize: 200, sort: "name" });

  const startCount = useStartInventoryStockCount(countId);
  const submitCount = useSubmitInventoryStockCount(countId);
  const approveCount = useApproveInventoryStockCount(countId);
  const cancelCount = useCancelInventoryStockCount(countId);

  const [confirmSubmit, setConfirmSubmit] = useState(false);
  const [confirmApprove, setConfirmApprove] = useState(false);
  const [confirmCancel, setConfirmCancel] = useState(false);
  const [actionError, setActionError] = useState<string | null>(null);

  const canRecord = hasPermission(currentUser, "inventory.counts.create");
  const canSubmit = hasPermission(currentUser, "inventory.counts.submit");
  const canApprove = hasPermission(currentUser, "inventory.counts.approve");

  if (isLoading) {
    return (
      <div className="flex-1 p-6">
        <PageSkeleton />
      </div>
    );
  }

  if (isError || !count) {
    return (
      <div className="flex-1 p-6">
        <ErrorState variant="404" title="Stock count not found" onRetry={() => void refetch()} />
      </div>
    );
  }

  const itemName = new Map((items?.data ?? []).map((i) => [i.id, i.name]));
  const locationName = locations?.find((l) => l.id === count.storage_location_id)?.name ?? "—";
  const allLinesCounted = count.lines.every((line) => line.counted_quantity !== null);

  return (
    <div className="flex flex-1 flex-col gap-6 p-6">
      <div>
        <Link
          href="/inventory/stock-counts"
          className="text-muted-foreground inline-flex items-center gap-1 text-sm hover:underline"
        >
          <ArrowLeft className="size-3.5" />
          Stock counts
        </Link>
      </div>

      <PageHeader
        title={count.count_number}
        description={locationName}
        actions={
          <div className="flex items-center gap-2">
            <StatusBadge label={humanize(count.status)} tone={COUNT_STATUS_TONES[count.status]} />
            {count.status === "draft" && canRecord && (
              <Button size="sm" onClick={() => startCount.mutate()} disabled={startCount.isPending}>
                {startCount.isPending ? "Starting…" : "Start counting"}
              </Button>
            )}
            {count.status === "in_progress" && canSubmit && (
              <Button
                size="sm"
                disabled={!allLinesCounted}
                onClick={() => setConfirmSubmit(true)}
                title={!allLinesCounted ? "Every line needs a counted quantity first." : undefined}
              >
                Submit for approval
              </Button>
            )}
            {count.status === "submitted" && canApprove && (
              <Button size="sm" onClick={() => setConfirmApprove(true)}>
                Approve
              </Button>
            )}
            {(count.status === "draft" ||
              count.status === "in_progress" ||
              count.status === "submitted") &&
              canRecord && (
                <Button variant="destructive" size="sm" onClick={() => setConfirmCancel(true)}>
                  Cancel
                </Button>
              )}
          </div>
        }
      />

      <SectionCard title="Count lines" description="System quantity is frozen when counting starts.">
        {count.status === "draft" ? (
          <EmptyState
            title="Not started yet"
            description="Start counting to snapshot expected stock for this location."
          />
        ) : count.lines.length === 0 ? (
          <EmptyState title="No stock at this location" description="Nothing to count here." />
        ) : (
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Item</TableHead>
                <TableHead>System quantity</TableHead>
                <TableHead>Counted quantity</TableHead>
                <TableHead>Variance</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {count.lines.map((line) =>
                count.status === "in_progress" && canRecord ? (
                  <CountLineRow
                    key={line.id}
                    countId={countId}
                    line={line}
                    itemName={itemName.get(line.inventory_item_id) ?? "—"}
                  />
                ) : (
                  <TableRow key={line.id}>
                    <TableCell>{itemName.get(line.inventory_item_id) ?? "—"}</TableCell>
                    <TableCell>{formatQuantity(line.system_quantity)}</TableCell>
                    <TableCell>
                      {line.counted_quantity !== null
                        ? formatQuantity(line.counted_quantity)
                        : "Not counted"}
                    </TableCell>
                    <TableCell>
                      {line.variance_quantity !== null
                        ? formatQuantity(line.variance_quantity)
                        : "—"}
                    </TableCell>
                  </TableRow>
                ),
              )}
            </TableBody>
          </Table>
        )}
      </SectionCard>

      {count.status === "approved" && (
        <SectionCard title="Approval">
          <p className="text-sm">
            Approved {formatDateTime(count.approved_at)}. Every non-zero variance posted a
            correcting stock-count-adjustment movement.
          </p>
        </SectionCard>
      )}

      {actionError && (
        <p role="alert" className="text-destructive text-sm">
          {actionError}
        </p>
      )}

      <ConfirmDialog
        open={confirmSubmit}
        onOpenChange={setConfirmSubmit}
        title="Submit this count for approval?"
        description="Once submitted, counted quantities can no longer be edited."
        confirmLabel="Submit"
        onConfirm={async () => {
          setActionError(null);
          try {
            await submitCount.mutateAsync();
          } catch (err) {
            setActionError(err instanceof ApiError ? err.message : "The count could not be submitted.");
          }
        }}
      />

      <ConfirmDialog
        open={confirmApprove}
        onOpenChange={setConfirmApprove}
        title="Approve this count?"
        description="Every non-zero variance will post a correcting stock-count-adjustment movement, permanently adjusting stock."
        confirmLabel="Approve"
        onConfirm={async () => {
          setActionError(null);
          try {
            await approveCount.mutateAsync();
          } catch (err) {
            setActionError(err instanceof ApiError ? err.message : "The count could not be approved.");
          }
        }}
      />

      <ConfirmDialog
        open={confirmCancel}
        onOpenChange={setConfirmCancel}
        variant="warning"
        title="Cancel this count?"
        description="No stock will be affected. This session cannot be resumed."
        confirmLabel="Cancel session"
        onConfirm={async () => {
          setActionError(null);
          try {
            await cancelCount.mutateAsync();
          } catch (err) {
            setActionError(err instanceof ApiError ? err.message : "The count could not be cancelled.");
          }
        }}
      />
    </div>
  );
}
