"use client";

import { useState } from "react";
import type { CustomerCreditIssueReason } from "@rkpr/contracts";

import { useIssueCustomerCredit } from "@/lib/hooks/use-customer-credit";
import { ApiError } from "@/lib/api/errors";
import { Modal } from "@/components/modals/modal";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { CurrencyInput } from "@/components/forms/currency-input";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";

const ISSUE_REASONS: CustomerCreditIssueReason[] = [
  "service_recovery",
  "refund_as_credit",
  "campaign_reward",
  "referral_reward",
  "achievement_reward",
  "goodwill_adjustment",
  "migration",
];

export function IssueCreditModal({
  open,
  onOpenChange,
  accountId,
}: {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  accountId: string;
}) {
  const issueCredit = useIssueCustomerCredit();

  const [amountRupees, setAmountRupees] = useState("");
  const [issueReason, setIssueReason] = useState<CustomerCreditIssueReason>("service_recovery");
  const [reason, setReason] = useState("");
  const [approvalReference, setApprovalReference] = useState("");
  const [error, setError] = useState<string | null>(null);

  function reset() {
    setAmountRupees("");
    setIssueReason("service_recovery");
    setReason("");
    setApprovalReference("");
    setError(null);
  }

  const canSubmit = amountRupees.trim() && Number(amountRupees) > 0 && !issueCredit.isPending;

  return (
    <Modal
      open={open}
      onOpenChange={(next) => {
        if (!next) reset();
        onOpenChange(next);
      }}
      title="Issue internal credit"
      description="Credits this customer's account. Every issuance is recorded in the ledger."
      footer={
        <>
          <Button variant="outline" onClick={() => onOpenChange(false)}>
            Cancel
          </Button>
          <Button
            disabled={!canSubmit}
            onClick={() => {
              setError(null);
              issueCredit.mutate(
                {
                  account_id: accountId,
                  amount_minor: Math.round(Number(amountRupees) * 100),
                  issue_reason: issueReason,
                  reason: reason.trim() || null,
                  approval_reference: approvalReference.trim() || null,
                  idempotency_key: crypto.randomUUID(),
                },
                {
                  onSuccess: () => {
                    reset();
                    onOpenChange(false);
                  },
                  onError: (err) =>
                    setError(err instanceof ApiError ? err.message : "Could not issue credit."),
                },
              );
            }}
          >
            {issueCredit.isPending ? "Issuing…" : "Issue credit"}
          </Button>
        </>
      }
    >
      <div className="flex flex-col gap-4">
        {error && <p className="text-sm text-red-600">{error}</p>}
        <div className="flex flex-col gap-1.5">
          <Label htmlFor="issue-credit-amount">Amount</Label>
          <CurrencyInput
            id="issue-credit-amount"
            value={amountRupees}
            onChange={(e) => setAmountRupees(e.target.value)}
          />
        </div>
        <div className="flex flex-col gap-1.5">
          <Label>Issue reason</Label>
          <Select value={issueReason} onValueChange={(v) => setIssueReason(v as CustomerCreditIssueReason)}>
            <SelectTrigger>
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              {ISSUE_REASONS.map((r) => (
                <SelectItem key={r} value={r}>
                  {r.replace(/_/g, " ")}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
        <div className="flex flex-col gap-1.5">
          <Label htmlFor="issue-credit-approval">Approval reference (optional)</Label>
          <Input
            id="issue-credit-approval"
            value={approvalReference}
            onChange={(e) => setApprovalReference(e.target.value)}
          />
        </div>
        <div className="flex flex-col gap-1.5">
          <Label htmlFor="issue-credit-reason">Notes (optional)</Label>
          <Textarea id="issue-credit-reason" rows={2} value={reason} onChange={(e) => setReason(e.target.value)} />
        </div>
      </div>
    </Modal>
  );
}
