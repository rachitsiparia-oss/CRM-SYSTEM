"use client";

import { useState } from "react";
import type { CommunicationPreference } from "@rkpr/contracts";

import {
  useCommunicationPreference,
  useUpdateCommunicationPreference,
} from "@/lib/hooks/use-communications";
import { hasPermission, useCurrentUser } from "@/lib/hooks/use-current-user";
import { ApiError } from "@/lib/api/errors";
import { SectionCard } from "@/components/section-card";
import { CardSkeleton } from "@/components/skeletons/card-skeleton";
import { Button } from "@/components/ui/button";
import { Checkbox } from "@/components/ui/checkbox";

const CHANNELS = [
  { key: "email", label: "Email" },
  { key: "sms", label: "SMS" },
  { key: "whatsapp", label: "WhatsApp" },
] as const;

/** Keyed by `preference.id` from the parent so a fresh instance mounts —
 * and re-initializes its local editing state straight from props — every
 * time the loaded preference changes, instead of syncing state from a prop
 * in a `useEffect` (React Compiler flags synchronous setState-in-effect as
 * cascading-render-prone). */
function PreferenceEditor({
  preference,
  customerId,
  canManage,
}: {
  preference: CommunicationPreference;
  customerId: string;
  canManage: boolean;
}) {
  const updatePreference = useUpdateCommunicationPreference(customerId);
  const [doNotContact, setDoNotContact] = useState(preference.do_not_contact);
  const [transactional, setTransactional] = useState<Record<string, boolean>>({
    email: preference.allow_transactional_email,
    sms: preference.allow_transactional_sms,
    whatsapp: preference.allow_transactional_whatsapp,
  });
  const [promotional, setPromotional] = useState<Record<string, boolean>>({
    email: preference.allow_promotional_email,
    sms: preference.allow_promotional_sms,
    whatsapp: preference.allow_promotional_whatsapp,
  });
  const [error, setError] = useState<string | null>(null);

  async function handleSave() {
    setError(null);
    try {
      await updatePreference.mutateAsync({
        do_not_contact: doNotContact,
        allow_transactional_email: transactional.email,
        allow_transactional_sms: transactional.sms,
        allow_transactional_whatsapp: transactional.whatsapp,
        allow_promotional_email: promotional.email,
        allow_promotional_sms: promotional.sms,
        allow_promotional_whatsapp: promotional.whatsapp,
      });
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Preferences could not be saved.");
    }
  }

  return (
    <SectionCard
      title="Preferences"
      description="Marketing opt-out never blocks essential transactional messages unless do-not-contact is set."
    >
      <label className="mb-4 flex items-center gap-2 text-sm font-medium">
        <Checkbox
          checked={doNotContact}
          onCheckedChange={(checked) => setDoNotContact(checked === true)}
          disabled={!canManage}
        />
        Do not contact (overrides everything below)
      </label>

      <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
        {CHANNELS.map((channel) => (
          <div key={channel.key} className="rounded-md border p-3">
            <p className="mb-2 text-sm font-medium">{channel.label}</p>
            <label className="mb-2 flex items-center gap-2 text-sm">
              <Checkbox
                checked={transactional[channel.key] ?? false}
                onCheckedChange={(checked) =>
                  setTransactional((prev) => ({ ...prev, [channel.key]: checked === true }))
                }
                disabled={!canManage}
              />
              Transactional
            </label>
            <label className="flex items-center gap-2 text-sm">
              <Checkbox
                checked={promotional[channel.key] ?? false}
                onCheckedChange={(checked) =>
                  setPromotional((prev) => ({ ...prev, [channel.key]: checked === true }))
                }
                disabled={!canManage}
              />
              Promotional
            </label>
          </div>
        ))}
      </div>

      {canManage && (
        <div className="mt-4 flex justify-end">
          <Button disabled={updatePreference.isPending} onClick={() => void handleSave()}>
            {updatePreference.isPending ? "Saving…" : "Save preferences"}
          </Button>
        </div>
      )}
      {error && (
        <p role="alert" className="text-destructive mt-3 text-sm">
          {error}
        </p>
      )}
    </SectionCard>
  );
}

export function CustomerPreferenceForm({ customerId }: { customerId: string }) {
  const { data: currentUser } = useCurrentUser();
  const { data: preference, isLoading } = useCommunicationPreference(customerId);
  const canManage = hasPermission(currentUser, "communications.preferences.manage");

  if (isLoading) return <CardSkeleton />;
  if (!preference) return null;

  return (
    <PreferenceEditor
      key={preference.id}
      preference={preference}
      customerId={customerId}
      canManage={canManage}
    />
  );
}
