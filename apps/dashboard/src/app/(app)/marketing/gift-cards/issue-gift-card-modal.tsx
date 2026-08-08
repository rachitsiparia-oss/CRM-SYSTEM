"use client";

import { useState } from "react";
import { Check, Copy } from "lucide-react";

import { useIssueGiftCard } from "@/lib/hooks/use-gift-cards";
import { ApiError } from "@/lib/api/errors";
import { Modal } from "@/components/modals/modal";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { CurrencyInput } from "@/components/forms/currency-input";

interface IssuedCardResult {
  maskedDisplay: string;
  code: string;
}

export function IssueGiftCardModal({
  open,
  onOpenChange,
}: {
  open: boolean;
  onOpenChange: (open: boolean) => void;
}) {
  const issueGiftCard = useIssueGiftCard();

  const [amountRupees, setAmountRupees] = useState("");
  const [purchaserCustomerId, setPurchaserCustomerId] = useState("");
  const [purchaserContact, setPurchaserContact] = useState("");
  const [recipientCustomerId, setRecipientCustomerId] = useState("");
  const [recipientName, setRecipientName] = useState("");
  const [recipientContact, setRecipientContact] = useState("");
  const [expiresAt, setExpiresAt] = useState("");
  const [notes, setNotes] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<IssuedCardResult | null>(null);
  const [copied, setCopied] = useState(false);

  function reset() {
    setAmountRupees("");
    setPurchaserCustomerId("");
    setPurchaserContact("");
    setRecipientCustomerId("");
    setRecipientName("");
    setRecipientContact("");
    setExpiresAt("");
    setNotes("");
    setError(null);
    setResult(null);
    setCopied(false);
  }

  const canSubmit = amountRupees.trim() && Number(amountRupees) > 0 && !issueGiftCard.isPending;

  if (result) {
    return (
      <Modal
        open={open}
        onOpenChange={(next) => {
          if (!next) reset();
          onOpenChange(next);
        }}
        title="Gift card issued"
        description="This code is shown only once — copy it now. It will only ever be displayed as a masked value after this."
        footer={
          <Button
            onClick={() => {
              reset();
              onOpenChange(false);
            }}
          >
            Done
          </Button>
        }
      >
        <div className="flex flex-col gap-3">
          <p className="text-sm">
            Card: <span className="font-mono">{result.maskedDisplay}</span>
          </p>
          <div className="bg-muted flex items-center justify-between gap-3 rounded-md border p-3">
            <span className="font-mono text-lg font-semibold tracking-wide">{result.code}</span>
            <Button
              type="button"
              size="sm"
              variant="outline"
              onClick={() => {
                void navigator.clipboard.writeText(result.code);
                setCopied(true);
              }}
            >
              {copied ? <Check className="size-4" /> : <Copy className="size-4" />}
              {copied ? "Copied" : "Copy"}
            </Button>
          </div>
          <p className="text-destructive text-xs">
            This is the only time the full code is shown. Give it to the purchaser or recipient now
            — it cannot be retrieved again after you close this dialog.
          </p>
        </div>
      </Modal>
    );
  }

  return (
    <Modal
      open={open}
      onOpenChange={(next) => {
        if (!next) reset();
        onOpenChange(next);
      }}
      title="Issue gift card"
      description="The redemption code is generated on issue and shown exactly once."
      size="lg"
      footer={
        <>
          <Button variant="outline" onClick={() => onOpenChange(false)}>
            Cancel
          </Button>
          <Button
            disabled={!canSubmit}
            onClick={() => {
              setError(null);
              issueGiftCard.mutate(
                {
                  initial_amount_minor: Math.round(Number(amountRupees) * 100),
                  purchaser_customer_id: purchaserCustomerId.trim() || null,
                  purchaser_contact: purchaserContact.trim() || null,
                  recipient_customer_id: recipientCustomerId.trim() || null,
                  recipient_name: recipientName.trim() || null,
                  recipient_contact: recipientContact.trim() || null,
                  expires_at: expiresAt ? new Date(expiresAt).toISOString() : null,
                  notes: notes.trim() || null,
                  idempotency_key: crypto.randomUUID(),
                },
                {
                  onSuccess: (response) => {
                    setResult({
                      maskedDisplay: response.data.gift_card.masked_display,
                      code: response.data.code,
                    });
                  },
                  onError: (err) =>
                    setError(err instanceof ApiError ? err.message : "Could not issue the gift card."),
                },
              );
            }}
          >
            {issueGiftCard.isPending ? "Issuing…" : "Issue gift card"}
          </Button>
        </>
      }
    >
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
        {error && <p className="text-sm text-destructive sm:col-span-2">{error}</p>}
        <div className="flex flex-col gap-1.5">
          <Label htmlFor="gift-card-amount">Amount</Label>
          <CurrencyInput
            id="gift-card-amount"
            value={amountRupees}
            onChange={(e) => setAmountRupees(e.target.value)}
          />
        </div>
        <div className="flex flex-col gap-1.5">
          <Label htmlFor="gift-card-expires">Expires (optional)</Label>
          <Input
            id="gift-card-expires"
            type="date"
            value={expiresAt}
            onChange={(e) => setExpiresAt(e.target.value)}
          />
        </div>
        <div className="flex flex-col gap-1.5">
          <Label htmlFor="gift-card-purchaser-id">Purchaser customer ID</Label>
          <Input
            id="gift-card-purchaser-id"
            value={purchaserCustomerId}
            onChange={(e) => setPurchaserCustomerId(e.target.value)}
          />
        </div>
        <div className="flex flex-col gap-1.5">
          <Label htmlFor="gift-card-purchaser-contact">Purchaser contact</Label>
          <Input
            id="gift-card-purchaser-contact"
            value={purchaserContact}
            onChange={(e) => setPurchaserContact(e.target.value)}
          />
        </div>
        <div className="flex flex-col gap-1.5">
          <Label htmlFor="gift-card-recipient-id">Recipient customer ID</Label>
          <Input
            id="gift-card-recipient-id"
            value={recipientCustomerId}
            onChange={(e) => setRecipientCustomerId(e.target.value)}
          />
        </div>
        <div className="flex flex-col gap-1.5">
          <Label htmlFor="gift-card-recipient-name">Recipient name</Label>
          <Input
            id="gift-card-recipient-name"
            value={recipientName}
            onChange={(e) => setRecipientName(e.target.value)}
          />
        </div>
        <div className="flex flex-col gap-1.5 sm:col-span-2">
          <Label htmlFor="gift-card-recipient-contact">Recipient contact</Label>
          <Input
            id="gift-card-recipient-contact"
            value={recipientContact}
            onChange={(e) => setRecipientContact(e.target.value)}
          />
        </div>
        <div className="flex flex-col gap-1.5 sm:col-span-2">
          <Label htmlFor="gift-card-notes">Notes</Label>
          <Textarea id="gift-card-notes" rows={2} value={notes} onChange={(e) => setNotes(e.target.value)} />
        </div>
      </div>
    </Modal>
  );
}
