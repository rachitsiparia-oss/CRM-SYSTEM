"use client";

import { useState } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { Layers } from "lucide-react";

import {
  useAddVariant,
  useArchiveVariant,
  useProductVariants,
  useUpdateVariant,
} from "@/lib/hooks/use-menu-products";
import { formatMinorUnits } from "@/lib/crm-display";
import { ApiError } from "@/lib/api/errors";
import { SectionCard } from "@/components/section-card";
import { EmptyState } from "@/components/empty-state";
import { FormField } from "@/components/forms/form-field";
import { CurrencyInput } from "@/components/forms/currency-input";
import { ConfirmDialog } from "@/components/modals/confirm-dialog";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Switch } from "@/components/ui/switch";
import { Skeleton } from "@/components/ui/skeleton";

const schema = z.object({
  code: z.string().trim().min(1, "A code is required.").max(64),
  name: z.string().trim().min(1, "A name is required.").max(120),
  priceRupees: z
    .string()
    .trim()
    .min(1, "A price is required.")
    .refine((v) => Number.isFinite(Number(v)) && Number(v) >= 0, "Enter a valid price."),
});
type Values = z.infer<typeof schema>;

export function ProductVariants({ productId }: { productId: string }) {
  const { data: variants, isLoading } = useProductVariants(productId);
  const addVariant = useAddVariant(productId);
  const updateVariant = useUpdateVariant(productId);
  const archiveVariant = useArchiveVariant(productId);

  const [formError, setFormError] = useState<string | null>(null);
  const [pendingArchiveId, setPendingArchiveId] = useState<string | null>(null);

  const {
    register,
    handleSubmit,
    reset,
    formState: { errors },
  } = useForm<Values>({ resolver: zodResolver(schema) });

  async function onSubmit(values: Values) {
    setFormError(null);
    try {
      await addVariant.mutateAsync({
        code: values.code,
        name: values.name,
        price_minor: Math.round(Number(values.priceRupees) * 100),
      });
      reset();
    } catch (error) {
      setFormError(error instanceof ApiError ? error.message : "The variant could not be saved.");
    }
  }

  return (
    <SectionCard
      title="Variants"
      description="Sizes or configurations of this same product — e.g. 8-inch / 11-inch, Half / Full."
    >
      <div className="flex flex-col gap-4">
        <form
          onSubmit={handleSubmit(onSubmit)}
          className="bg-muted/40 grid gap-3 rounded-md border p-4 sm:grid-cols-4"
          noValidate
        >
          <FormField label="Code" htmlFor="variant-code" required error={errors.code?.message}>
            <Input id="variant-code" {...register("code")} />
          </FormField>
          <FormField label="Name" htmlFor="variant-name" required error={errors.name?.message}>
            <Input id="variant-name" placeholder="11-inch" {...register("name")} />
          </FormField>
          <FormField label="Price" htmlFor="variant-price" required error={errors.priceRupees?.message}>
            <CurrencyInput id="variant-price" {...register("priceRupees")} />
          </FormField>
          <div className="flex items-end">
            <Button type="submit" size="sm" disabled={addVariant.isPending}>
              {addVariant.isPending ? "Adding…" : "Add variant"}
            </Button>
          </div>
          {formError && (
            <p role="alert" className="text-destructive text-sm sm:col-span-4">
              {formError}
            </p>
          )}
        </form>

        {isLoading ? (
          <Skeleton className="h-16 w-full" />
        ) : !variants || variants.length === 0 ? (
          <EmptyState
            icon={Layers}
            title="No variants yet"
            description="Add a size or configuration variant above."
          />
        ) : (
          <ul className="flex flex-col gap-2">
            {variants.map((variant) => (
              <li
                key={variant.id}
                className="flex flex-wrap items-center justify-between gap-3 rounded-md border p-3"
              >
                <div>
                  <p className="font-medium">{variant.name}</p>
                  <p className="text-muted-foreground text-xs">
                    {variant.code} · {formatMinorUnits(variant.price_minor)}
                  </p>
                </div>
                <div className="flex items-center gap-4">
                  <label className="flex items-center gap-2 text-sm">
                    Available
                    <Switch
                      checked={variant.is_available}
                      onCheckedChange={(checked) =>
                        updateVariant.mutate({
                          variantId: variant.id,
                          code: variant.code,
                          name: variant.name,
                          price_minor: variant.price_minor,
                          is_active: variant.is_active,
                          is_available: checked,
                        })
                      }
                    />
                  </label>
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => setPendingArchiveId(variant.id)}
                  >
                    Remove
                  </Button>
                </div>
              </li>
            ))}
          </ul>
        )}
      </div>

      <ConfirmDialog
        open={pendingArchiveId !== null}
        onOpenChange={(open) => {
          if (!open) setPendingArchiveId(null);
        }}
        variant="delete"
        title="Remove this variant?"
        description="It will no longer be orderable, but stays in history for past orders."
        confirmLabel="Remove variant"
        onConfirm={async () => {
          if (!pendingArchiveId) return;
          await archiveVariant.mutateAsync(pendingArchiveId);
          setPendingArchiveId(null);
        }}
      />
    </SectionCard>
  );
}
