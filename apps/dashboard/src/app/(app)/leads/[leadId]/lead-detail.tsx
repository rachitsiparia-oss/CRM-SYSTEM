"use client";

import { useState } from "react";
import Link from "next/link";
import { ArrowLeft, UserCheck } from "lucide-react";

import {
  useArchiveLead,
  useLeadDetail,
  useSetLeadDoNotContact,
} from "@/lib/hooks/use-leads";
import { hasPermission, useCurrentUser } from "@/lib/hooks/use-current-user";
import {
  formatDate,
  formatDateTime,
  formatMinorUnits,
  humanize,
  LEAD_PRIORITY_TONES,
  LEAD_STATUS_TONES,
} from "@/lib/crm-display";
import { ApiError } from "@/lib/api/errors";
import { PageHeader } from "@/components/page-header";
import { PageSkeleton } from "@/components/skeletons/page-skeleton";
import { ErrorState } from "@/components/error-state";
import { StatusBadge } from "@/components/status-badge";
import { SectionCard } from "@/components/section-card";
import { ConfirmDialog } from "@/components/modals/confirm-dialog";
import { Button } from "@/components/ui/button";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { LeadStatusControl } from "./lead-status-control";
import { LeadFollowUps } from "./lead-follow-ups";
import { LeadActivity } from "./lead-activity";
import { LeadConvertModal } from "./lead-convert-modal";

function Field({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <dt className="text-muted-foreground text-xs">{label}</dt>
      <dd className="text-sm">{value}</dd>
    </div>
  );
}

export function LeadDetail({ leadId }: { leadId: string }) {
  const { data: currentUser } = useCurrentUser();
  const { data: lead, isLoading, isError, refetch } = useLeadDetail(leadId);
  const setDoNotContact = useSetLeadDoNotContact(leadId);
  const archiveLead = useArchiveLead(leadId);

  const [showConvert, setShowConvert] = useState(false);
  const [confirmArchive, setConfirmArchive] = useState(false);
  const [actionError, setActionError] = useState<string | null>(null);

  const canUpdate = hasPermission(currentUser, "leads.update");
  const canTransition = hasPermission(currentUser, "leads.transition");
  const canConvert = hasPermission(currentUser, "leads.convert");
  const canArchive = hasPermission(currentUser, "leads.archive");
  const canManageFollowUps = hasPermission(currentUser, "leads.followup.manage");
  const canLogActivity = hasPermission(currentUser, "leads.notes.manage");

  if (isLoading) {
    return (
      <div className="flex-1 p-6">
        <PageSkeleton />
      </div>
    );
  }

  if (isError || !lead) {
    return (
      <div className="flex-1 p-6">
        <ErrorState
          variant="404"
          title="Lead not found"
          description="This lead may have been archived, or it never existed."
          onRetry={() => void refetch()}
        />
      </div>
    );
  }

  const isConverted = lead.status === "won" && !!lead.won_customer_id;
  const isClosed = lead.status === "closed" || lead.status === "lost";

  function reportError(fallback: string) {
    return (error: unknown) =>
      setActionError(error instanceof ApiError ? error.message : fallback);
  }

  return (
    <div className="flex flex-1 flex-col gap-6 p-6">
      <div>
        <Link
          href="/leads"
          className="text-muted-foreground inline-flex items-center gap-1 text-sm hover:underline"
        >
          <ArrowLeft className="size-3.5" />
          Leads
        </Link>
      </div>

      <PageHeader
        title={lead.display_name}
        description={`${lead.lead_number} · ${humanize(lead.lead_type)} · ${humanize(lead.source)}`}
        actions={
          <div className="flex flex-wrap items-center gap-2">
            <StatusBadge label={humanize(lead.status)} tone={LEAD_STATUS_TONES[lead.status]} />
            <StatusBadge
              label={`${humanize(lead.priority)} priority`}
              tone={LEAD_PRIORITY_TONES[lead.priority]}
            />
            {lead.do_not_contact && <StatusBadge label="Do not contact" tone="danger" />}
            {canConvert && !isConverted && !isClosed && (
              <Button onClick={() => setShowConvert(true)}>
                <UserCheck className="size-4" />
                Convert to customer
              </Button>
            )}
            {canArchive && !isConverted && (
              <Button variant="outline" onClick={() => setConfirmArchive(true)}>
                Archive
              </Button>
            )}
          </div>
        }
      />

      {isConverted && lead.won_customer_id && (
        <div className="border-success/40 bg-success/10 rounded-md border p-3 text-sm">
          This lead was converted on {formatDateTime(lead.converted_at)}. It is now{" "}
          <Link
            href={`/customers/${lead.won_customer_id}`}
            className="font-medium hover:underline"
          >
            a customer
          </Link>
          . The lead and its full history are kept for reporting.
        </div>
      )}

      {actionError && (
        <p role="alert" className="text-destructive text-sm">
          {actionError}
        </p>
      )}

      <Tabs defaultValue="overview">
        <TabsList>
          <TabsTrigger value="overview">Overview</TabsTrigger>
          <TabsTrigger value="follow-ups">Follow-ups</TabsTrigger>
          <TabsTrigger value="activity">Activity</TabsTrigger>
        </TabsList>

        <TabsContent value="overview" className="mt-4 flex flex-col gap-4">
          <SectionCard title="Enquiry details">
            <dl className="grid grid-cols-1 gap-4 sm:grid-cols-3">
              <Field label="Contact person" value={lead.contact_name ?? "—"} />
              <Field label="Organization" value={lead.organization_name ?? "—"} />
              <Field label="Phone" value={lead.phone_e164 ?? "—"} />
              <Field label="Email" value={lead.email ?? "—"} />
              <Field
                label="Estimated value"
                value={formatMinorUnits(lead.estimated_value_minor)}
              />
              <Field label="Party size" value={lead.party_size ? String(lead.party_size) : "—"} />
              <Field label="Requested date" value={formatDate(lead.requested_date)} />
              <Field label="Campaign" value={lead.campaign_reference ?? "—"} />
              <Field label="Next follow-up" value={formatDateTime(lead.next_follow_up_at)} />
              <Field label="Last contact" value={formatDateTime(lead.last_contact_at)} />
              <Field label="Created" value={formatDateTime(lead.created_at)} />
              <Field label="Last updated" value={formatDateTime(lead.updated_at)} />
              {lead.lost_reason && (
                <Field label="Lost reason" value={humanize(lead.lost_reason)} />
              )}
            </dl>

            {lead.description && (
              <div className="mt-4">
                <p className="text-muted-foreground text-xs">Description</p>
                <p className="text-sm whitespace-pre-wrap">{lead.description}</p>
              </div>
            )}
            {lead.qualification_notes && (
              <div className="mt-4">
                <p className="text-muted-foreground text-xs">Qualification notes</p>
                <p className="text-sm whitespace-pre-wrap">{lead.qualification_notes}</p>
              </div>
            )}
          </SectionCard>

          {canTransition && !isConverted && <LeadStatusControl lead={lead} />}

          {canUpdate && (
            <SectionCard
              title="Contact preference"
              description="A lead marked do-not-contact cannot have new follow-ups scheduled."
            >
              <Button
                variant="outline"
                disabled={setDoNotContact.isPending}
                onClick={() => {
                  setActionError(null);
                  setDoNotContact.mutate(!lead.do_not_contact, {
                    onError: reportError("The contact preference could not be updated."),
                  });
                }}
              >
                {lead.do_not_contact
                  ? "Allow contact again"
                  : "Mark as do not contact"}
              </Button>
            </SectionCard>
          )}
        </TabsContent>

        <TabsContent value="follow-ups" className="mt-4">
          <LeadFollowUps
            leadId={leadId}
            doNotContact={lead.do_not_contact}
            canEdit={canManageFollowUps && !isConverted}
            currentStaffId={currentUser?.id}
          />
        </TabsContent>

        <TabsContent value="activity" className="mt-4">
          <LeadActivity leadId={leadId} canEdit={canLogActivity} />
        </TabsContent>
      </Tabs>

      <LeadConvertModal
        leadId={leadId}
        open={showConvert}
        onOpenChange={setShowConvert}
      />

      <ConfirmDialog
        open={confirmArchive}
        onOpenChange={setConfirmArchive}
        variant="warning"
        title="Archive this lead?"
        description="The lead is hidden from the pipeline but keeps its full history and can be restored."
        confirmLabel="Archive lead"
        onConfirm={async () => {
          setActionError(null);
          try {
            await archiveLead.mutateAsync("Archived from the lead detail page.");
          } catch (error) {
            reportError("The lead could not be archived.")(error);
          }
        }}
      />
    </div>
  );
}
