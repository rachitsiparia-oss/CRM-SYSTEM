"use client";

import { useState } from "react";
import Link from "next/link";
import { ArrowLeft, Eye } from "lucide-react";
import type { ColumnDef } from "@tanstack/react-table";
import type { GiftCardLedgerEntry } from "@rkpr/contracts";

import {
  useActivateGiftCard,
  useCancelGiftCard,
  useExpireGiftCard,
  useGiftCardDetail,
  useGiftCardLedger,
  useReinstateGiftCard,
  useRevealGiftCardCode,
  useSuspendGiftCard,
} from "@/lib/hooks/use-gift-cards";
import { hasPermission, useCurrentUser } from "@/lib/hooks/use-current-user";
import { GIFT_CARD_STATUS_TONES, formatDateTime, formatMinorUnits, humanize } from "@/lib/crm-display";
import { ApiError } from "@/lib/api/errors";
import { PageHeader } from "@/components/page-header";
import { PageSkeleton } from "@/components/skeletons/page-skeleton";
import { ErrorState } from "@/components/error-state";
import { StatusBadge, type StatusTone } from "@/components/status-badge";
import { SectionCard } from "@/components/section-card";
import { StatCard } from "@/components/stat-card";
import { ConfirmDialog } from "@/components/modals/confirm-dialog";
import { Button } from "@/components/ui/button";
import { DataTable } from "@/components/data-table/data-table";
import { AdjustBalanceModal } from "./adjust-balance-modal";
import { ReverseLedgerEntryModal } from "./reverse-ledger-entry-modal";

const LEDGER_ENTRY_TONES: Record<GiftCardLedgerEntry["entry_type"], StatusTone> = {
  issue: "info",
  activate: "success",
  redeem: "info",
  reverse: "warning",
  adjust: "warning",
  expire: "neutral",
  cancel: "danger",
  migration: "neutral",
};

const PAGE_SIZE = 20;

function Field({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <dt className="text-muted-foreground text-xs">{label}</dt>
      <dd className="text-sm">{value}</dd>
    </div>
  );
}

export function GiftCardDetail({ giftCardId }: { giftCardId: string }) {
  const { data: currentUser } = useCurrentUser();
  const { data: giftCard, isLoading, isError, refetch } = useGiftCardDetail(giftCardId);
  const [ledgerPage, setLedgerPage] = useState(1);
  const { data: ledger, isLoading: ledgerLoading } = useGiftCardLedger(giftCardId, {
    page: ledgerPage,
    pageSize: PAGE_SIZE,
  });

  const revealCode = useRevealGiftCardCode(giftCardId);
  const activate = useActivateGiftCard(giftCardId);
  const suspend = useSuspendGiftCard(giftCardId);
  const reinstate = useReinstateGiftCard(giftCardId);
  const cancel = useCancelGiftCard(giftCardId);
  const expire = useExpireGiftCard(giftCardId);

  const [error, setError] = useState<string | null>(null);
  const [revealed, setRevealed] = useState<{ card_number: string; code_last4: string } | null>(null);
  const [showAdjust, setShowAdjust] = useState(false);
  const [confirmAction, setConfirmAction] = useState<
    "activate" | "suspend" | "reinstate" | "cancel" | "expire" | null
  >(null);
  const [reverseTarget, setReverseTarget] = useState<string | null>(null);

  const canReveal = hasPermission(currentUser, "gift_cards.reveal_sensitive");
  const canAdjust = hasPermission(currentUser, "gift_cards.adjust");
  const canReverse = hasPermission(currentUser, "gift_cards.reverse");

  if (isLoading) {
    return (
      <div className="flex-1 p-6">
        <PageSkeleton />
      </div>
    );
  }

  if (isError || !giftCard) {
    return (
      <div className="flex-1 p-6">
        <ErrorState variant="404" title="Gift card not found" onRetry={() => void refetch()} />
      </div>
    );
  }

  const availableActions: { key: typeof confirmAction; label: string }[] =
    giftCard.status === "draft"
      ? [{ key: "activate", label: "Activate" }]
      : giftCard.status === "active" || giftCard.status === "partially_redeemed"
        ? [
            { key: "suspend", label: "Suspend" },
            { key: "expire", label: "Expire" },
            { key: "cancel", label: "Cancel" },
          ]
        : giftCard.status === "suspended"
          ? [
              { key: "reinstate", label: "Reinstate" },
              { key: "cancel", label: "Cancel" },
            ]
          : [];

  const actionMutation = {
    activate,
    suspend,
    reinstate,
    cancel,
    expire,
  } as const;

  const ledgerColumns: ColumnDef<GiftCardLedgerEntry, unknown>[] = [
    {
      id: "entry_type",
      header: "Type",
      enableSorting: false,
      cell: ({ row }) => (
        <StatusBadge
          label={humanize(row.original.entry_type)}
          tone={LEDGER_ENTRY_TONES[row.original.entry_type]}
        />
      ),
    },
    {
      id: "amount",
      header: "Amount",
      enableSorting: false,
      cell: ({ row }) => (
        <span className="text-sm">{formatMinorUnits(row.original.amount_delta_minor)}</span>
      ),
    },
    {
      id: "balance_after",
      header: "Balance after",
      enableSorting: false,
      cell: ({ row }) => <span className="text-sm">{formatMinorUnits(row.original.balance_after_minor)}</span>,
    },
    {
      id: "reason",
      header: "Reason",
      enableSorting: false,
      cell: ({ row }) => <span className="text-sm">{row.original.reason ?? "—"}</span>,
    },
    {
      id: "effective_at",
      header: "Effective",
      enableSorting: false,
      cell: ({ row }) => <span className="text-sm">{formatDateTime(row.original.effective_at)}</span>,
    },
    {
      id: "actions",
      header: "",
      enableSorting: false,
      cell: ({ row }) =>
        canReverse && row.original.entry_type !== "reverse" && !row.original.reversal_of_id ? (
          <Button size="sm" variant="outline" onClick={() => setReverseTarget(row.original.id)}>
            Reverse
          </Button>
        ) : null,
    },
  ];

  const ledgerPageCount = ledger ? Math.max(1, Math.ceil(ledger.pagination.total / PAGE_SIZE)) : 0;

  return (
    <div className="flex flex-1 flex-col gap-6 p-6">
      <div>
        <Link
          href="/marketing/gift-cards"
          className="text-muted-foreground inline-flex items-center gap-1 text-sm hover:underline"
        >
          <ArrowLeft className="size-3.5" />
          Gift cards
        </Link>
      </div>

      <PageHeader
        title={giftCard.masked_display}
        description={giftCard.card_number}
        actions={
          <div className="flex flex-wrap items-center gap-2">
            <StatusBadge
              label={humanize(giftCard.status)}
              tone={GIFT_CARD_STATUS_TONES[giftCard.status]}
            />
            {canAdjust && (
              <Button size="sm" variant="outline" onClick={() => setShowAdjust(true)}>
                Adjust balance
              </Button>
            )}
            {canAdjust &&
              availableActions.map((action) => (
                <Button
                  key={action.key}
                  size="sm"
                  variant={action.key === "cancel" ? "destructive" : "outline"}
                  onClick={() => setConfirmAction(action.key)}
                >
                  {action.label}
                </Button>
              ))}
          </div>
        }
      />

      {error && (
        <p role="alert" className="text-destructive text-sm">
          {error}
        </p>
      )}

      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <StatCard label="Current balance" value={formatMinorUnits(giftCard.current_balance_minor)} />
        <StatCard label="Initial amount" value={formatMinorUnits(giftCard.initial_amount_minor)} />
        <StatCard label="Issued" value={formatDateTime(giftCard.issued_at)} />
        <StatCard label="Expires" value={formatDateTime(giftCard.expires_at)} />
      </div>

      <SectionCard
        title="Redemption code"
        description="Masked by default. Revealing shows the card number and last 4 digits only — the full redemption code is never shown again after issue."
        actions={
          canReveal ? (
            <Button
              size="sm"
              variant="outline"
              disabled={revealCode.isPending}
              onClick={() => {
                setError(null);
                revealCode.mutate(undefined, {
                  onSuccess: (response) => setRevealed(response.data),
                  onError: (err) =>
                    setError(err instanceof ApiError ? err.message : "Could not reveal this code."),
                });
              }}
            >
              <Eye className="size-4" />
              {revealCode.isPending ? "Revealing…" : "Reveal"}
            </Button>
          ) : undefined
        }
      >
        {revealed ? (
          <div className="flex flex-col gap-1">
            <p className="font-mono text-sm">{revealed.card_number}</p>
            <p className="font-mono text-sm">****-****-****-{revealed.code_last4}</p>
          </div>
        ) : (
          <p className="font-mono text-sm">{giftCard.masked_display}</p>
        )}
      </SectionCard>

      <SectionCard title="Purchaser and recipient">
        <dl className="grid grid-cols-1 gap-4 sm:grid-cols-3">
          <Field label="Purchaser customer ID" value={giftCard.purchaser_customer_id ?? "—"} />
          <Field label="Purchaser contact" value={giftCard.purchaser_contact ?? "—"} />
          <Field label="Recipient customer ID" value={giftCard.recipient_customer_id ?? "—"} />
          <Field label="Recipient name" value={giftCard.recipient_name ?? "—"} />
          <Field label="Recipient contact" value={giftCard.recipient_contact ?? "—"} />
          <Field label="Source order" value={giftCard.source_order_id ?? "—"} />
          <Field label="Notes" value={giftCard.notes ?? "—"} />
        </dl>
      </SectionCard>

      <SectionCard title="Ledger" description="Every issue, redemption, adjustment, and reversal.">
        <DataTable
          columns={ledgerColumns}
          data={ledger?.data ?? []}
          getRowId={(row) => row.id}
          loading={ledgerLoading}
          emptyTitle="No ledger entries yet"
          pagination={{
            pageIndex: ledgerPage - 1,
            pageCount: ledgerPageCount,
            total: ledger?.pagination.total ?? 0,
            pageSize: PAGE_SIZE,
            onPageChange: (pageIndex) => setLedgerPage(pageIndex + 1),
          }}
        />
      </SectionCard>

      {canAdjust && (
        <AdjustBalanceModal open={showAdjust} onOpenChange={setShowAdjust} giftCardId={giftCardId} />
      )}

      {reverseTarget && (
        <ReverseLedgerEntryModal
          open={!!reverseTarget}
          onOpenChange={(next) => !next && setReverseTarget(null)}
          entryId={reverseTarget}
        />
      )}

      <ConfirmDialog
        open={!!confirmAction}
        onOpenChange={(next) => !next && setConfirmAction(null)}
        variant={confirmAction === "cancel" ? "danger" : "warning"}
        title={confirmAction ? `${confirmAction[0]!.toUpperCase()}${confirmAction.slice(1)} this gift card?` : ""}
        description="This changes the gift card's status and is recorded for audit history."
        confirmLabel={confirmAction ? confirmAction[0]!.toUpperCase() + confirmAction.slice(1) : "Confirm"}
        onConfirm={async () => {
          if (!confirmAction) return;
          try {
            await actionMutation[confirmAction].mutateAsync({});
          } catch (err) {
            setError(err instanceof ApiError ? err.message : "That action could not be completed.");
          }
        }}
      />
    </div>
  );
}
