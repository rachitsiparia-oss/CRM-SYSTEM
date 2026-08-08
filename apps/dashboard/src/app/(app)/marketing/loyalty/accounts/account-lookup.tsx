"use client";

import { useMemo, useState } from "react";
import type { ColumnDef } from "@tanstack/react-table";
import type { LoyaltyLedgerEntry, LoyaltyLedgerEntryType } from "@rkpr/contracts";
import { Search, X } from "lucide-react";

import { useCustomerList } from "@/lib/hooks/use-customers";
import { useLoyaltyAccountForCustomer, useLoyaltyLedger, useLoyaltyPrograms } from "@/lib/hooks/use-loyalty";
import { useDebouncedValue } from "@/lib/hooks/use-debounced-value";
import { hasPermission, useCurrentUser } from "@/lib/hooks/use-current-user";
import { LOYALTY_ACCOUNT_STATUS_TONES, formatDateTime, humanize } from "@/lib/crm-display";
import type { StatusTone } from "@/components/status-badge";
import { PageHeader } from "@/components/page-header";
import { StatusBadge } from "@/components/status-badge";
import { DataTable } from "@/components/data-table/data-table";
import { SectionCard } from "@/components/section-card";
import { EmptyState } from "@/components/empty-state";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { EnrollModal } from "./enroll-modal";
import { AdjustPointsModal, EarnPointsModal, RedeemPointsModal } from "./ledger-action-modals";
import { ReverseEntryModal } from "./reverse-entry-modal";
import { AssignTierModal } from "./assign-tier-modal";

const PAGE_SIZE = 20;

const LEDGER_ENTRY_TONE: Record<LoyaltyLedgerEntryType, StatusTone> = {
  earn_order: "success",
  earn_campaign: "success",
  earn_manual: "success",
  redeem_order: "warning",
  redeem_reward: "warning",
  expire: "neutral",
  reverse_earn: "info",
  reverse_redemption: "info",
  service_recovery_credit: "success",
  merge_transfer: "neutral",
  correction: "info",
  referral_reward: "success",
  achievement_reward: "success",
};

export function AccountLookup() {
  const { data: currentUser } = useCurrentUser();
  const [searchInput, setSearchInput] = useState("");
  const [selectedCustomerId, setSelectedCustomerId] = useState<string | null>(null);
  const [selectedCustomerName, setSelectedCustomerName] = useState<string>("");
  const [page, setPage] = useState(1);

  const [showEnroll, setShowEnroll] = useState(false);
  const [showEarn, setShowEarn] = useState(false);
  const [showRedeem, setShowRedeem] = useState(false);
  const [showAdjust, setShowAdjust] = useState(false);
  const [showAssignTier, setShowAssignTier] = useState(false);
  const [reverseEntryId, setReverseEntryId] = useState<string | null>(null);

  const search = useDebouncedValue(searchInput);
  const { data: customerResults } = useCustomerList({
    page: 1,
    pageSize: 8,
    search: search.length >= 2 ? search : undefined,
  });
  const { data: programs } = useLoyaltyPrograms();

  const {
    data: account,
    isLoading: accountLoading,
    isError: accountError,
  } = useLoyaltyAccountForCustomer(selectedCustomerId ?? undefined);

  const { data: ledger, isLoading: ledgerLoading } = useLoyaltyLedger(account?.id, {
    page,
    pageSize: PAGE_SIZE,
  });

  const canManage = hasPermission(currentUser, "loyalty.manage");
  const canAdjust = hasPermission(currentUser, "loyalty.adjust");
  const canReverse = hasPermission(currentUser, "loyalty.reverse");
  const canManageTiers = hasPermission(currentUser, "loyalty.tiers.manage");

  const program = programs?.find((p) => p.id === account?.program_id);

  const columns = useMemo<ColumnDef<LoyaltyLedgerEntry, unknown>[]>(
    () => [
      {
        id: "entry_type",
        header: "Type",
        enableSorting: false,
        cell: ({ row }) => (
          <StatusBadge
            label={humanize(row.original.entry_type)}
            tone={LEDGER_ENTRY_TONE[row.original.entry_type]}
          />
        ),
      },
      {
        id: "points_delta",
        header: "Points",
        enableSorting: false,
        cell: ({ row }) => (
          <span
            className={row.original.points_delta < 0 ? "font-medium text-destructive" : "font-medium text-success"}
          >
            {row.original.points_delta > 0 ? "+" : ""}
            {row.original.points_delta}
          </span>
        ),
      },
      {
        id: "balance_after",
        header: "Balance after",
        enableSorting: false,
        cell: ({ row }) => <span className="text-sm">{row.original.balance_after}</span>,
      },
      {
        id: "description",
        header: "Description",
        enableSorting: false,
        cell: ({ row }) => (
          <span className="text-muted-foreground text-sm">{row.original.description ?? "—"}</span>
        ),
      },
      {
        id: "effective_at",
        header: "Effective at",
        enableSorting: false,
        cell: ({ row }) => <span className="text-sm">{formatDateTime(row.original.effective_at)}</span>,
      },
      {
        id: "actions",
        header: "",
        enableSorting: false,
        cell: ({ row }) =>
          canReverse && !row.original.reversal_of_id ? (
            <Button size="sm" variant="ghost" onClick={() => setReverseEntryId(row.original.id)}>
              Reverse
            </Button>
          ) : null,
      },
    ],
    [canReverse],
  );

  const pageCount = ledger ? Math.max(1, Math.ceil(ledger.pagination.total / PAGE_SIZE)) : 0;

  function selectCustomer(id: string, name: string) {
    setSelectedCustomerId(id);
    setSelectedCustomerName(name);
    setSearchInput("");
    setPage(1);
  }

  return (
    <div className="flex flex-1 flex-col gap-6 p-6">
      <PageHeader
        title="Member accounts"
        description="Look up a customer's loyalty account, points ledger, and lifetime activity."
      />

      <SectionCard title="Find a customer" description="Search by name, phone, or customer number.">
        <div className="flex flex-col gap-2">
          {selectedCustomerId ? (
            <div className="flex items-center gap-2">
              <span className="text-sm font-medium">{selectedCustomerName}</span>
              <Button
                size="sm"
                variant="ghost"
                onClick={() => {
                  setSelectedCustomerId(null);
                  setSelectedCustomerName("");
                }}
              >
                <X className="size-3.5" />
                Change customer
              </Button>
            </div>
          ) : (
            <div className="relative max-w-sm">
              <Search className="text-muted-foreground absolute top-2.5 left-2.5 size-4" />
              <Input
                className="pl-8"
                value={searchInput}
                onChange={(e) => setSearchInput(e.target.value)}
                placeholder="Search customers…"
              />
              {search.length >= 2 && (customerResults?.data.length ?? 0) > 0 && (
                <div className="bg-background absolute z-10 mt-1 w-full rounded-md border shadow-md">
                  {customerResults?.data.map((customer) => (
                    <button
                      key={customer.id}
                      type="button"
                      className="hover:bg-muted flex w-full flex-col items-start px-3 py-2 text-left text-sm"
                      onClick={() => selectCustomer(customer.id, customer.display_name)}
                    >
                      <span className="font-medium">{customer.display_name}</span>
                      <span className="text-muted-foreground text-xs">
                        {customer.customer_number}
                        {customer.primary_phone_e164 ? ` · ${customer.primary_phone_e164}` : ""}
                      </span>
                    </button>
                  ))}
                </div>
              )}
            </div>
          )}
        </div>
      </SectionCard>

      {selectedCustomerId && (
        <SectionCard
          title="Loyalty account"
          description={program ? `${program.name} (${program.code})` : undefined}
        >
          {accountLoading ? (
            <p className="text-muted-foreground text-sm">Loading…</p>
          ) : accountError ? (
            <p className="text-sm text-destructive">Could not load this customer&rsquo;s loyalty account.</p>
          ) : !account ? (
            <EmptyState
              title="Not enrolled"
              description="This customer has no loyalty account yet."
              action={
                canManage ? (
                  <Button size="sm" onClick={() => setShowEnroll(true)}>
                    Enroll
                  </Button>
                ) : undefined
              }
            />
          ) : (
            <div className="flex flex-col gap-4">
              <div className="flex flex-wrap items-center justify-between gap-3">
                <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
                  <div>
                    <p className="text-muted-foreground text-xs">Status</p>
                    <StatusBadge
                      label={humanize(account.status)}
                      tone={LOYALTY_ACCOUNT_STATUS_TONES[account.status]}
                    />
                  </div>
                  <div>
                    <p className="text-muted-foreground text-xs">Points balance</p>
                    <p className="text-lg font-semibold">{account.points_balance}</p>
                  </div>
                  <div>
                    <p className="text-muted-foreground text-xs">Lifetime earned</p>
                    <p className="text-sm font-medium">{account.lifetime_points_earned}</p>
                  </div>
                  <div>
                    <p className="text-muted-foreground text-xs">Lifetime redeemed</p>
                    <p className="text-sm font-medium">{account.lifetime_points_redeemed}</p>
                  </div>
                </div>
                <div className="flex flex-wrap gap-2">
                  {canAdjust && (
                    <>
                      <Button size="sm" variant="outline" onClick={() => setShowEarn(true)}>
                        Earn points
                      </Button>
                      <Button size="sm" variant="outline" onClick={() => setShowRedeem(true)}>
                        Redeem points
                      </Button>
                      <Button size="sm" variant="outline" onClick={() => setShowAdjust(true)}>
                        Adjust points
                      </Button>
                    </>
                  )}
                  {canManageTiers && (
                    <Button size="sm" variant="outline" onClick={() => setShowAssignTier(true)}>
                      Assign tier
                    </Button>
                  )}
                </div>
              </div>

              <DataTable
                columns={columns}
                data={ledger?.data ?? []}
                getRowId={(row) => row.id}
                loading={ledgerLoading}
                emptyTitle="No ledger entries yet"
                emptyDescription="Points activity for this account will appear here."
                pagination={{
                  pageIndex: page - 1,
                  pageCount,
                  total: ledger?.pagination.total ?? 0,
                  pageSize: PAGE_SIZE,
                  onPageChange: (pageIndex) => setPage(pageIndex + 1),
                }}
              />
            </div>
          )}
        </SectionCard>
      )}

      {selectedCustomerId && (
        <EnrollModal customerId={selectedCustomerId} open={showEnroll} onOpenChange={setShowEnroll} />
      )}
      {account && (
        <>
          <EarnPointsModal accountId={account.id} open={showEarn} onOpenChange={setShowEarn} />
          <RedeemPointsModal accountId={account.id} open={showRedeem} onOpenChange={setShowRedeem} />
          <AdjustPointsModal accountId={account.id} open={showAdjust} onOpenChange={setShowAdjust} />
          <AssignTierModal
            accountId={account.id}
            programId={account.program_id}
            open={showAssignTier}
            onOpenChange={setShowAssignTier}
          />
        </>
      )}
      <ReverseEntryModal
        entryId={reverseEntryId}
        open={!!reverseEntryId}
        onOpenChange={(open) => {
          if (!open) setReverseEntryId(null);
        }}
      />
    </div>
  );
}
