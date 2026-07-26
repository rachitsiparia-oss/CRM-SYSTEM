"use client";

import { useState } from "react";
import { Wallet } from "lucide-react";

import { useAddOrderPayment, useOrderPayments, useUpdateOrderPaymentStatus } from "@/lib/hooks/use-orders";
import { hasPermission, useCurrentUser } from "@/lib/hooks/use-current-user";
import { formatDateTime, formatMinorUnits, humanize, PAYMENT_STATUS_TONES } from "@/lib/crm-display";
import { ApiError } from "@/lib/api/errors";
import { SectionCard } from "@/components/section-card";
import { FormField } from "@/components/forms/form-field";
import { CurrencyInput } from "@/components/forms/currency-input";
import { EmptyState } from "@/components/empty-state";
import { CardSkeleton } from "@/components/skeletons/card-skeleton";
import { StatusBadge } from "@/components/status-badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";

const METHODS = ["cash", "card", "upi", "online"];
const STATUSES = ["pending", "partial", "paid", "refunded", "failed"];

function toMinorUnits(rupees: string): number {
  const parsed = Number(rupees);
  if (!Number.isFinite(parsed) || parsed < 0) return 0;
  return Math.round(parsed * 100);
}

export function OrderPaymentsTab({ orderId }: { orderId: string }) {
  const { data: currentUser } = useCurrentUser();
  const { data: payments, isLoading } = useOrderPayments(orderId);
  const addPayment = useAddOrderPayment(orderId);
  const updateStatus = useUpdateOrderPaymentStatus(orderId);

  const [method, setMethod] = useState("cash");
  const [status, setStatus] = useState("paid");
  const [amountRupees, setAmountRupees] = useState("");
  const [reference, setReference] = useState("");
  const [error, setError] = useState<string | null>(null);

  const canManage = hasPermission(currentUser, "orders.payments.manage");

  async function handleAddPayment() {
    setError(null);
    try {
      await addPayment.mutateAsync({
        method,
        status,
        amountMinor: toMinorUnits(amountRupees),
        reference: reference.trim() || undefined,
      });
      setAmountRupees("");
      setReference("");
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "The payment could not be recorded.");
    }
  }

  return (
    <div className="flex flex-col gap-4">
      {canManage && (
        <SectionCard title="Record a payment" description="No payment gateway — this records a payment already collected.">
          <div className="flex flex-wrap items-end gap-3">
            <FormField label="Method" htmlFor="payment-method">
              <Select value={method} onValueChange={setMethod}>
                <SelectTrigger id="payment-method" className="w-32">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {METHODS.map((option) => (
                    <SelectItem key={option} value={option}>
                      {humanize(option)}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </FormField>

            <FormField label="Status" htmlFor="payment-status">
              <Select value={status} onValueChange={setStatus}>
                <SelectTrigger id="payment-status" className="w-32">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {STATUSES.map((option) => (
                    <SelectItem key={option} value={option}>
                      {humanize(option)}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </FormField>

            <FormField label="Amount" htmlFor="payment-amount" className="w-32">
              <CurrencyInput
                id="payment-amount"
                value={amountRupees}
                onChange={(e) => setAmountRupees(e.target.value)}
              />
            </FormField>

            <FormField label="Reference (optional)" htmlFor="payment-reference" className="min-w-48 flex-1">
              <Input
                id="payment-reference"
                value={reference}
                onChange={(e) => setReference(e.target.value)}
                placeholder="UPI transaction ID, receipt number…"
              />
            </FormField>

            <Button disabled={!amountRupees || addPayment.isPending} onClick={() => void handleAddPayment()}>
              {addPayment.isPending ? "Recording…" : "Record payment"}
            </Button>
          </div>
          {error && (
            <p role="alert" className="text-destructive mt-3 text-sm">
              {error}
            </p>
          )}
        </SectionCard>
      )}

      <SectionCard title="Payment history">
        {isLoading ? (
          <CardSkeleton />
        ) : !payments || payments.length === 0 ? (
          <EmptyState icon={Wallet} title="No payments recorded" description="Payments will appear here once recorded." />
        ) : (
          <div className="flex flex-col gap-3">
            {payments.map((payment) => (
              <div key={payment.id} className="flex items-center justify-between gap-3 rounded-md border p-3">
                <div>
                  <p className="text-sm font-medium">
                    {formatMinorUnits(payment.amount_minor)} via {humanize(payment.method)}
                  </p>
                  <p className="text-muted-foreground text-xs">
                    {formatDateTime(payment.recorded_at)}
                    {payment.reference ? ` · ${payment.reference}` : ""}
                  </p>
                </div>
                <div className="flex items-center gap-2">
                  <StatusBadge label={humanize(payment.status)} tone={PAYMENT_STATUS_TONES[payment.status]} />
                  {canManage && (
                    <Select
                      value={payment.status}
                      onValueChange={(value) => updateStatus.mutate({ paymentId: payment.id, status: value })}
                    >
                      <SelectTrigger className="w-32" aria-label="Update payment status">
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        {STATUSES.map((option) => (
                          <SelectItem key={option} value={option}>
                            {humanize(option)}
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  )}
                </div>
              </div>
            ))}
          </div>
        )}
      </SectionCard>
    </div>
  );
}
