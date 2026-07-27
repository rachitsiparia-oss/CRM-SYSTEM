"use client";

import { useState } from "react";
import Link from "next/link";
import { ArrowLeft, Plus } from "lucide-react";

import {
  useAddTransferItem,
  useInventoryTransfer,
  usePostInventoryTransfer,
  useReverseInventoryTransfer,
} from "@/lib/hooks/use-inventory-operations";
import { useInventoryItemList } from "@/lib/hooks/use-inventory-items";
import { useInventoryLocations } from "@/lib/hooks/use-inventory-reference";
import { hasPermission, useCurrentUser } from "@/lib/hooks/use-current-user";
import { TRANSFER_STATUS_TONES, formatDateTime, humanize } from "@/lib/crm-display";
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

function AddTransferLineModal({
  transferId,
  open,
  onOpenChange,
}: {
  transferId: string;
  open: boolean;
  onOpenChange: (open: boolean) => void;
}) {
  const { data: itemsPage } = useInventoryItemList({ page: 1, pageSize: 100, sort: "name" });
  const addItem = useAddTransferItem(transferId);
  const [itemId, setItemId] = useState("");
  const [quantity, setQuantity] = useState("");
  const [error, setError] = useState<string | null>(null);

  function resetForm() {
    setItemId("");
    setQuantity("");
    setError(null);
  }

  async function handleSubmit() {
    setError(null);
    if (!itemId || !quantity) {
      setError("Item and quantity are required.");
      return;
    }
    try {
      await addItem.mutateAsync({ inventory_item_id: itemId, quantity });
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
      title="Add transfer line"
      footer={
        <>
          <Button variant="outline" onClick={() => onOpenChange(false)}>
            Cancel
          </Button>
          <Button disabled={addItem.isPending} onClick={() => void handleSubmit()}>
            {addItem.isPending ? "Adding…" : "Add line"}
          </Button>
        </>
      }
    >
      <div className="grid gap-4">
        <FormField label="Item" htmlFor="transfer-line-item" required>
          <Select value={itemId} onValueChange={setItemId}>
            <SelectTrigger id="transfer-line-item">
              <SelectValue placeholder="Select an item" />
            </SelectTrigger>
            <SelectContent>
              {(itemsPage?.data ?? []).map((item) => (
                <SelectItem key={item.id} value={item.id}>
                  {item.name}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </FormField>
        <FormField label="Quantity" htmlFor="transfer-line-qty" required>
          <Input
            id="transfer-line-qty"
            inputMode="decimal"
            value={quantity}
            onChange={(e) => setQuantity(e.target.value)}
          />
        </FormField>
        {error && (
          <p role="alert" className="text-destructive text-sm">
            {error}
          </p>
        )}
      </div>
    </Modal>
  );
}

export function TransferDetail({ transferId }: { transferId: string }) {
  const { data: currentUser } = useCurrentUser();
  const { data: transfer, isLoading, isError, refetch } = useInventoryTransfer(transferId);
  const { data: locations } = useInventoryLocations();
  const postTransfer = usePostInventoryTransfer(transferId);
  const reverseTransfer = useReverseInventoryTransfer(transferId);

  const [showAddLine, setShowAddLine] = useState(false);
  const [confirmPost, setConfirmPost] = useState(false);
  const [confirmReverse, setConfirmReverse] = useState(false);
  const [reverseReason, setReverseReason] = useState("");
  const [actionError, setActionError] = useState<string | null>(null);

  const canCreate = hasPermission(currentUser, "inventory.transfers.create");
  const canPost = hasPermission(currentUser, "inventory.transfers.post");
  const canReverse = hasPermission(currentUser, "inventory.transfers.reverse");

  if (isLoading) {
    return (
      <div className="flex-1 p-6">
        <PageSkeleton />
      </div>
    );
  }

  if (isError || !transfer) {
    return (
      <div className="flex-1 p-6">
        <ErrorState variant="404" title="Transfer not found" onRetry={() => void refetch()} />
      </div>
    );
  }

  const isDraft = transfer.status === "draft";
  const locationName = (id: string) => locations?.find((l) => l.id === id)?.name ?? "—";

  return (
    <div className="flex flex-1 flex-col gap-6 p-6">
      <div>
        <Link
          href="/inventory/transfers"
          className="text-muted-foreground inline-flex items-center gap-1 text-sm hover:underline"
        >
          <ArrowLeft className="size-3.5" />
          Transfers
        </Link>
      </div>

      <PageHeader
        title={transfer.transfer_number}
        description={`${locationName(transfer.source_location_id)} → ${locationName(transfer.destination_location_id)}`}
        actions={
          <div className="flex items-center gap-2">
            <StatusBadge
              label={humanize(transfer.status)}
              tone={TRANSFER_STATUS_TONES[transfer.status]}
            />
            {isDraft && canCreate && (
              <Button variant="outline" size="sm" onClick={() => setShowAddLine(true)}>
                <Plus className="size-4" />
                Add line
              </Button>
            )}
            {isDraft && canPost && (
              <Button size="sm" onClick={() => setConfirmPost(true)}>
                Post transfer
              </Button>
            )}
            {transfer.status === "posted" && canReverse && (
              <Button variant="destructive" size="sm" onClick={() => setConfirmReverse(true)}>
                Reverse
              </Button>
            )}
          </div>
        }
      />

      <SectionCard title="Details">
        <dl className="grid grid-cols-2 gap-4 sm:grid-cols-3">
          <Field label="Requested by" value={transfer.requested_by} />
          <Field label="Notes" value={transfer.notes ?? "—"} />
          <Field label="Created" value={formatDateTime(transfer.created_at)} />
        </dl>
      </SectionCard>

      <SectionCard title="Line items">
        {transfer.items.length === 0 ? (
          <EmptyState title="No lines yet" description="Add a line to move an item." />
        ) : (
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Quantity</TableHead>
                <TableHead>Notes</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {transfer.items.map((item) => (
                <TableRow key={item.id}>
                  <TableCell>{item.quantity}</TableCell>
                  <TableCell>{item.notes ?? "—"}</TableCell>
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

      <AddTransferLineModal transferId={transferId} open={showAddLine} onOpenChange={setShowAddLine} />

      <ConfirmDialog
        open={confirmPost}
        onOpenChange={setConfirmPost}
        title="Post this transfer?"
        description="Posting atomically creates the linked transfer-out and transfer-in movements. This cannot be undone except by reversal."
        confirmLabel="Post transfer"
        onConfirm={async () => {
          setActionError(null);
          try {
            await postTransfer.mutateAsync();
          } catch (err) {
            setActionError(err instanceof ApiError ? err.message : "The transfer could not be posted.");
          }
        }}
      />

      <Modal
        open={confirmReverse}
        onOpenChange={(next) => {
          if (!next) setReverseReason("");
          setConfirmReverse(next);
        }}
        title="Reverse this transfer?"
        description="Both legs of the transfer will be reversed."
        footer={
          <>
            <Button variant="outline" onClick={() => setConfirmReverse(false)}>
              Cancel
            </Button>
            <Button
              variant="destructive"
              disabled={!reverseReason.trim() || reverseTransfer.isPending}
              onClick={async () => {
                setActionError(null);
                try {
                  await reverseTransfer.mutateAsync({ reason: reverseReason });
                  setConfirmReverse(false);
                  setReverseReason("");
                } catch (err) {
                  setActionError(
                    err instanceof ApiError ? err.message : "The transfer could not be reversed.",
                  );
                }
              }}
            >
              {reverseTransfer.isPending ? "Reversing…" : "Reverse transfer"}
            </Button>
          </>
        }
      >
        <FormField label="Reason" htmlFor="transfer-reverse-reason" required>
          <Input
            id="transfer-reverse-reason"
            value={reverseReason}
            onChange={(e) => setReverseReason(e.target.value)}
          />
        </FormField>
      </Modal>
    </div>
  );
}
