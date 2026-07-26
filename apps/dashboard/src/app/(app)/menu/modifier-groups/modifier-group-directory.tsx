"use client";

import { useState } from "react";
import { Plus, X } from "lucide-react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";

import {
  useArchiveModifierGroup,
  useCreateModifierGroup,
  useModifierGroupList,
  useRestoreModifierGroup,
} from "@/lib/hooks/use-menu-modifiers";
import {
  useAddModifierToGroup,
  useCreateModifier,
  useModifierGroupItems,
  useModifierList,
  useRemoveModifierFromGroup,
} from "@/lib/hooks/use-menu-modifiers";
import { hasPermission, useCurrentUser } from "@/lib/hooks/use-current-user";
import { formatMinorUnits } from "@/lib/crm-display";
import { ApiError } from "@/lib/api/errors";
import { PageHeader } from "@/components/page-header";
import { SectionCard } from "@/components/section-card";
import { EmptyState } from "@/components/empty-state";
import { StatusBadge } from "@/components/status-badge";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { CurrencyInput } from "@/components/forms/currency-input";
import { FormField } from "@/components/forms/form-field";
import { Skeleton } from "@/components/ui/skeleton";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";

const groupSchema = z.object({
  name: z.string().trim().min(1, "A name is required.").max(120),
  minSelect: z.string().refine((v) => Number.isInteger(Number(v)) && Number(v) >= 0, "Enter a whole number."),
  maxSelect: z.string().refine((v) => Number.isInteger(Number(v)) && Number(v) >= 1, "Enter a whole number of at least 1."),
});
type GroupValues = z.infer<typeof groupSchema>;

function CreateModifierGroupForm() {
  const [formError, setFormError] = useState<string | null>(null);
  const createGroup = useCreateModifierGroup();
  const {
    register,
    handleSubmit,
    reset,
    formState: { errors },
  } = useForm<GroupValues>({
    resolver: zodResolver(groupSchema),
    defaultValues: { minSelect: "0", maxSelect: "1" },
  });

  async function onSubmit(values: GroupValues) {
    setFormError(null);
    const minSelect = Number(values.minSelect);
    const maxSelect = Number(values.maxSelect);
    try {
      await createGroup.mutateAsync({
        name: values.name,
        min_select: minSelect,
        max_select: maxSelect,
        is_required: minSelect > 0,
        sort_order: 0,
      });
      reset({ name: "", minSelect: "0", maxSelect: "1" });
    } catch (error) {
      setFormError(error instanceof ApiError ? error.message : "The group could not be created.");
    }
  }

  return (
    <form
      onSubmit={handleSubmit(onSubmit)}
      className="grid gap-3 sm:grid-cols-4"
      noValidate
    >
      <FormField label="Group name" htmlFor="group-name" required error={errors.name?.message} className="sm:col-span-2">
        <Input id="group-name" placeholder="Add-ons" {...register("name")} />
      </FormField>
      <FormField label="Min select" htmlFor="group-min" error={errors.minSelect?.message}>
        <Input id="group-min" type="number" min={0} {...register("minSelect")} />
      </FormField>
      <FormField label="Max select" htmlFor="group-max" error={errors.maxSelect?.message}>
        <Input id="group-max" type="number" min={1} {...register("maxSelect")} />
      </FormField>
      {formError && (
        <p role="alert" className="text-destructive text-sm sm:col-span-4">
          {formError}
        </p>
      )}
      <div className="sm:col-span-4">
        <Button type="submit" size="sm" disabled={createGroup.isPending}>
          {createGroup.isPending ? "Creating…" : "Create group"}
        </Button>
      </div>
    </form>
  );
}

const modifierSchema = z.object({
  name: z.string().trim().min(1, "A name is required.").max(120),
  priceRupees: z.string().trim().optional(),
});
type ModifierValues = z.infer<typeof modifierSchema>;

function CreateModifierForm() {
  const [formError, setFormError] = useState<string | null>(null);
  const createModifier = useCreateModifier();
  const {
    register,
    handleSubmit,
    reset,
    formState: { errors },
  } = useForm<ModifierValues>({ resolver: zodResolver(modifierSchema) });

  async function onSubmit(values: ModifierValues) {
    setFormError(null);
    const rupees = Number(values.priceRupees || 0);
    try {
      await createModifier.mutateAsync({
        name: values.name,
        default_price_minor: Number.isFinite(rupees) ? Math.round(rupees * 100) : 0,
        is_active: true,
      });
      reset();
    } catch (error) {
      setFormError(error instanceof ApiError ? error.message : "The modifier could not be created.");
    }
  }

  return (
    <form onSubmit={handleSubmit(onSubmit)} className="grid gap-3 sm:grid-cols-3" noValidate>
      <FormField label="Modifier name" htmlFor="mod-name" required error={errors.name?.message} className="sm:col-span-2">
        <Input id="mod-name" placeholder="Cheese slice" {...register("name")} />
      </FormField>
      <FormField label="Extra price" htmlFor="mod-price">
        <CurrencyInput id="mod-price" {...register("priceRupees")} />
      </FormField>
      {formError && (
        <p role="alert" className="text-destructive text-sm sm:col-span-3">
          {formError}
        </p>
      )}
      <div className="sm:col-span-3">
        <Button type="submit" size="sm" disabled={createModifier.isPending}>
          {createModifier.isPending ? "Creating…" : "Add modifier to catalog"}
        </Button>
      </div>
    </form>
  );
}

function GroupCard({ groupId, canManage }: { groupId: string; canManage: boolean }) {
  const { data: groups } = useModifierGroupList();
  const group = groups?.find((g) => g.id === groupId);
  const { data: items, isLoading } = useModifierGroupItems(groupId);
  const { data: modifiers } = useModifierList();
  const addModifier = useAddModifierToGroup(groupId);
  const removeModifier = useRemoveModifierFromGroup(groupId);
  const archiveGroup = useArchiveModifierGroup(groupId);
  const restoreGroup = useRestoreModifierGroup(groupId);

  const [selectedModifierId, setSelectedModifierId] = useState("");
  const [error, setError] = useState<string | null>(null);

  if (!group) return null;

  const attachedIds = new Set((items ?? []).map((item) => item.modifier_id));
  const availableModifiers = (modifiers ?? []).filter((m) => !attachedIds.has(m.id));

  return (
    <li className="rounded-md border p-4">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <p className="flex items-center gap-2 font-medium">
            {group.name}
            {group.is_required && <StatusBadge label="Required" tone="warning" />}
          </p>
          <p className="text-muted-foreground text-xs">
            Select {group.min_select}–{group.max_select}
          </p>
        </div>
        {canManage && (
          <Button
            variant="ghost"
            size="sm"
            disabled={archiveGroup.isPending || restoreGroup.isPending}
            onClick={() => archiveGroup.mutate()}
          >
            Archive
          </Button>
        )}
      </div>

      {error && (
        <p role="alert" className="text-destructive mt-2 text-sm">
          {error}
        </p>
      )}

      <div className="mt-3">
        {isLoading ? (
          <Skeleton className="h-8 w-48" />
        ) : (
          <ul className="flex flex-wrap gap-2">
            {(items ?? []).map((item) => {
              const modifier = modifiers?.find((m) => m.id === item.modifier_id);
              return (
                <li key={item.modifier_id}>
                  <Badge variant="secondary" className="gap-1.5 py-1">
                    {modifier?.name ?? item.modifier_id}
                    {modifier && modifier.default_price_minor > 0 && (
                      <span className="text-muted-foreground">
                        {" "}
                        · {formatMinorUnits(modifier.default_price_minor)}
                      </span>
                    )}
                    {canManage && (
                      <button
                        type="button"
                        aria-label={`Remove ${modifier?.name ?? "modifier"} from group`}
                        className="hover:text-destructive"
                        onClick={() => {
                          setError(null);
                          removeModifier.mutate(item.modifier_id, {
                            onError: (err) =>
                              setError(
                                err instanceof ApiError
                                  ? err.message
                                  : "The modifier could not be removed.",
                              ),
                          });
                        }}
                      >
                        <X className="size-3" />
                      </button>
                    )}
                  </Badge>
                </li>
              );
            })}
            {(items ?? []).length === 0 && (
              <li className="text-muted-foreground text-sm">No modifiers in this group yet.</li>
            )}
          </ul>
        )}

        {canManage && availableModifiers.length > 0 && (
          <div className="mt-3 flex items-center gap-2">
            <Select value={selectedModifierId} onValueChange={setSelectedModifierId}>
              <SelectTrigger className="w-56">
                <SelectValue placeholder="Add a modifier…" />
              </SelectTrigger>
              <SelectContent>
                {availableModifiers.map((modifier) => (
                  <SelectItem key={modifier.id} value={modifier.id}>
                    {modifier.name}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
            <Button
              size="sm"
              disabled={!selectedModifierId || addModifier.isPending}
              onClick={() => {
                setError(null);
                addModifier.mutate(
                  { modifierId: selectedModifierId },
                  {
                    onSuccess: () => setSelectedModifierId(""),
                    onError: (err) =>
                      setError(
                        err instanceof ApiError ? err.message : "The modifier could not be added.",
                      ),
                  },
                );
              }}
            >
              <Plus className="size-3.5" />
              Add
            </Button>
          </div>
        )}
      </div>
    </li>
  );
}

export function ModifierGroupDirectory() {
  const { data: currentUser } = useCurrentUser();
  const { data: groups, isLoading } = useModifierGroupList();
  const canManage = hasPermission(currentUser, "menu.modifiers.manage");

  return (
    <div className="flex flex-1 flex-col gap-4 p-6">
      <PageHeader
        title="Modifier Groups"
        description="Reusable add-ons and options — Extra Cheese, Spice Level, and similar — that attach to products."
      />

      {canManage && (
        <>
          <SectionCard title="New modifier group">
            <CreateModifierGroupForm />
          </SectionCard>
          <SectionCard title="Add a modifier to the catalog" description="Reusable across any group.">
            <CreateModifierForm />
          </SectionCard>
        </>
      )}

      <SectionCard title="Groups">
        {isLoading ? (
          <div className="flex flex-col gap-2">
            <Skeleton className="h-24 w-full" />
            <Skeleton className="h-24 w-full" />
          </div>
        ) : !groups || groups.length === 0 ? (
          <EmptyState
            title="No modifier groups yet"
            description="Create a group above to start offering add-ons on products."
          />
        ) : (
          <ul className="flex flex-col gap-3">
            {groups.map((group) => (
              <GroupCard key={group.id} groupId={group.id} canManage={canManage} />
            ))}
          </ul>
        )}
      </SectionCard>
    </div>
  );
}
