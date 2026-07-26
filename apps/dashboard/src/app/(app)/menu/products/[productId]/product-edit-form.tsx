"use client";

import { useState } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import type { Product } from "@rkpr/contracts";

import { useCategoryList } from "@/lib/hooks/use-menu-categories";
import { useSetAvailabilityOverride, useUpdateProduct } from "@/lib/hooks/use-menu-products";
import { ApiError } from "@/lib/api/errors";
import { SectionCard } from "@/components/section-card";
import { FormField } from "@/components/forms/form-field";
import { CurrencyInput } from "@/components/forms/currency-input";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Checkbox } from "@/components/ui/checkbox";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";

const SPICE_LEVELS = ["mild", "medium", "hot", "extra_hot"];
const UNSET = "__unset";

const schema = z.object({
  categoryId: z.string().min(1),
  name: z.string().trim().min(1, "A name is required.").max(180),
  displayName: z.string().trim().max(180).optional(),
  shortDescription: z.string().trim().max(240).optional(),
  description: z.string().trim().max(4000).optional(),
  barcode: z.string().trim().max(64).optional(),
  foodType: z.enum(["vegetarian", "non_vegetarian"]),
  spiceLevel: z.string(),
  priceRupees: z
    .string()
    .trim()
    .min(1, "A price is required.")
    .refine((v) => Number.isFinite(Number(v)) && Number(v) >= 0, "Enter a valid price."),
  taxCategory: z.string().trim().max(64).optional(),
  preparationMinutes: z.string().trim().optional(),
  calories: z.string().trim().optional(),
  isJainCapable: z.boolean(),
  isVeganCapable: z.boolean(),
  containsEgg: z.boolean(),
  containsDairy: z.boolean(),
  containsGluten: z.boolean(),
  containsNuts: z.boolean(),
  containsSoy: z.boolean(),
  containsAlcohol: z.boolean(),
  dineInAvailable: z.boolean(),
  takeawayAvailable: z.boolean(),
  deliveryAvailable: z.boolean(),
  isFeatured: z.boolean(),
  isChefRecommended: z.boolean(),
});
type Values = z.infer<typeof schema>;

function toNullable(value: string): string | null {
  return value === UNSET || value === "" ? null : value;
}

function toIntOrNull(value: string): number | null {
  if (!value.trim()) return null;
  const parsed = Number(value);
  return Number.isFinite(parsed) ? Math.round(parsed) : null;
}

export function ProductEditForm({ product }: { product: Product }) {
  const [formError, setFormError] = useState<string | null>(null);
  const [saved, setSaved] = useState(false);
  const { data: categories } = useCategoryList({ page: 1, pageSize: 100, sort: "sort_order" });
  const updateProduct = useUpdateProduct(product.id);
  const setAvailabilityOverride = useSetAvailabilityOverride(product.id);
  const [overrideReason, setOverrideReason] = useState("");

  const {
    register,
    handleSubmit,
    watch,
    setValue,
    formState: { errors, isDirty },
  } = useForm<Values>({
    resolver: zodResolver(schema),
    defaultValues: {
      categoryId: product.category_id,
      name: product.name,
      displayName: product.display_name ?? "",
      shortDescription: product.short_description ?? "",
      description: product.description ?? "",
      barcode: product.barcode ?? "",
      foodType: product.food_type,
      spiceLevel: product.spice_level ?? UNSET,
      priceRupees: (product.base_price_minor / 100).toString(),
      taxCategory: product.tax_category ?? "",
      preparationMinutes: product.preparation_minutes?.toString() ?? "",
      calories: product.calories?.toString() ?? "",
      isJainCapable: product.is_jain_capable,
      isVeganCapable: product.is_vegan_capable,
      containsEgg: product.contains_egg,
      containsDairy: product.contains_dairy,
      containsGluten: product.contains_gluten,
      containsNuts: product.contains_nuts,
      containsSoy: product.contains_soy,
      containsAlcohol: product.contains_alcohol,
      dineInAvailable: product.dine_in_available,
      takeawayAvailable: product.takeaway_available,
      deliveryAvailable: product.delivery_available,
      isFeatured: product.is_featured,
      isChefRecommended: product.is_chef_recommended,
    },
  });

  async function onSubmit(values: Values) {
    setFormError(null);
    setSaved(false);
    try {
      await updateProduct.mutateAsync({
        category_id: values.categoryId,
        name: values.name,
        display_name: values.displayName || null,
        short_description: values.shortDescription || null,
        description: values.description || null,
        barcode: values.barcode || null,
        food_type: values.foodType,
        spice_level: toNullable(values.spiceLevel),
        base_price_minor: Math.round(Number(values.priceRupees) * 100),
        tax_category: values.taxCategory || null,
        preparation_minutes: toIntOrNull(values.preparationMinutes ?? ""),
        calories: toIntOrNull(values.calories ?? ""),
        is_jain_capable: values.isJainCapable,
        is_vegan_capable: values.isVeganCapable,
        contains_egg: values.containsEgg,
        contains_dairy: values.containsDairy,
        contains_gluten: values.containsGluten,
        contains_nuts: values.containsNuts,
        contains_soy: values.containsSoy,
        contains_alcohol: values.containsAlcohol,
        dine_in_available: values.dineInAvailable,
        takeaway_available: values.takeawayAvailable,
        delivery_available: values.deliveryAvailable,
        is_featured: values.isFeatured,
        is_chef_recommended: values.isChefRecommended,
        expected_version: product.version,
      });
      setSaved(true);
    } catch (error) {
      if (error instanceof ApiError && error.status === 409) {
        setFormError(
          "Someone else updated this product while you were editing. Reload to see their changes.",
        );
        return;
      }
      setFormError(error instanceof ApiError ? error.message : "The changes could not be saved.");
    }
  }

  const dietaryCheckboxes: { key: keyof Values; label: string }[] = [
    { key: "isJainCapable", label: "Jain capable" },
    { key: "isVeganCapable", label: "Vegan capable" },
    { key: "containsEgg", label: "Contains egg" },
    { key: "containsDairy", label: "Contains dairy" },
    { key: "containsGluten", label: "Contains gluten" },
    { key: "containsNuts", label: "Contains nuts" },
    { key: "containsSoy", label: "Contains soy" },
    { key: "containsAlcohol", label: "Contains alcohol" },
  ];

  const channelCheckboxes: { key: keyof Values; label: string }[] = [
    { key: "dineInAvailable", label: "Dine-in" },
    { key: "takeawayAvailable", label: "Takeaway" },
    { key: "deliveryAvailable", label: "Delivery" },
  ];

  return (
    <div className="flex flex-col gap-4">
      <SectionCard title="Edit product">
        <form onSubmit={handleSubmit(onSubmit)} className="grid gap-4 sm:grid-cols-3" noValidate>
          <FormField label="Name" htmlFor="edit-name" required error={errors.name?.message}>
            <Input id="edit-name" {...register("name")} />
          </FormField>
          <FormField label="Display name" htmlFor="edit-display-name">
            <Input id="edit-display-name" {...register("displayName")} />
          </FormField>
          <FormField label="Category" htmlFor="edit-category" required>
            <Select
              value={watch("categoryId")}
              onValueChange={(value) => setValue("categoryId", value, { shouldDirty: true })}
            >
              <SelectTrigger id="edit-category">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {(categories?.data ?? []).map((category) => (
                  <SelectItem key={category.id} value={category.id}>
                    {category.name}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </FormField>

          <FormField label="Short description" htmlFor="edit-short-desc" className="sm:col-span-3">
            <Input id="edit-short-desc" {...register("shortDescription")} />
          </FormField>
          <FormField label="Description" htmlFor="edit-description" className="sm:col-span-3">
            <Textarea id="edit-description" rows={3} {...register("description")} />
          </FormField>

          <FormField label="Base price" htmlFor="edit-price" required error={errors.priceRupees?.message}>
            <CurrencyInput id="edit-price" {...register("priceRupees")} />
          </FormField>
          <FormField label="Tax category" htmlFor="edit-tax">
            <Input id="edit-tax" placeholder="GST-5" {...register("taxCategory")} />
          </FormField>
          <FormField label="Barcode" htmlFor="edit-barcode">
            <Input id="edit-barcode" {...register("barcode")} />
          </FormField>

          <FormField label="Food type" htmlFor="edit-food-type" required>
            <Select
              value={watch("foodType")}
              onValueChange={(value) => setValue("foodType", value as Values["foodType"])}
            >
              <SelectTrigger id="edit-food-type">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="vegetarian">Vegetarian</SelectItem>
                <SelectItem value="non_vegetarian">Non-vegetarian</SelectItem>
              </SelectContent>
            </Select>
          </FormField>
          <FormField label="Spice level" htmlFor="edit-spice">
            <Select
              value={watch("spiceLevel")}
              onValueChange={(value) => setValue("spiceLevel", value)}
            >
              <SelectTrigger id="edit-spice">
                <SelectValue placeholder="Not set" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value={UNSET}>Not set</SelectItem>
                {SPICE_LEVELS.map((level) => (
                  <SelectItem key={level} value={level}>
                    {level.replace("_", " ")}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </FormField>
          <FormField label="Preparation time (minutes)" htmlFor="edit-prep">
            <Input id="edit-prep" type="number" min={0} {...register("preparationMinutes")} />
          </FormField>
          <FormField label="Calories" htmlFor="edit-calories">
            <Input id="edit-calories" type="number" min={0} {...register("calories")} />
          </FormField>

          <div className="sm:col-span-3">
            <p className="mb-2 text-sm font-medium">Dietary information and allergens</p>
            <div className="grid grid-cols-2 gap-2 sm:grid-cols-4">
              {dietaryCheckboxes.map(({ key, label }) => (
                <label key={key} className="flex items-center gap-2 text-sm">
                  <Checkbox
                    checked={watch(key) as boolean}
                    onCheckedChange={(checked) =>
                      setValue(key, checked === true, { shouldDirty: true })
                    }
                  />
                  {label}
                </label>
              ))}
            </div>
          </div>

          <div className="sm:col-span-3">
            <p className="mb-2 text-sm font-medium">Channel availability</p>
            <div className="flex gap-4">
              {channelCheckboxes.map(({ key, label }) => (
                <label key={key} className="flex items-center gap-2 text-sm">
                  <Checkbox
                    checked={watch(key) as boolean}
                    onCheckedChange={(checked) =>
                      setValue(key, checked === true, { shouldDirty: true })
                    }
                  />
                  {label}
                </label>
              ))}
            </div>
          </div>

          <div className="flex gap-4 sm:col-span-3">
            <label className="flex items-center gap-2 text-sm">
              <Checkbox
                checked={watch("isFeatured")}
                onCheckedChange={(checked) =>
                  setValue("isFeatured", checked === true, { shouldDirty: true })
                }
              />
              Featured
            </label>
            <label className="flex items-center gap-2 text-sm">
              <Checkbox
                checked={watch("isChefRecommended")}
                onCheckedChange={(checked) =>
                  setValue("isChefRecommended", checked === true, { shouldDirty: true })
                }
              />
              Chef recommendation
            </label>
          </div>

          {formError && (
            <p role="alert" className="text-destructive sm:col-span-3 text-sm">
              {formError}
            </p>
          )}
          {saved && !formError && (
            <p className="text-success sm:col-span-3 text-sm">Changes saved.</p>
          )}

          <div className="sm:col-span-3">
            <Button type="submit" disabled={updateProduct.isPending || !isDirty}>
              {updateProduct.isPending ? "Saving…" : "Save changes"}
            </Button>
          </div>
        </form>
      </SectionCard>

      <SectionCard
        title="Availability override"
        description="Manually mark this product available or unavailable, with a reason recorded in the audit trail."
      >
        <div className="flex flex-wrap items-end gap-3">
          <FormField label="Reason" htmlFor="override-reason" className="min-w-64 flex-1">
            <Input
              id="override-reason"
              value={overrideReason}
              onChange={(e) => setOverrideReason(e.target.value)}
              placeholder="e.g. Out of vegetable patties"
            />
          </FormField>
          <Button
            variant="outline"
            className="mb-1"
            disabled={!overrideReason.trim() || setAvailabilityOverride.isPending}
            onClick={() =>
              setAvailabilityOverride.mutate(
                { isAvailable: !product.is_available, reason: overrideReason.trim() },
                { onSuccess: () => setOverrideReason("") },
              )
            }
          >
            Mark {product.is_available ? "unavailable" : "available"}
          </Button>
        </div>
      </SectionCard>
    </div>
  );
}
