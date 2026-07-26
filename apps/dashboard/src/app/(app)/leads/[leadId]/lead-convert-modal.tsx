"use client";

import { useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { AlertTriangle, UserPlus } from "lucide-react";

import { useConversionPreview, useConvertLead } from "@/lib/hooks/use-leads";
import { humanize } from "@/lib/crm-display";
import { ApiError } from "@/lib/api/errors";
import { Modal } from "@/components/modals/modal";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { RadioGroup, RadioGroupItem } from "@/components/ui/radio-group";
import { Label } from "@/components/ui/label";

const CREATE_NEW = "__create_new";

export function LeadConvertModal({
  leadId,
  open,
  onOpenChange,
}: {
  leadId: string;
  open: boolean;
  onOpenChange: (open: boolean) => void;
}) {
  const router = useRouter();
  const { data: preview, isLoading, isError } = useConversionPreview(leadId, open);
  const convertLead = useConvertLead(leadId);

  const [choice, setChoice] = useState(CREATE_NEW);
  const [error, setError] = useState<string | null>(null);

  // Minted on the first attempt and reused by every retry until the dialog
  // closes, so a double click, a lost response, or a retry after a network
  // error all resolve to the same customer rather than creating duplicates
  // (CLAUDE.md section 7).
  const idempotencyKey = useRef<string>("");

  const matches = preview?.possible_customer_matches ?? [];

  function handleClose(next: boolean) {
    if (!next) {
      idempotencyKey.current = "";
      setChoice(CREATE_NEW);
      setError(null);
    }
    onOpenChange(next);
  }

  async function handleConvert() {
    setError(null);
    if (!idempotencyKey.current) {
      idempotencyKey.current = crypto.randomUUID();
    }
    try {
      const result = await convertLead.mutateAsync({
        idempotencyKey: idempotencyKey.current,
        existingCustomerId: choice === CREATE_NEW ? null : choice,
      });
      handleClose(false);
      router.push(`/customers/${result.data.id}`);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "The lead could not be converted.");
    }
  }

  return (
    <Modal
      open={open}
      onOpenChange={handleClose}
      title="Convert lead to customer"
      description="The lead and its full history are preserved — converting links it to a customer record rather than replacing it."
      footer={
        <>
          <Button type="button" variant="outline" onClick={() => handleClose(false)}>
            Cancel
          </Button>
          <Button
            onClick={() => void handleConvert()}
            disabled={isLoading || isError || convertLead.isPending}
          >
            {convertLead.isPending ? "Converting…" : "Convert lead"}
          </Button>
        </>
      }
    >
      {isLoading ? (
        <div className="flex flex-col gap-2">
          <Skeleton className="h-5 w-64" />
          <Skeleton className="h-16 w-full" />
        </div>
      ) : isError ? (
        <p className="text-destructive text-sm">
          The conversion preview could not be loaded. Close this dialog and try again.
        </p>
      ) : (
        <div className="flex flex-col gap-4">
          {matches.length > 0 ? (
            <>
              <p className="border-warning/40 bg-warning/10 flex items-start gap-2 rounded-md border p-3 text-sm">
                <AlertTriangle
                  className="text-warning-foreground mt-0.5 size-4 shrink-0"
                  aria-hidden="true"
                />
                <span>
                  {matches.length === 1
                    ? "An existing customer already matches this lead's phone or email."
                    : `${matches.length} existing customers match this lead's phone or email.`}{" "}
                  Link the lead to the existing record instead of creating a duplicate.
                </span>
              </p>

              <RadioGroup value={choice} onValueChange={setChoice} className="gap-3">
                {matches.map((match) => (
                  <div key={match.id} className="flex items-start gap-3 rounded-md border p-3">
                    <RadioGroupItem value={match.id} id={`match-${match.id}`} className="mt-1" />
                    <Label htmlFor={`match-${match.id}`} className="flex flex-col items-start gap-0.5 font-normal">
                      <span className="font-medium">{match.display_name}</span>
                      <span className="text-muted-foreground text-xs">
                        {match.customer_number} · {humanize(match.customer_status)}
                        {match.primary_phone_e164 ? ` · ${match.primary_phone_e164}` : ""}
                        {match.primary_email ? ` · ${match.primary_email}` : ""}
                      </span>
                    </Label>
                  </div>
                ))}
                <div className="flex items-start gap-3 rounded-md border p-3">
                  <RadioGroupItem value={CREATE_NEW} id="match-create-new" className="mt-1" />
                  <Label
                    htmlFor="match-create-new"
                    className="flex flex-col items-start gap-0.5 font-normal"
                  >
                    <span className="flex items-center gap-1.5 font-medium">
                      <UserPlus className="size-3.5" aria-hidden="true" />
                      Create a new customer anyway
                    </span>
                    <span className="text-muted-foreground text-xs">
                      Choose this only if none of the matches above is the same person.
                    </span>
                  </Label>
                </div>
              </RadioGroup>
            </>
          ) : (
            <p className="text-sm">
              No existing customer matches this lead&apos;s phone or email, so a new customer record
              will be created from the lead&apos;s details.
            </p>
          )}

          {error && (
            <p role="alert" className="text-destructive text-sm">
              {error}
            </p>
          )}
        </div>
      )}
    </Modal>
  );
}
