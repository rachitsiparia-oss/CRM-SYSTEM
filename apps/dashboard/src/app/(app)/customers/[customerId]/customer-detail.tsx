"use client";

import { useState } from "react";
import Link from "next/link";
import { ArrowLeft } from "lucide-react";

import {
  useArchiveCustomer,
  useCustomerDetail,
  useRestoreCustomer,
} from "@/lib/hooks/use-customers";
import { hasPermission, useCurrentUser } from "@/lib/hooks/use-current-user";
import {
  CUSTOMER_STATUS_TONES,
  formatDate,
  formatDateTime,
  formatMinorUnits,
  humanize,
} from "@/lib/crm-display";
import { ApiError } from "@/lib/api/errors";
import { PageHeader } from "@/components/page-header";
import { PageSkeleton } from "@/components/skeletons/page-skeleton";
import { ErrorState } from "@/components/error-state";
import { StatusBadge } from "@/components/status-badge";
import { SectionCard } from "@/components/section-card";
import { StatCard } from "@/components/stat-card";
import { ConfirmDialog } from "@/components/modals/confirm-dialog";
import { Button } from "@/components/ui/button";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { CustomerEditForm } from "./customer-edit-form";
import { CustomerAddresses } from "./customer-addresses";
import { CustomerNotes } from "./customer-notes";
import { CustomerTags } from "./customer-tags";
import { CustomerTimeline } from "./customer-timeline";

function Field({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <dt className="text-muted-foreground text-xs">{label}</dt>
      <dd className="text-sm">{value}</dd>
    </div>
  );
}

export function CustomerDetail({ customerId }: { customerId: string }) {
  const { data: currentUser } = useCurrentUser();
  const { data: customer, isLoading, isError, refetch } = useCustomerDetail(customerId);
  const archiveCustomer = useArchiveCustomer(customerId);
  const restoreCustomer = useRestoreCustomer(customerId);

  const [confirmArchive, setConfirmArchive] = useState(false);
  const [actionError, setActionError] = useState<string | null>(null);

  const canUpdate = hasPermission(currentUser, "customers.update");
  const canArchive = hasPermission(currentUser, "customers.archive");
  const canRestore = hasPermission(currentUser, "customers.restore");

  if (isLoading) {
    return (
      <div className="flex-1 p-6">
        <PageSkeleton />
      </div>
    );
  }

  if (isError || !customer) {
    return (
      <div className="flex-1 p-6">
        <ErrorState
          variant="404"
          title="Customer not found"
          description="This customer may have been archived, merged, or never existed."
          onRetry={() => void refetch()}
        />
      </div>
    );
  }

  const isMerged = customer.customer_status === "merged";

  return (
    <div className="flex flex-1 flex-col gap-6 p-6">
      <div>
        <Link
          href="/customers"
          className="text-muted-foreground inline-flex items-center gap-1 text-sm hover:underline"
        >
          <ArrowLeft className="size-3.5" />
          Customers
        </Link>
      </div>

      <PageHeader
        title={customer.display_name}
        description={`${customer.customer_number} · ${humanize(customer.customer_type)}`}
        actions={
          <div className="flex items-center gap-2">
            <StatusBadge
              label={humanize(customer.customer_status)}
              tone={CUSTOMER_STATUS_TONES[customer.customer_status]}
            />
            {customer.customer_status === "archived"
              ? canRestore && (
                  <Button
                    variant="outline"
                    disabled={restoreCustomer.isPending}
                    onClick={() => {
                      setActionError(null);
                      restoreCustomer.mutate(undefined, {
                        onError: (error) =>
                          setActionError(
                            error instanceof ApiError
                              ? error.message
                              : "The customer could not be restored.",
                          ),
                      });
                    }}
                  >
                    {restoreCustomer.isPending ? "Restoring…" : "Restore"}
                  </Button>
                )
              : canArchive &&
                !isMerged && (
                  <Button variant="outline" onClick={() => setConfirmArchive(true)}>
                    Archive
                  </Button>
                )}
          </div>
        }
      />

      {isMerged && customer.merged_into_customer_id && (
        <div className="bg-muted rounded-md border p-3 text-sm">
          This record was merged into{" "}
          <Link
            href={`/customers/${customer.merged_into_customer_id}`}
            className="font-medium hover:underline"
          >
            another customer
          </Link>
          . It is kept for history and is no longer the canonical profile.
        </div>
      )}

      {actionError && (
        <p role="alert" className="text-destructive text-sm">
          {actionError}
        </p>
      )}

      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <StatCard label="Completed orders" value={String(customer.completed_order_count)} />
        <StatCard label="Lifetime value" value={formatMinorUnits(customer.lifetime_value_minor)} />
        <StatCard
          label="Average order value"
          value={formatMinorUnits(customer.average_order_value_minor)}
        />
        <StatCard label="Last order" value={formatDate(customer.last_order_at)} />
      </div>

      <Tabs defaultValue="profile">
        <TabsList>
          <TabsTrigger value="profile">Profile</TabsTrigger>
          <TabsTrigger value="addresses">Addresses</TabsTrigger>
          <TabsTrigger value="notes">Notes</TabsTrigger>
          <TabsTrigger value="tags">Tags</TabsTrigger>
          <TabsTrigger value="timeline">Timeline</TabsTrigger>
        </TabsList>

        <TabsContent value="profile" className="mt-4 flex flex-col gap-4">
          <SectionCard title="Identity and contact">
            <dl className="grid grid-cols-1 gap-4 sm:grid-cols-3">
              <Field label="First name" value={customer.first_name ?? "—"} />
              <Field label="Last name" value={customer.last_name ?? "—"} />
              <Field label="Organization" value={customer.organization_name ?? "—"} />
              <Field label="Phone" value={customer.primary_phone_e164 ?? "—"} />
              <Field label="Email" value={customer.primary_email ?? "—"} />
              <Field label="Preferred language" value={customer.preferred_language ?? "—"} />
              <Field label="Date of birth" value={formatDate(customer.date_of_birth)} />
              <Field label="Anniversary" value={formatDate(customer.anniversary_date)} />
              <Field label="Acquisition source" value={humanize(customer.acquisition_source)} />
              <Field label="Segment" value={humanize(customer.customer_segment)} />
              <Field label="Dietary preference" value={humanize(customer.dietary_preference)} />
              <Field label="Spice preference" value={humanize(customer.spice_preference)} />
              <Field label="Created" value={formatDateTime(customer.created_at)} />
              <Field label="Last updated" value={formatDateTime(customer.updated_at)} />
              <Field label="Last activity" value={formatDateTime(customer.last_activity_at)} />
            </dl>
          </SectionCard>

          {canUpdate && !isMerged && <CustomerEditForm customer={customer} />}
          {!canUpdate && (
            <p className="text-muted-foreground text-sm">
              You can view this profile but not edit it — editing requires the{" "}
              <code className="font-mono text-xs">customers.update</code> permission.
            </p>
          )}
        </TabsContent>

        <TabsContent value="addresses" className="mt-4">
          <CustomerAddresses customerId={customerId} canEdit={canUpdate && !isMerged} />
        </TabsContent>

        <TabsContent value="notes" className="mt-4">
          <CustomerNotes
            customerId={customerId}
            canEdit={hasPermission(currentUser, "customers.notes.manage") && !isMerged}
          />
        </TabsContent>

        <TabsContent value="tags" className="mt-4">
          <CustomerTags
            customerId={customerId}
            canEdit={hasPermission(currentUser, "customers.tags.manage") && !isMerged}
          />
        </TabsContent>

        <TabsContent value="timeline" className="mt-4">
          <CustomerTimeline customerId={customerId} />
        </TabsContent>
      </Tabs>

      <ConfirmDialog
        open={confirmArchive}
        onOpenChange={setConfirmArchive}
        variant="warning"
        title="Archive this customer?"
        description="The profile stays in the system with its full history and can be restored later. It is hidden from the default customer list."
        confirmLabel="Archive customer"
        onConfirm={async () => {
          setActionError(null);
          try {
            await archiveCustomer.mutateAsync("Archived from the customer profile page.");
          } catch (error) {
            setActionError(
              error instanceof ApiError ? error.message : "The customer could not be archived.",
            );
          }
        }}
      />
    </div>
  );
}
