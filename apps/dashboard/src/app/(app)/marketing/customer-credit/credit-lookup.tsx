"use client";

import { useState } from "react";
import type { ColumnDef } from "@tanstack/react-table";
import type { CustomerCreditLedgerEntry } from "@rkpr/contracts";
import { Search } from "lucide-react";

import {
  useCustomerCreditAccount,
  useCustomerCreditAnalytics,
  useCustomerCreditLedger,
  useEnsureCustomerCreditAccount,
} from "@/lib/hooks/use-customer-credit";
import { hasPermission, useCurrentUser } from "@/lib/hooks/use-current-user";
import {
  CUSTOMER_CREDIT_ACCOUNT_STATUS_TONES,
  formatDateTime,
  formatMinorUnits,
  humanize,
} from "@/lib/crm-display";
import { ApiError } from "@/lib/api/errors";
import { PageHeader } from "@/components/page-header";
import { EmptyState } from "@/components/empty-state";
import { ErrorState } from "@/components/error-state";
import { StatusBadge, type StatusTone } from "@/components/status-badge";
import { SectionCard } from "@/components/section-card";
import { StatCard } from "@/components/stat-card";
import { DataTable } from "@/components/data-table/data-table";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { IssueCreditModal } from "./issue-credit-modal";
import { RedeemCreditModal } from "./redeem-credit-modal";
import { AdjustCreditModal } from "./adjust-credit-modal";
import { ReverseCreditEntryModal } from "./reverse-credit-entry-modal";

const LEDGER_ENTRY_TONES: Record<CustomerCreditLedgerEntry["entry_type"], StatusTone> = {
  issue: "info",
  redeem: "info",
  reverse: "warning",
  adjust: "warning",
  expire: "neutral",
  migration: "neutral",
};

const PAGE_SIZE = 20;

export function CreditLookup() {
  const { data: currentUser } = useCurrentUser();
  const [customerIdInput, setCustomerIdInput] = useState("");
  const [customerId, setCustomerId] = useState<string | undefined>(undefined);
  const [ledgerPage, setLedgerPage] = useState(1);
  const [error, setError] = useState<string | null>(null);
  const [showIssue, setShowIssue] = useState(false);
  const [showRedeem, setShowRedeem] = useState(false);
  const [showAdjust, setShowAdjust] = useState(false);
  const [reverseTarget, setReverseTarget] = useState<string | null>(null);

  const canIssue = hasPermission(currentUser, "customer_credit.issue");
  const canAdjust = hasPermission(currentUser, "customer_credit.adjust");
  const canReverse = hasPermission(currentUser, "customer_credit.reverse");
  const canViewAnalytics = hasPermission(currentUser, "customer_credit.analytics.view");

  const { data: analytics, isLoading: analyticsLoading } = useCustomerCreditAnalytics();
  const { data: account, isLoading, isError, refetch } = useCustomerCreditAccount(customerId);
  const ensureAccount = useEnsureCustomerCreditAccount();

  const { data: ledger, isLoading: ledgerLoading } = useCustomerCreditLedger(account?.id, {
    page: ledgerPage,
    pageSize: PAGE_SIZE,
  });

  const ledgerColumns: ColumnDef<CustomerCreditLedgerEntry, unknown>[] = [
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
      id: "issue_reason",
      header: "Reason",
      enableSorting: false,
      cell: ({ row }) => (
        <span className="text-sm">
          {row.original.issue_reason ? humanize(row.original.issue_reason) : (row.original.reason ?? "—")}
        </span>
      ),
    },
    {
      id: "amount",
      header: "Amount",
      enableSorting: false,
      cell: ({ row }) => <span className="text-sm">{formatMinorUnits(row.original.amount_delta_minor)}</span>,
    },
    {
      id: "balance_after",
      header: "Balance after",
      enableSorting: false,
      cell: ({ row }) => <span className="text-sm">{formatMinorUnits(row.original.balance_after_minor)}</span>,
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
      <PageHeader
        title="Internal customer credit"
        description="Look up a customer's internal credit account, issue, redeem, or adjust their balance."
      />

      {canViewAnalytics && (
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
          <StatCard label="Active accounts" value={analytics?.active_accounts ?? 0} loading={analyticsLoading} />
          <StatCard
            label="Outstanding liability"
            value={formatMinorUnits(analytics?.outstanding_liability_minor)}
            loading={analyticsLoading}
          />
          <StatCard
            label="Issued (30d)"
            value={formatMinorUnits(analytics?.issued_30d_minor)}
            loading={analyticsLoading}
          />
          <StatCard
            label="Redeemed (30d)"
            value={formatMinorUnits(analytics?.redeemed_30d_minor)}
            loading={analyticsLoading}
          />
        </div>
      )}

      <SectionCard title="Look up account">
        <form
          className="flex flex-wrap items-end gap-3"
          onSubmit={(e) => {
            e.preventDefault();
            setError(null);
            setLedgerPage(1);
            setCustomerId(customerIdInput.trim() || undefined);
          }}
        >
          <div className="flex flex-col gap-1.5">
            <Label htmlFor="credit-customer-id">Customer ID</Label>
            <Input
              id="credit-customer-id"
              className="w-80"
              value={customerIdInput}
              onChange={(e) => setCustomerIdInput(e.target.value)}
              placeholder="Customer UUID"
            />
          </div>
          <Button type="submit" disabled={!customerIdInput.trim()}>
            <Search className="size-4" />
            Look up
          </Button>
        </form>
      </SectionCard>

      {error && (
        <p role="alert" className="text-destructive text-sm">
          {error}
        </p>
      )}

      {!customerId ? (
        <EmptyState title="Enter a customer ID to view their credit account" />
      ) : isLoading ? (
        <SectionCard title="Loading…">
          <p className="text-muted-foreground text-sm">Loading account…</p>
        </SectionCard>
      ) : isError ? (
        <ErrorState title="Could not load this customer's credit account" onRetry={() => void refetch()} />
      ) : !account ? (
        <EmptyState
          title="No credit account found"
          description="This customer does not have an internal credit account yet."
          action={
            canIssue ? (
              <Button
                disabled={ensureAccount.isPending}
                onClick={() => {
                  setError(null);
                  ensureAccount.mutate(customerId, {
                    onError: (err) =>
                      setError(err instanceof ApiError ? err.message : "Could not open an account."),
                  });
                }}
              >
                {ensureAccount.isPending ? "Opening…" : "Open account"}
              </Button>
            ) : undefined
          }
        />
      ) : (
        <>
          <SectionCard
            title="Account"
            actions={
              <div className="flex flex-wrap gap-2">
                <StatusBadge
                  label={humanize(account.status)}
                  tone={CUSTOMER_CREDIT_ACCOUNT_STATUS_TONES[account.status]}
                />
                {canIssue && (
                  <Button size="sm" variant="outline" onClick={() => setShowRedeem(true)}>
                    Redeem
                  </Button>
                )}
                {canIssue && (
                  <Button size="sm" onClick={() => setShowIssue(true)}>
                    Issue credit
                  </Button>
                )}
                {canAdjust && (
                  <Button size="sm" variant="outline" onClick={() => setShowAdjust(true)}>
                    Adjust
                  </Button>
                )}
              </div>
            }
          >
            <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
              <StatCard label="Current balance" value={formatMinorUnits(account.current_balance_minor)} />
              <StatCard label="Account ID" value={account.id.slice(0, 8) + "…"} />
              <StatCard label="Opened" value={formatDateTime(account.created_at)} />
            </div>
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

          {canIssue && (
            <>
              <IssueCreditModal open={showIssue} onOpenChange={setShowIssue} accountId={account.id} />
              <RedeemCreditModal
                open={showRedeem}
                onOpenChange={setShowRedeem}
                accountId={account.id}
                availableBalanceMinor={account.current_balance_minor}
              />
            </>
          )}
          {canAdjust && (
            <AdjustCreditModal open={showAdjust} onOpenChange={setShowAdjust} accountId={account.id} />
          )}
          {reverseTarget && (
            <ReverseCreditEntryModal
              open={!!reverseTarget}
              onOpenChange={(next) => !next && setReverseTarget(null)}
              entryId={reverseTarget}
            />
          )}
        </>
      )}
    </div>
  );
}
