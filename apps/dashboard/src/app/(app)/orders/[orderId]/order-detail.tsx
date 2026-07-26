"use client";

import { useState } from "react";
import Link from "next/link";
import { ArrowLeft } from "lucide-react";

import { useOrderDetail, useUpdateOrder } from "@/lib/hooks/use-orders";
import { hasPermission, useCurrentUser } from "@/lib/hooks/use-current-user";
import { formatDateTime, formatMinorUnits, humanize, ORDER_STATUS_TONES, PAYMENT_STATUS_TONES } from "@/lib/crm-display";
import { ApiError } from "@/lib/api/errors";
import { PageHeader } from "@/components/page-header";
import { PageSkeleton } from "@/components/skeletons/page-skeleton";
import { ErrorState } from "@/components/error-state";
import { StatusBadge } from "@/components/status-badge";
import { SectionCard } from "@/components/section-card";
import { FormField } from "@/components/forms/form-field";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { OrderStatusControl } from "./order-status-control";
import { OrderAssignControl } from "./order-assign-control";
import { OrderItemsTab } from "./order-items-tab";
import { OrderTimelineTab } from "./order-timeline-tab";
import { OrderPaymentsTab } from "./order-payments-tab";
import { OrderNotesTab } from "./order-notes-tab";
import { OrderAuditTab } from "./order-audit-tab";

function Field({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <dt className="text-muted-foreground text-xs">{label}</dt>
      <dd className="text-sm">{value}</dd>
    </div>
  );
}

export function OrderDetail({ orderId }: { orderId: string }) {
  const { data: currentUser } = useCurrentUser();
  const { data: order, isLoading, isError, refetch } = useOrderDetail(orderId);
  const updateOrder = useUpdateOrder(orderId);

  const [editingNotes, setEditingNotes] = useState(false);
  const [internalNotesDraft, setInternalNotesDraft] = useState("");
  const [customerNotesDraft, setCustomerNotesDraft] = useState("");
  const [notesError, setNotesError] = useState<string | null>(null);

  const canUpdate = hasPermission(currentUser, "orders.update");
  const canTransition = hasPermission(currentUser, "orders.transition");
  const canAssign = hasPermission(currentUser, "orders.assign");

  if (isLoading) {
    return (
      <div className="flex-1 p-6">
        <PageSkeleton />
      </div>
    );
  }

  if (isError || !order) {
    return (
      <div className="flex-1 p-6">
        <ErrorState
          variant="404"
          title="Order not found"
          description="This order may not exist, or you may not have access to it."
          onRetry={() => void refetch()}
        />
      </div>
    );
  }

  const isReadOnly = order.status === "completed" || order.status === "cancelled";

  async function saveNotes() {
    setNotesError(null);
    try {
      await updateOrder.mutateAsync({
        internal_notes: internalNotesDraft || null,
        customer_notes: customerNotesDraft || null,
        expected_version: order?.version,
      });
      setEditingNotes(false);
    } catch (err) {
      setNotesError(err instanceof ApiError ? err.message : "The notes could not be saved.");
    }
  }

  return (
    <div className="flex flex-1 flex-col gap-6 p-6">
      <div>
        <Link href="/orders/list" className="text-muted-foreground inline-flex items-center gap-1 text-sm hover:underline">
          <ArrowLeft className="size-3.5" />
          Orders
        </Link>
      </div>

      <PageHeader
        title={order.order_number}
        description={`${humanize(order.source)} · ${humanize(order.order_type)} · ${formatDateTime(order.created_at)}`}
        actions={
          <div className="flex flex-wrap items-center gap-2">
            <StatusBadge label={humanize(order.status)} tone={ORDER_STATUS_TONES[order.status]} />
            <StatusBadge label={humanize(order.payment_status)} tone={PAYMENT_STATUS_TONES[order.payment_status]} />
          </div>
        }
      />

      <Tabs defaultValue="overview">
        <TabsList>
          <TabsTrigger value="overview">Overview</TabsTrigger>
          <TabsTrigger value="items">Items</TabsTrigger>
          <TabsTrigger value="timeline">Timeline</TabsTrigger>
          <TabsTrigger value="payments">Payments</TabsTrigger>
          <TabsTrigger value="notes">Notes</TabsTrigger>
          <TabsTrigger value="audit">Audit</TabsTrigger>
        </TabsList>

        <TabsContent value="overview" className="mt-4 flex flex-col gap-4">
          <SectionCard title="Order details">
            <dl className="grid grid-cols-1 gap-4 sm:grid-cols-3">
              <Field label="Grand total" value={formatMinorUnits(order.grand_total_minor)} />
              <Field label="Estimated completion" value={formatDateTime(order.estimated_completion_time)} />
              <Field label="Version" value={String(order.version)} />
              <Field label="Created" value={formatDateTime(order.created_at)} />
              <Field label="Last updated" value={formatDateTime(order.updated_at)} />
            </dl>
          </SectionCard>

          {canTransition && !isReadOnly && <OrderStatusControl order={order} />}
          {canAssign && !isReadOnly && <OrderAssignControl order={order} />}

          {canUpdate && (
            <SectionCard
              title="Notes"
              description={isReadOnly ? "This order is read-only." : undefined}
              actions={
                !isReadOnly && !editingNotes ? (
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => {
                      setInternalNotesDraft(order.internal_notes ?? "");
                      setCustomerNotesDraft(order.customer_notes ?? "");
                      setEditingNotes(true);
                    }}
                  >
                    Edit
                  </Button>
                ) : null
              }
            >
              {editingNotes ? (
                <div className="flex flex-col gap-4">
                  <FormField label="Internal notes" htmlFor="order-internal-notes-edit">
                    <Textarea
                      id="order-internal-notes-edit"
                      rows={3}
                      value={internalNotesDraft}
                      onChange={(e) => setInternalNotesDraft(e.target.value)}
                    />
                  </FormField>
                  <FormField label="Customer notes" htmlFor="order-customer-notes-edit">
                    <Textarea
                      id="order-customer-notes-edit"
                      rows={3}
                      value={customerNotesDraft}
                      onChange={(e) => setCustomerNotesDraft(e.target.value)}
                    />
                  </FormField>
                  {notesError && (
                    <p role="alert" className="text-destructive text-sm">
                      {notesError}
                    </p>
                  )}
                  <div className="flex justify-end gap-2">
                    <Button variant="outline" onClick={() => setEditingNotes(false)}>
                      Cancel
                    </Button>
                    <Button disabled={updateOrder.isPending} onClick={() => void saveNotes()}>
                      {updateOrder.isPending ? "Saving…" : "Save"}
                    </Button>
                  </div>
                </div>
              ) : (
                <dl className="grid grid-cols-1 gap-4 sm:grid-cols-2">
                  <Field label="Internal notes" value={order.internal_notes ?? "—"} />
                  <Field label="Customer notes" value={order.customer_notes ?? "—"} />
                </dl>
              )}
            </SectionCard>
          )}
        </TabsContent>

        <TabsContent value="items" className="mt-4">
          <OrderItemsTab order={order} />
        </TabsContent>

        <TabsContent value="timeline" className="mt-4">
          <OrderTimelineTab orderId={orderId} />
        </TabsContent>

        <TabsContent value="payments" className="mt-4">
          <OrderPaymentsTab orderId={orderId} />
        </TabsContent>

        <TabsContent value="notes" className="mt-4">
          <OrderNotesTab orderId={orderId} />
        </TabsContent>

        <TabsContent value="audit" className="mt-4">
          <OrderAuditTab orderId={orderId} />
        </TabsContent>
      </Tabs>
    </div>
  );
}
