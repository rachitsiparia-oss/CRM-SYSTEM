"use client";

import { useState } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import type { Supplier } from "@rkpr/contracts";
import { Plus, Truck } from "lucide-react";

import {
  useArchiveInventorySupplier,
  useCreateInventorySupplier,
  useInventorySuppliers,
  useRestoreInventorySupplier,
  useUpdateInventorySupplier,
} from "@/lib/hooks/use-inventory-reference";
import { useDebouncedValue } from "@/lib/hooks/use-debounced-value";
import { hasPermission, useCurrentUser } from "@/lib/hooks/use-current-user";
import { formatMinorUnits } from "@/lib/crm-display";
import { ApiError } from "@/lib/api/errors";
import { PageHeader } from "@/components/page-header";
import { SectionCard } from "@/components/section-card";
import { ErrorState } from "@/components/error-state";
import { EmptyState } from "@/components/empty-state";
import { StatusBadge } from "@/components/status-badge";
import { ConfirmDialog } from "@/components/modals/confirm-dialog";
import { Modal } from "@/components/modals/modal";
import { FormField } from "@/components/forms/form-field";
import { SearchInput } from "@/components/forms/search-input";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Skeleton } from "@/components/ui/skeleton";

const createSchema = z.object({
  supplierCode: z.string().trim().min(1, "A code is required.").max(32),
  name: z.string().trim().min(1, "A name is required.").max(180),
  contactPerson: z.string().trim().max(160).optional(),
  phone: z.string().trim().max(20).optional(),
  email: z.string().trim().max(255).optional(),
  address: z.string().trim().max(200).optional(),
  city: z.string().trim().max(120).optional(),
  leadTimeDays: z
    .string()
    .trim()
    .optional()
    .refine((v) => !v || (Number.isInteger(Number(v)) && Number(v) >= 0), "Enter whole days."),
  paymentTerms: z.string().trim().max(120).optional(),
  notes: z.string().trim().max(2000).optional(),
});
type CreateValues = z.infer<typeof createSchema>;

function CreateSupplierModal({
  open,
  onOpenChange,
}: {
  open: boolean;
  onOpenChange: (open: boolean) => void;
}) {
  const [formError, setFormError] = useState<string | null>(null);
  const createSupplier = useCreateInventorySupplier();
  const {
    register,
    handleSubmit,
    reset,
    formState: { errors },
  } = useForm<CreateValues>({ resolver: zodResolver(createSchema) });

  async function onSubmit(values: CreateValues) {
    setFormError(null);
    try {
      await createSupplier.mutateAsync({
        supplier_code: values.supplierCode,
        name: values.name,
        contact_person: values.contactPerson || null,
        phone_e164: values.phone || null,
        email: values.email || null,
        address_line1: values.address || null,
        city: values.city || null,
        normal_lead_time_days: values.leadTimeDays ? Number(values.leadTimeDays) : null,
        payment_terms: values.paymentTerms || null,
        notes: values.notes || null,
      });
      reset();
      onOpenChange(false);
    } catch (error) {
      setFormError(error instanceof ApiError ? error.message : "The supplier could not be saved.");
    }
  }

  return (
    <Modal
      open={open}
      onOpenChange={(next) => {
        if (!next) {
          reset();
          setFormError(null);
        }
        onOpenChange(next);
      }}
      title="New supplier"
      footer={
        <>
          <Button type="button" variant="outline" onClick={() => onOpenChange(false)}>
            Cancel
          </Button>
          <Button type="submit" form="supplier-create-form" disabled={createSupplier.isPending}>
            {createSupplier.isPending ? "Creating…" : "Create supplier"}
          </Button>
        </>
      }
    >
      <form
        id="supplier-create-form"
        onSubmit={handleSubmit(onSubmit)}
        className="grid gap-4 sm:grid-cols-2"
        noValidate
      >
        <FormField label="Supplier code" htmlFor="sup-code" required error={errors.supplierCode?.message}>
          <Input id="sup-code" placeholder="SUP-BAK-001" {...register("supplierCode")} />
        </FormField>
        <FormField label="Name" htmlFor="sup-name" required error={errors.name?.message}>
          <Input id="sup-name" {...register("name")} />
        </FormField>
        <FormField label="Contact person" htmlFor="sup-contact">
          <Input id="sup-contact" {...register("contactPerson")} />
        </FormField>
        <FormField label="Phone" htmlFor="sup-phone">
          <Input id="sup-phone" placeholder="+91 98860 11001" {...register("phone")} />
        </FormField>
        <FormField label="Email" htmlFor="sup-email" className="sm:col-span-2">
          <Input id="sup-email" type="email" {...register("email")} />
        </FormField>
        <FormField label="Address" htmlFor="sup-address" className="sm:col-span-2">
          <Input id="sup-address" {...register("address")} />
        </FormField>
        <FormField label="City" htmlFor="sup-city">
          <Input id="sup-city" {...register("city")} />
        </FormField>
        <FormField
          label="Normal lead time (days)"
          htmlFor="sup-lead-time"
          error={errors.leadTimeDays?.message}
        >
          <Input id="sup-lead-time" inputMode="numeric" {...register("leadTimeDays")} />
        </FormField>
        <FormField label="Payment terms" htmlFor="sup-terms" className="sm:col-span-2">
          <Input id="sup-terms" placeholder="15 days" {...register("paymentTerms")} />
        </FormField>
        <FormField label="Notes" htmlFor="sup-notes" className="sm:col-span-2">
          <Textarea id="sup-notes" rows={2} {...register("notes")} />
        </FormField>
        {formError && (
          <p role="alert" className="text-destructive sm:col-span-2 text-sm">
            {formError}
          </p>
        )}
      </form>
    </Modal>
  );
}

function SupplierRow({ supplier, canManage }: { supplier: Supplier; canManage: boolean }) {
  const [editing, setEditing] = useState(false);
  const [name, setName] = useState(supplier.name);
  const [contactPerson, setContactPerson] = useState(supplier.contact_person ?? "");
  const [confirmArchive, setConfirmArchive] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const updateSupplier = useUpdateInventorySupplier(supplier.id);
  const archiveSupplier = useArchiveInventorySupplier(supplier.id);
  const restoreSupplier = useRestoreInventorySupplier(supplier.id);

  async function handleSave() {
    setError(null);
    try {
      await updateSupplier.mutateAsync({
        name,
        contact_person: contactPerson || null,
        expected_version: supplier.version,
      });
      setEditing(false);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "The supplier could not be saved.");
    }
  }

  return (
    <li className="flex flex-col gap-3 rounded-md border p-4">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <p className="flex items-center gap-2 font-medium">
            {supplier.name}
            {supplier.status !== "active" && (
              <StatusBadge
                label={supplier.status === "archived" ? "Archived" : "Inactive"}
                tone="neutral"
              />
            )}
          </p>
          <p className="text-muted-foreground text-xs">{supplier.supplier_code}</p>
          <div className="mt-1 flex flex-wrap gap-x-4 gap-y-0.5 text-sm">
            {supplier.contact_person && <span>{supplier.contact_person}</span>}
            {supplier.phone_e164 && <span>{supplier.phone_e164}</span>}
            {supplier.email && <span>{supplier.email}</span>}
          </div>
          <div className="text-muted-foreground mt-1 flex flex-wrap gap-x-4 gap-y-0.5 text-xs">
            {supplier.normal_lead_time_days !== null && (
              <span>Lead time: {supplier.normal_lead_time_days} days</span>
            )}
            {supplier.payment_terms && <span>Terms: {supplier.payment_terms}</span>}
            {supplier.minimum_order_value_minor !== null && (
              <span>Min order: {formatMinorUnits(supplier.minimum_order_value_minor)}</span>
            )}
          </div>
        </div>
        {canManage && (
          <div className="flex gap-2">
            <Button variant="outline" size="sm" onClick={() => setEditing((v) => !v)}>
              {editing ? "Cancel" : "Edit"}
            </Button>
            {supplier.status === "archived" ? (
              <Button
                variant="outline"
                size="sm"
                disabled={restoreSupplier.isPending}
                onClick={() => restoreSupplier.mutate()}
              >
                Restore
              </Button>
            ) : (
              <Button variant="ghost" size="sm" onClick={() => setConfirmArchive(true)}>
                Archive
              </Button>
            )}
          </div>
        )}
      </div>

      {editing && (
        <div className="flex flex-col gap-3 border-t pt-3">
          <FormField label="Name" htmlFor={`sup-name-${supplier.id}`}>
            <Input
              id={`sup-name-${supplier.id}`}
              value={name}
              onChange={(e) => setName(e.target.value)}
            />
          </FormField>
          <FormField label="Contact person" htmlFor={`sup-contact-${supplier.id}`}>
            <Input
              id={`sup-contact-${supplier.id}`}
              value={contactPerson}
              onChange={(e) => setContactPerson(e.target.value)}
            />
          </FormField>
          {error && (
            <p role="alert" className="text-destructive text-sm">
              {error}
            </p>
          )}
          <div>
            <Button size="sm" disabled={updateSupplier.isPending} onClick={() => void handleSave()}>
              {updateSupplier.isPending ? "Saving…" : "Save"}
            </Button>
          </div>
        </div>
      )}

      <ConfirmDialog
        open={confirmArchive}
        onOpenChange={setConfirmArchive}
        variant="warning"
        title={`Archive ${supplier.name}?`}
        description="Items referencing this supplier are unaffected. It can be restored later."
        confirmLabel="Archive supplier"
        onConfirm={async () => {
          setError(null);
          try {
            await archiveSupplier.mutateAsync();
          } catch (err) {
            setError(err instanceof ApiError ? err.message : "The supplier could not be archived.");
          }
        }}
      />
    </li>
  );
}

export function SupplierDirectory() {
  const { data: currentUser } = useCurrentUser();
  const [searchInput, setSearchInput] = useState("");
  const [showCreate, setShowCreate] = useState(false);
  const search = useDebouncedValue(searchInput);

  const { data, isLoading, isError, refetch } = useInventorySuppliers({
    page: 1,
    pageSize: 100,
    search: search || undefined,
  });

  const canManage = hasPermission(currentUser, "inventory.suppliers.manage");
  const suppliers = data?.data ?? [];

  return (
    <div className="flex flex-1 flex-col gap-4 p-6">
      <PageHeader
        title="Suppliers"
        description="The RKPR supplier directory — contacts, lead times, and payment terms."
        actions={
          canManage ? (
            <Button onClick={() => setShowCreate(true)}>
              <Plus className="size-4" />
              New supplier
            </Button>
          ) : null
        }
      />

      <SearchInput
        value={searchInput}
        onChange={setSearchInput}
        placeholder="Search suppliers…"
        className="max-w-xs"
      />

      <SectionCard title="Suppliers">
        {isError ? (
          <ErrorState title="Could not load suppliers" onRetry={() => void refetch()} />
        ) : isLoading ? (
          <div className="flex flex-col gap-2">
            <Skeleton className="h-24 w-full" />
            <Skeleton className="h-24 w-full" />
          </div>
        ) : suppliers.length === 0 ? (
          <EmptyState
            icon={Truck}
            title="No suppliers found"
            description="Create the first supplier record."
          />
        ) : (
          <ul className="flex flex-col gap-3">
            {suppliers.map((supplier) => (
              <SupplierRow key={supplier.id} supplier={supplier} canManage={canManage} />
            ))}
          </ul>
        )}
      </SectionCard>

      <CreateSupplierModal open={showCreate} onOpenChange={setShowCreate} />
    </div>
  );
}
