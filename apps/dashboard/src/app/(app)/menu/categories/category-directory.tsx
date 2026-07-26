"use client";

import { useState } from "react";
import { ArrowDown, ArrowUp, FolderPlus } from "lucide-react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import type { MenuCategory } from "@rkpr/contracts";

import {
  useArchiveCategory,
  useCategoryList,
  useCreateCategory,
  useReorderCategories,
  useRestoreCategory,
  useUpdateCategory,
} from "@/lib/hooks/use-menu-categories";
import { hasPermission, useCurrentUser } from "@/lib/hooks/use-current-user";
import { ApiError } from "@/lib/api/errors";
import { PageHeader } from "@/components/page-header";
import { SectionCard } from "@/components/section-card";
import { ErrorState } from "@/components/error-state";
import { EmptyState } from "@/components/empty-state";
import { StatusBadge } from "@/components/status-badge";
import { ConfirmDialog } from "@/components/modals/confirm-dialog";
import { Modal } from "@/components/modals/modal";
import { FormField } from "@/components/forms/form-field";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Skeleton } from "@/components/ui/skeleton";
import { SearchInput } from "@/components/forms/search-input";

const createSchema = z.object({
  code: z
    .string()
    .trim()
    .min(1, "A code is required.")
    .max(64)
    .regex(/^[a-z0-9-_]+$/i, "Letters, numbers, hyphens, and underscores only."),
  name: z.string().trim().min(1, "A name is required.").max(120),
  description: z.string().trim().max(2000).optional(),
});
type CreateValues = z.infer<typeof createSchema>;

function CreateCategoryModal({
  open,
  onOpenChange,
}: {
  open: boolean;
  onOpenChange: (open: boolean) => void;
}) {
  const [formError, setFormError] = useState<string | null>(null);
  const createCategory = useCreateCategory();
  const {
    register,
    handleSubmit,
    reset,
    formState: { errors },
  } = useForm<CreateValues>({ resolver: zodResolver(createSchema) });

  async function onSubmit(values: CreateValues) {
    setFormError(null);
    try {
      await createCategory.mutateAsync({
        code: values.code,
        name: values.name,
        description: values.description || null,
      });
      reset();
      onOpenChange(false);
    } catch (error) {
      setFormError(error instanceof ApiError ? error.message : "The category could not be saved.");
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
      title="New category"
      footer={
        <>
          <Button type="button" variant="outline" onClick={() => onOpenChange(false)}>
            Cancel
          </Button>
          <Button type="submit" form="category-create-form" disabled={createCategory.isPending}>
            {createCategory.isPending ? "Creating…" : "Create category"}
          </Button>
        </>
      }
    >
      <form
        id="category-create-form"
        onSubmit={handleSubmit(onSubmit)}
        className="grid gap-4"
        noValidate
      >
        <FormField label="Code" htmlFor="cat-code" required error={errors.code?.message}>
          <Input id="cat-code" placeholder="pizzas" {...register("code")} />
        </FormField>
        <FormField label="Name" htmlFor="cat-name" required error={errors.name?.message}>
          <Input id="cat-name" placeholder="Pizzas" {...register("name")} />
        </FormField>
        <FormField label="Description" htmlFor="cat-description">
          <Textarea id="cat-description" rows={3} {...register("description")} />
        </FormField>
        {formError && (
          <p role="alert" className="text-destructive text-sm">
            {formError}
          </p>
        )}
      </form>
    </Modal>
  );
}

function CategoryRow({
  category,
  canManage,
  isFirst,
  isLast,
  onMove,
}: {
  category: MenuCategory;
  canManage: boolean;
  isFirst: boolean;
  isLast: boolean;
  onMove: (direction: "up" | "down") => void;
}) {
  const [editing, setEditing] = useState(false);
  const [name, setName] = useState(category.name);
  const [description, setDescription] = useState(category.description ?? "");
  const [confirmArchive, setConfirmArchive] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const updateCategory = useUpdateCategory(category.id);
  const archiveCategory = useArchiveCategory(category.id);
  const restoreCategory = useRestoreCategory(category.id);

  async function handleSave() {
    setError(null);
    try {
      await updateCategory.mutateAsync({
        name,
        description: description || null,
        expected_version: category.version,
      });
      setEditing(false);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "The category could not be saved.");
    }
  }

  return (
    <li className="flex flex-col gap-3 rounded-md border p-4">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div className="flex items-start gap-3">
          {canManage && (
            <div className="flex flex-col gap-1 pt-0.5">
              <Button
                variant="ghost"
                size="icon"
                className="size-6"
                disabled={isFirst}
                aria-label={`Move ${category.name} up`}
                onClick={() => onMove("up")}
              >
                <ArrowUp className="size-3.5" />
              </Button>
              <Button
                variant="ghost"
                size="icon"
                className="size-6"
                disabled={isLast}
                aria-label={`Move ${category.name} down`}
                onClick={() => onMove("down")}
              >
                <ArrowDown className="size-3.5" />
              </Button>
            </div>
          )}
          <div>
            <p className="flex items-center gap-2 font-medium">
              {category.name}
              {!category.is_active && <StatusBadge label="Inactive" tone="neutral" />}
            </p>
            <p className="text-muted-foreground text-xs">{category.code}</p>
            {category.description && (
              <p className="mt-1 text-sm">{category.description}</p>
            )}
          </div>
        </div>
        {canManage && (
          <div className="flex gap-2">
            <Button variant="outline" size="sm" onClick={() => setEditing((v) => !v)}>
              {editing ? "Cancel" : "Edit"}
            </Button>
            <Button variant="ghost" size="sm" onClick={() => setConfirmArchive(true)}>
              Archive
            </Button>
          </div>
        )}
      </div>

      {editing && (
        <div className="flex flex-col gap-3 border-t pt-3">
          <FormField label="Name" htmlFor={`name-${category.id}`}>
            <Input
              id={`name-${category.id}`}
              value={name}
              onChange={(e) => setName(e.target.value)}
            />
          </FormField>
          <FormField label="Description" htmlFor={`description-${category.id}`}>
            <Textarea
              id={`description-${category.id}`}
              rows={2}
              value={description}
              onChange={(e) => setDescription(e.target.value)}
            />
          </FormField>
          {error && (
            <p role="alert" className="text-destructive text-sm">
              {error}
            </p>
          )}
          <div>
            <Button size="sm" disabled={updateCategory.isPending} onClick={() => void handleSave()}>
              {updateCategory.isPending ? "Saving…" : "Save"}
            </Button>
          </div>
        </div>
      )}

      {!category.is_active && canManage && (
        <div>
          <Button
            variant="outline"
            size="sm"
            disabled={restoreCategory.isPending}
            onClick={() => restoreCategory.mutate()}
          >
            Restore
          </Button>
        </div>
      )}

      <ConfirmDialog
        open={confirmArchive}
        onOpenChange={setConfirmArchive}
        variant="warning"
        title={`Archive ${category.name}?`}
        description="Products in this category are unaffected but the category is hidden from the default list. It can be restored later."
        confirmLabel="Archive category"
        onConfirm={async () => {
          setError(null);
          try {
            await archiveCategory.mutateAsync("Archived from category management.");
          } catch (err) {
            setError(err instanceof ApiError ? err.message : "The category could not be archived.");
          }
        }}
      />
    </li>
  );
}

export function CategoryDirectory() {
  const { data: currentUser } = useCurrentUser();
  const [search, setSearch] = useState("");
  const [showCreate, setShowCreate] = useState(false);
  const reorderCategories = useReorderCategories();

  const { data, isLoading, isError, refetch } = useCategoryList({
    page: 1,
    pageSize: 100,
    search: search || undefined,
    sort: "sort_order",
  });

  const canManage = hasPermission(currentUser, "menu.categories.manage");
  const categories = data?.data ?? [];

  function handleMove(index: number, direction: "up" | "down") {
    const targetIndex = direction === "up" ? index - 1 : index + 1;
    if (targetIndex < 0 || targetIndex >= categories.length) return;
    const reordered = [...categories];
    const [moved] = reordered.splice(index, 1);
    reordered.splice(targetIndex, 0, moved);
    reorderCategories.mutate(reordered.map((c) => c.id));
  }

  return (
    <div className="flex flex-1 flex-col gap-4 p-6">
      <PageHeader
        title="Menu Categories"
        description="How products are grouped in the menu. Use the arrows to control display order."
        actions={
          canManage ? (
            <Button onClick={() => setShowCreate(true)}>
              <FolderPlus className="size-4" />
              New category
            </Button>
          ) : null
        }
      />

      <SearchInput
        value={search}
        onChange={setSearch}
        placeholder="Search categories…"
        className="max-w-xs"
      />

      <SectionCard title="Categories">
        {isError ? (
          <ErrorState
            title="Could not load categories"
            onRetry={() => void refetch()}
          />
        ) : isLoading ? (
          <div className="flex flex-col gap-2">
            <Skeleton className="h-20 w-full" />
            <Skeleton className="h-20 w-full" />
            <Skeleton className="h-20 w-full" />
          </div>
        ) : categories.length === 0 ? (
          <EmptyState title="No categories found" description="Create the first menu category." />
        ) : (
          <ul className="flex flex-col gap-3">
            {categories.map((category, index) => (
              <CategoryRow
                key={category.id}
                category={category}
                canManage={canManage}
                isFirst={index === 0}
                isLast={index === categories.length - 1}
                onMove={(direction) => handleMove(index, direction)}
              />
            ))}
          </ul>
        )}
      </SectionCard>

      <CreateCategoryModal open={showCreate} onOpenChange={setShowCreate} />
    </div>
  );
}
