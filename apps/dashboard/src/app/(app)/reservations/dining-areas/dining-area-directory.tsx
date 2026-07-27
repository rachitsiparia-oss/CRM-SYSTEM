"use client";

import { useState } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { Plus, Archive, RotateCcw } from "lucide-react";

import {
  useArchiveDiningArea,
  useCreateDiningArea,
  useDiningAreas,
  useRestoreDiningArea,
} from "@/lib/hooks/use-reservations";
import { hasPermission, useCurrentUser } from "@/lib/hooks/use-current-user";
import { ApiError } from "@/lib/api/errors";
import { PageHeader } from "@/components/page-header";
import { SectionCard } from "@/components/section-card";
import { Modal } from "@/components/modals/modal";
import { ConfirmDialog } from "@/components/modals/confirm-dialog";
import { FormField } from "@/components/forms/form-field";
import { StatusBadge } from "@/components/status-badge";
import { EmptyState } from "@/components/empty-state";
import { CardSkeleton } from "@/components/skeletons/card-skeleton";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";

const schema = z.object({
  code: z.string().trim().min(1, "A code is required.").max(64),
  name: z.string().trim().min(1, "A name is required.").max(120),
  description: z.string().trim().optional(),
});
type Values = z.infer<typeof schema>;

function DiningAreaRow({
  area,
  canManage,
}: {
  area: { id: string; code: string; name: string; description: string | null; is_active: boolean };
  canManage: boolean;
}) {
  const archive = useArchiveDiningArea(area.id);
  const restore = useRestoreDiningArea(area.id);
  const [confirmArchive, setConfirmArchive] = useState(false);

  return (
    <li className="flex items-center justify-between rounded-md border p-3">
      <div>
        <p className="text-sm font-medium">{area.name}</p>
        <p className="text-muted-foreground text-xs">
          {area.code}
          {area.description ? ` · ${area.description}` : ""}
        </p>
      </div>
      <div className="flex items-center gap-2">
        <StatusBadge
          label={area.is_active ? "Active" : "Archived"}
          tone={area.is_active ? "success" : "neutral"}
        />
        {canManage && area.is_active && (
          <Button variant="outline" size="sm" onClick={() => setConfirmArchive(true)}>
            <Archive className="size-3.5" />
            Archive
          </Button>
        )}
        {canManage && !area.is_active && (
          <Button variant="outline" size="sm" onClick={() => void restore.mutateAsync()}>
            <RotateCcw className="size-3.5" />
            Restore
          </Button>
        )}
      </div>
      <ConfirmDialog
        open={confirmArchive}
        onOpenChange={setConfirmArchive}
        variant="danger"
        title={`Archive ${area.name}?`}
        description="It will no longer be selectable for new reservations or tables."
        confirmLabel="Archive"
        onConfirm={async () => {
          await archive.mutateAsync("Archived from dining areas list.");
        }}
      />
    </li>
  );
}

export function DiningAreaDirectory() {
  const { data: currentUser } = useCurrentUser();
  const { data: areas, isLoading } = useDiningAreas(true);
  const createArea = useCreateDiningArea();
  const [showCreate, setShowCreate] = useState(false);
  const [formError, setFormError] = useState<string | null>(null);

  const canManage = hasPermission(currentUser, "reservations.tables.manage");

  const {
    register,
    handleSubmit,
    reset,
    formState: { errors },
  } = useForm<Values>({ resolver: zodResolver(schema) });

  async function onSubmit(values: Values) {
    setFormError(null);
    try {
      await createArea.mutateAsync({
        code: values.code,
        name: values.name,
        description: values.description || null,
      });
      reset();
      setShowCreate(false);
    } catch (error) {
      setFormError(error instanceof ApiError ? error.message : "The dining area could not be created.");
    }
  }

  return (
    <div className="flex flex-1 flex-col gap-4 p-6">
      <PageHeader
        title="Dining Areas"
        description="Indoor, outdoor, and private zones — each with its own tables."
        actions={
          canManage ? (
            <Button onClick={() => setShowCreate(true)}>
              <Plus className="size-4" />
              New dining area
            </Button>
          ) : null
        }
      />

      <SectionCard title="Areas">
        {isLoading ? (
          <CardSkeleton />
        ) : !areas || areas.length === 0 ? (
          <EmptyState title="No dining areas yet" description="Create the first dining area to get started." />
        ) : (
          <ul className="flex flex-col gap-2">
            {areas.map((area) => (
              <DiningAreaRow key={area.id} area={area} canManage={canManage} />
            ))}
          </ul>
        )}
      </SectionCard>

      <Modal
        open={showCreate}
        onOpenChange={(next) => {
          if (!next) reset();
          setShowCreate(next);
        }}
        title="New dining area"
        footer={
          <>
            <Button type="button" variant="outline" onClick={() => setShowCreate(false)}>
              Cancel
            </Button>
            <Button type="submit" form="dining-area-create-form" disabled={createArea.isPending}>
              {createArea.isPending ? "Creating…" : "Create area"}
            </Button>
          </>
        }
      >
        <form
          id="dining-area-create-form"
          onSubmit={handleSubmit(onSubmit)}
          className="flex flex-col gap-4"
          noValidate
        >
          <FormField label="Code" htmlFor="dining-area-code" required error={errors.code?.message}>
            <Input id="dining-area-code" placeholder="indoor" {...register("code")} />
          </FormField>
          <FormField label="Name" htmlFor="dining-area-name" required error={errors.name?.message}>
            <Input id="dining-area-name" {...register("name")} />
          </FormField>
          <FormField label="Description" htmlFor="dining-area-description">
            <Textarea id="dining-area-description" rows={2} {...register("description")} />
          </FormField>
          {formError && (
            <p role="alert" className="text-destructive text-sm">
              {formError}
            </p>
          )}
        </form>
      </Modal>
    </div>
  );
}
