"use client";

import { useState } from "react";
import type { ReservationPolicies, ReservationSettings } from "@rkpr/contracts";

import {
  useReservationPolicies,
  useReservationSettings,
  useUpdateReservationPolicies,
  useUpdateReservationSettings,
} from "@/lib/hooks/use-reservations";
import { hasPermission, useCurrentUser } from "@/lib/hooks/use-current-user";
import { ApiError } from "@/lib/api/errors";
import { PageHeader } from "@/components/page-header";
import { SectionCard } from "@/components/section-card";
import { FormField } from "@/components/forms/form-field";
import { CardSkeleton } from "@/components/skeletons/card-skeleton";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Checkbox } from "@/components/ui/checkbox";

export function ReservationSettingsEditor() {
  const { data: currentUser } = useCurrentUser();
  const canManage = hasPermission(currentUser, "reservations.settings.manage");

  return (
    <div className="flex flex-1 flex-col gap-4 p-6">
      <PageHeader
        title="Reservation Settings"
        description="Booking policies and operational toggles for the reservation engines."
      />
      <PoliciesForm canManage={canManage} />
      <SettingsForm canManage={canManage} />
    </div>
  );
}

function PoliciesForm({ canManage }: { canManage: boolean }) {
  const { data: policies, isLoading } = useReservationPolicies();

  if (isLoading || !policies) {
    return (
      <SectionCard title="Booking policies">
        <CardSkeleton />
      </SectionCard>
    );
  }

  // Keyed by id: this only ever mounts once real data exists, so the local
  // editable state below can be a plain lazy useState initializer — no
  // effect needed to sync it in after the query resolves.
  return <PoliciesFormFields key={policies.id} policies={policies} canManage={canManage} />;
}

function PoliciesFormFields({
  policies,
  canManage,
}: {
  policies: ReservationPolicies;
  canManage: boolean;
}) {
  const update = useUpdateReservationPolicies();
  const [values, setValues] = useState({
    depositRequiredByDefault: policies.deposit_required_by_default,
    advanceBookingLimitDays: String(policies.advance_booking_limit_days),
    minimumNoticeMinutes: String(policies.minimum_notice_minutes),
    cancellationWindowMinutes: String(policies.cancellation_window_minutes),
    noShowGraceMinutes: String(policies.no_show_grace_minutes),
    bufferBeforeMinutes: String(policies.buffer_before_minutes),
    bufferAfterMinutes: String(policies.buffer_after_minutes),
    defaultMinimumPartySize: String(policies.default_minimum_party_size),
    defaultMaximumPartySize: String(policies.default_maximum_party_size),
    largePartyThreshold: String(policies.large_party_threshold),
  });
  const [error, setError] = useState<string | null>(null);

  async function save() {
    setError(null);
    try {
      await update.mutateAsync({
        deposit_required_by_default: values.depositRequiredByDefault,
        advance_booking_limit_days: Number(values.advanceBookingLimitDays),
        minimum_notice_minutes: Number(values.minimumNoticeMinutes),
        cancellation_window_minutes: Number(values.cancellationWindowMinutes),
        no_show_grace_minutes: Number(values.noShowGraceMinutes),
        buffer_before_minutes: Number(values.bufferBeforeMinutes),
        buffer_after_minutes: Number(values.bufferAfterMinutes),
        default_minimum_party_size: Number(values.defaultMinimumPartySize),
        default_maximum_party_size: Number(values.defaultMaximumPartySize),
        large_party_threshold: Number(values.largePartyThreshold),
        expected_version: policies.version,
      });
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "These policies could not be saved.");
    }
  }

  return (
    <SectionCard
      title="Booking policies"
      description="Thresholds enforced by the availability and assignment engines."
    >
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
        <FormField label="Advance booking limit (days)" htmlFor="policy-advance-limit">
          <Input
            id="policy-advance-limit"
            inputMode="numeric"
            disabled={!canManage}
            value={values.advanceBookingLimitDays}
            onChange={(e) => setValues((v) => ({ ...v, advanceBookingLimitDays: e.target.value }))}
          />
        </FormField>
        <FormField label="Minimum notice (minutes)" htmlFor="policy-minimum-notice">
          <Input
            id="policy-minimum-notice"
            inputMode="numeric"
            disabled={!canManage}
            value={values.minimumNoticeMinutes}
            onChange={(e) => setValues((v) => ({ ...v, minimumNoticeMinutes: e.target.value }))}
          />
        </FormField>
        <FormField label="Cancellation window (minutes)" htmlFor="policy-cancellation-window">
          <Input
            id="policy-cancellation-window"
            inputMode="numeric"
            disabled={!canManage}
            value={values.cancellationWindowMinutes}
            onChange={(e) =>
              setValues((v) => ({ ...v, cancellationWindowMinutes: e.target.value }))
            }
          />
        </FormField>
        <FormField label="No-show grace (minutes)" htmlFor="policy-no-show-grace">
          <Input
            id="policy-no-show-grace"
            inputMode="numeric"
            disabled={!canManage}
            value={values.noShowGraceMinutes}
            onChange={(e) => setValues((v) => ({ ...v, noShowGraceMinutes: e.target.value }))}
          />
        </FormField>
        <FormField label="Buffer before (minutes)" htmlFor="policy-buffer-before">
          <Input
            id="policy-buffer-before"
            inputMode="numeric"
            disabled={!canManage}
            value={values.bufferBeforeMinutes}
            onChange={(e) => setValues((v) => ({ ...v, bufferBeforeMinutes: e.target.value }))}
          />
        </FormField>
        <FormField label="Buffer after (minutes)" htmlFor="policy-buffer-after">
          <Input
            id="policy-buffer-after"
            inputMode="numeric"
            disabled={!canManage}
            value={values.bufferAfterMinutes}
            onChange={(e) => setValues((v) => ({ ...v, bufferAfterMinutes: e.target.value }))}
          />
        </FormField>
        <FormField label="Default minimum party size" htmlFor="policy-min-party">
          <Input
            id="policy-min-party"
            inputMode="numeric"
            disabled={!canManage}
            value={values.defaultMinimumPartySize}
            onChange={(e) => setValues((v) => ({ ...v, defaultMinimumPartySize: e.target.value }))}
          />
        </FormField>
        <FormField label="Default maximum party size" htmlFor="policy-max-party">
          <Input
            id="policy-max-party"
            inputMode="numeric"
            disabled={!canManage}
            value={values.defaultMaximumPartySize}
            onChange={(e) => setValues((v) => ({ ...v, defaultMaximumPartySize: e.target.value }))}
          />
        </FormField>
        <FormField
          label="Large party threshold"
          htmlFor="policy-large-party"
          description="Above this size, guests are routed to leads/events instead of a standard reservation."
        >
          <Input
            id="policy-large-party"
            inputMode="numeric"
            disabled={!canManage}
            value={values.largePartyThreshold}
            onChange={(e) => setValues((v) => ({ ...v, largePartyThreshold: e.target.value }))}
          />
        </FormField>
      </div>
      <label className="mt-4 flex items-center gap-2 text-sm">
        <Checkbox
          checked={values.depositRequiredByDefault}
          disabled={!canManage}
          onCheckedChange={(checked) =>
            setValues((v) => ({ ...v, depositRequiredByDefault: checked === true }))
          }
        />
        Require a deposit by default
      </label>

      {canManage && (
        <div className="mt-4 flex justify-end">
          <Button disabled={update.isPending} onClick={() => void save()}>
            {update.isPending ? "Saving…" : "Save policies"}
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

function SettingsForm({ canManage }: { canManage: boolean }) {
  const { data: settings, isLoading } = useReservationSettings();

  if (isLoading || !settings) {
    return (
      <SectionCard title="Operational settings">
        <CardSkeleton />
      </SectionCard>
    );
  }

  return <SettingsFormFields key={settings.id} settings={settings} canManage={canManage} />;
}

function SettingsFormFields({
  settings,
  canManage,
}: {
  settings: ReservationSettings;
  canManage: boolean;
}) {
  const update = useUpdateReservationSettings();
  const [values, setValues] = useState({
    defaultReservationDurationMinutes: String(settings.default_reservation_duration_minutes),
    autoAssignmentEnabled: settings.auto_assignment_enabled,
    waitlistEnabled: settings.waitlist_enabled,
    onlineBookingEnabled: settings.online_booking_enabled,
    walkInEnabled: settings.walk_in_enabled,
    pendingRequestExpiryMinutes: settings.pending_request_expiry_minutes
      ? String(settings.pending_request_expiry_minutes)
      : "",
    reminderLeadTimeMinutes: settings.reminder_lead_time_minutes
      ? String(settings.reminder_lead_time_minutes)
      : "",
  });
  const [error, setError] = useState<string | null>(null);

  async function save() {
    setError(null);
    try {
      await update.mutateAsync({
        default_reservation_duration_minutes: Number(values.defaultReservationDurationMinutes),
        auto_assignment_enabled: values.autoAssignmentEnabled,
        waitlist_enabled: values.waitlistEnabled,
        online_booking_enabled: values.onlineBookingEnabled,
        walk_in_enabled: values.walkInEnabled,
        pending_request_expiry_minutes: values.pendingRequestExpiryMinutes
          ? Number(values.pendingRequestExpiryMinutes)
          : null,
        reminder_lead_time_minutes: values.reminderLeadTimeMinutes
          ? Number(values.reminderLeadTimeMinutes)
          : null,
        expected_version: settings.version,
      });
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "These settings could not be saved.");
    }
  }

  return (
    <SectionCard
      title="Operational settings"
      description="Feature toggles and timing for the reservation engines."
    >
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
        <FormField label="Default reservation duration (minutes)" htmlFor="settings-default-duration">
          <Input
            id="settings-default-duration"
            inputMode="numeric"
            disabled={!canManage}
            value={values.defaultReservationDurationMinutes}
            onChange={(e) =>
              setValues((v) => ({ ...v, defaultReservationDurationMinutes: e.target.value }))
            }
          />
        </FormField>
        <FormField label="Pending request expiry (minutes)" htmlFor="settings-pending-expiry">
          <Input
            id="settings-pending-expiry"
            inputMode="numeric"
            disabled={!canManage}
            value={values.pendingRequestExpiryMinutes}
            onChange={(e) =>
              setValues((v) => ({ ...v, pendingRequestExpiryMinutes: e.target.value }))
            }
          />
        </FormField>
        <FormField label="Reminder lead time (minutes)" htmlFor="settings-reminder-lead">
          <Input
            id="settings-reminder-lead"
            inputMode="numeric"
            disabled={!canManage}
            value={values.reminderLeadTimeMinutes}
            onChange={(e) => setValues((v) => ({ ...v, reminderLeadTimeMinutes: e.target.value }))}
          />
        </FormField>
      </div>
      <div className="mt-4 flex flex-col gap-2">
        {(
          [
            ["autoAssignmentEnabled", "Auto-assignment enabled"],
            ["waitlistEnabled", "Waitlist enabled"],
            ["onlineBookingEnabled", "Online booking enabled"],
            ["walkInEnabled", "Walk-in enabled"],
          ] as const
        ).map(([key, label]) => (
          <label key={key} className="flex items-center gap-2 text-sm">
            <Checkbox
              checked={values[key]}
              disabled={!canManage}
              onCheckedChange={(checked) => setValues((v) => ({ ...v, [key]: checked === true }))}
            />
            {label}
          </label>
        ))}
      </div>

      {canManage && (
        <div className="mt-4 flex justify-end">
          <Button disabled={update.isPending} onClick={() => void save()}>
            {update.isPending ? "Saving…" : "Save settings"}
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
