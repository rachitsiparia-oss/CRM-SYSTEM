"use client";

import { useState } from "react";
import Link from "next/link";
import { ArrowLeft, Plus } from "lucide-react";

import {
  useAddReceiptItem,
  useInventoryReceipt,
  usePostInventoryReceipt,
  useReverseInventoryReceipt,
} from "@/lib/hooks/use-inventory-operations";
import { useInventoryItemList } from "@/lib/hooks/use-inventory-items";
import { useInventorySuppliers, useInventoryLocations, useInventoryUnits } from "@/lib/hooks/use-inventory-reference";
import { hasPermission, useCurrentUser } from "@/lib/hooks/use-current-user";
import { RECEIPT_STATUS_TONES, formatDate, formatMinorUnits, humanize } from "@/lib/crm-display";
import { ApiError } from "@/lib/api/errors";
import { PageHeader } from "@/components/page-header";
import { PageSkeleton } from "@/components/skeletons/page-skeleton";
import { ErrorState } from "@/components/error-state";
import { EmptyState } from "@/components/empty-state";
import { StatusBadge } from "@/components/status-badge";
import { SectionCard } from "@/components/section-card";
import { ConfirmDialog } from "@/components/modals/confirm-dialog";
import { Modal } from "@/components/modals/modal";
import { FormField } from "@/components/forms/form-field";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";

function Field({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <dt className="text-muted-foreground text-xs">{label}</dt>
      <dd className="text-sm">{value}</dd>
    </div>
  );
}

function AddReceiptLineModal({
  receiptId,
  open,
  onOpenChange,
}: {
  receiptId: string;
  open: boolean;
  onOpenChange: (open: boolean) => void;
}) {
  const { data: itemsPage } = useInventoryItemList({ page: 1, pageSize: 100, sort: "name" });
  const { data: units } = useInventoryUnits();
  const addItem = useAddReceiptItem(receiptId);

  const [itemId, setItemId] = useState("");
  const [purchaseUnitId, setPurchaseUnitId] = useState("");
  const [acceptedQuantity, setAcceptedQuantity] = useState("");
  const [unitCostRupees, setUnitCostRupees] = useState("");
  const [batchCode, setBatchCode] = useState("");
  const [expiresAt, setExpiresAt] = useState("");
  const [error, setError] = useState<string | null>(null);

  const selectedItem = (itemsPage?.data ?? []).find((i) => i.id === itemId);

  function resetForm() {
    setItemId("");
    setPurchaseUnitId("");
    setAcceptedQuantity("");
    setUnitCostRupees("");
    setBatchCode("");
    setExpiresAt("");
    setError(null);
  }

  async function handleSubmit() {
    setError(null);
    if (!itemId || !purchaseUnitId || !acceptedQuantity || !unitCostRupees) {
      setError("Item, purchase unit, quantity, and unit cost are required.");
      return;
    }
    try {
      await addItem.mutateAsync({
        inventory_item_id: itemId,
        purchase_unit_id: purchaseUnitId,
        received_quantity: acceptedQuantity,
        accepted_quantity: acceptedQuantity,
        rejected_quantity: "0",
        unit_cost_minor: Math.round(Number(unitCostRupees) * 100),
        batch_code: batchCode || null,
        expires_at: expiresAt || null,
      });
      resetForm();
      onOpenChange(false);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "The line could not be added.");
    }
  }

  return (
    <Modal
      open={open}
      onOpenChange={(next) => {
        if (!next) resetForm();
        onOpenChange(next);
      }}
      title="Add receipt line"
      footer={
        <>
          <Button type="button" variant="outline" onClick={() => onOpenChange(false)}>
            Cancel
          </Button>
          <Button type="button" disabled={addItem.isPending} onClick={() => void handleSubmit()}>
            {addItem.isPending ? "Adding…" : "Add line"}
          </Button>
        </>
      }
    >
      <div className="grid gap-4">
        <FormField label="Item" htmlFor="line-item" required>
          <Select value={itemId} onValueChange={setItemId}>
            <SelectTrigger id="line-item">
              <SelectValue placeholder="Select an item" />
            </SelectTrigger>
            <SelectContent>
              {(itemsPage?.data ?? []).map((item) => (
                <SelectItem key={item.id} value={item.id}>
                  {item.name} ({item.item_code})
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </FormField>

        <FormField label="Purchase unit" htmlFor="line-unit" required>
          <Select value={purchaseUnitId} onValueChange={setPurchaseUnitId}>
            <SelectTrigger id="line-unit">
              <SelectValue placeholder="Select a unit" />
            </SelectTrigger>
            <SelectContent>
              {(units ?? []).map((unit) => (
                <SelectItem key={unit.id} value={unit.id}>
                  {unit.name} ({unit.symbol})
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </FormField>

        <FormField label="Accepted quantity" htmlFor="line-qty" required>
          <Input
            id="line-qty"
            inputMode="decimal"
            value={acceptedQuantity}
            onChange={(e) => setAcceptedQuantity(e.target.value)}
          />
        </FormField>

        <FormField label="Unit cost (per purchase unit, ₹)" htmlFor="line-cost" required>
          <Input
            id="line-cost"
            inputMode="decimal"
            value={unitCostRupees}
            onChange={(e) => setUnitCostRupees(e.target.value)}
          />
        </FormField>

        {selectedItem?.requires_batch_tracking && (
          <>
            <FormField label="Batch code" htmlFor="line-batch" required>
              <Input id="line-batch" value={batchCode} onChange={(e) => setBatchCode(e.target.value)} />
            </FormField>
            <FormField label="Expires on" htmlFor="line-expiry">
              <Input
                id="line-expiry"
                type="date"
                value={expiresAt}
                onChange={(e) => setExpiresAt(e.target.value)}
              />
            </FormField>
          </>
        )}

        {error && (
          <p role="alert" className="text-destructive text-sm">
            {error}
          </p>
        )}
      </div>
    </Modal>
  );
}

export function ReceiptDetail({ receiptId }: { receiptId: string }) {
  const { data: currentUser } = useCurrentUser();
  const { data: receipt, isLoading, isError, refetch } = useInventoryReceipt(receiptId);
  const { data: suppliersPage } = useInventorySuppliers({ pageSize: 100 });
  const { data: locations } = useInventoryLocations();
  const postReceipt = usePostInventoryReceipt(receiptId);
  const reverseReceipt = useReverseInventoryReceipt(receiptId);

  const [showAddLine, setShowAddLine] = useState(false);
  const [confirmPost, setConfirmPost] = useState(false);
  const [confirmReverse, setConfirmReverse] = useState(false);
  const [reverseReason, setReverseReason] = useState("");
  const [actionError, setActionError] = useState<string | null>(null);

  const canCreate = hasPermission(currentUser, "inventory.receipts.create");
  const canPost = hasPermission(currentUser, "inventory.receipts.post");
  const canReverse = hasPermission(currentUser, "inventory.receipts.reverse");

  if (isLoading) {
    return (
      <div className="flex-1 p-6">
        <PageSkeleton />
      </div>
    );
  }

  if (isError || !receipt) {
    return (
      <div className="flex-1 p-6">
        <ErrorState
          variant="404"
          title="Receipt not found"
          onRetry={() => void refetch()}
        />
      </div>
    );
  }

  const isDraft = receipt.status === "draft";

  return (
    <div className="flex flex-1 flex-col gap-6 p-6">
      <div>
        <Link
          href="/inventory/receipts"
          className="text-muted-foreground inline-flex items-center gap-1 text-sm hover:underline"
        >
          <ArrowLeft className="size-3.5" />
          Receipts
        </Link>
      </div>

      <PageHeader
        title={receipt.receipt_number}
        description={`${suppliersPage?.data.find((s) => s.id === receipt.supplier_id)?.name ?? "—"} · ${formatDate(receipt.received_date)}`}
        actions={
          <div className="flex items-center gap-2">
            <StatusBadge
              label={humanize(receipt.status)}
              tone={RECEIPT_STATUS_TONES[receipt.status]}
            />
            {isDraft && canCreate && (
              <Button variant="outline" size="sm" onClick={() => setShowAddLine(true)}>
                <Plus className="size-4" />
                Add line
              </Button>
            )}
            {isDraft && canPost && (
              <Button size="sm" onClick={() => setConfirmPost(true)}>
                Post receipt
              </Button>
            )}
            {receipt.status === "posted" && canReverse && (
              <Button variant="destructive" size="sm" onClick={() => setConfirmReverse(true)}>
                Reverse
              </Button>
            )}
          </div>
        }
      />

      <SectionCard title="Details">
        <dl className="grid grid-cols-2 gap-4 sm:grid-cols-4">
          <Field
            label="Location"
            value={locations?.find((l) => l.id === receipt.storage_location_id)?.name ?? "—"}
          />
          <Field label="Supplier reference" value={receipt.supplier_reference ?? "—"} />
          <Field label="Total value" value={formatMinorUnits(receipt.total_value_minor)} />
          <Field label="Notes" value={receipt.notes ?? "—"} />
        </dl>
      </SectionCard>

      <SectionCard
        title="Line items"
        description={isDraft ? "Posted receipts become read-only." : "This receipt is read-only."}
      >
        {receipt.items.length === 0 ? (
          <EmptyState title="No lines yet" description="Add a line to record a received item." />
        ) : (
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Accepted</TableHead>
                <TableHead>Base quantity</TableHead>
                <TableHead>Unit cost</TableHead>
                <TableHead>Line total</TableHead>
                <TableHead>Batch</TableHead>
                <TableHead>Expires</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {receipt.items.map((item) => (
                <TableRow key={item.id}>
                  <TableCell>{item.accepted_quantity}</TableCell>
                  <TableCell>{item.base_quantity}</TableCell>
                  <TableCell>{formatMinorUnits(item.unit_cost_minor)}</TableCell>
                  <TableCell>{formatMinorUnits(item.line_total_minor)}</TableCell>
                  <TableCell>{item.batch_code ?? "—"}</TableCell>
                  <TableCell>{formatDate(item.expires_at)}</TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        )}
      </SectionCard>

      {actionError && (
        <p role="alert" className="text-destructive text-sm">
          {actionError}
        </p>
      )}

      <AddReceiptLineModal receiptId={receiptId} open={showAddLine} onOpenChange={setShowAddLine} />

      <ConfirmDialog
        open={confirmPost}
        onOpenChange={setConfirmPost}
        title="Post this receipt?"
        description="Posting validates every line, converts quantities to base units, updates stock and cost, and makes the receipt read-only. This cannot be undone except by reversal."
        confirmLabel="Post receipt"
        onConfirm={async () => {
          setActionError(null);
          try {
            await postReceipt.mutateAsync();
          } catch (err) {
            setActionError(err instanceof ApiError ? err.message : "The receipt could not be posted.");
          }
        }}
      />

      <Modal
        open={confirmReverse}
        onOpenChange={(next) => {
          if (!next) setReverseReason("");
          setConfirmReverse(next);
        }}
        title="Reverse this receipt?"
        description="A compensating reversal movement will be posted for every line. The original record stays in the ledger."
        footer={
          <>
            <Button variant="outline" onClick={() => setConfirmReverse(false)}>
              Cancel
            </Button>
            <Button
              variant="destructive"
              disabled={!reverseReason.trim() || reverseReceipt.isPending}
              onClick={async () => {
                setActionError(null);
                try {
                  await reverseReceipt.mutateAsync({ reason: reverseReason });
                  setConfirmReverse(false);
                  setReverseReason("");
                } catch (err) {
                  setActionError(
                    err instanceof ApiError ? err.message : "The receipt could not be reversed.",
                  );
                }
              }}
            >
              {reverseReceipt.isPending ? "Reversing…" : "Reverse receipt"}
            </Button>
          </>
        }
      >
        <FormField label="Reason" htmlFor="reverse-reason" required>
          <Input
            id="reverse-reason"
            value={reverseReason}
            onChange={(e) => setReverseReason(e.target.value)}
          />
        </FormField>
      </Modal>
    </div>
  );
}
