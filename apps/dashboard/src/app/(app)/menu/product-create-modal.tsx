"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";

import { useCategoryList } from "@/lib/hooks/use-menu-categories";
import { useCreateProduct } from "@/lib/hooks/use-menu-products";
import { ApiError } from "@/lib/api/errors";
import { Modal } from "@/components/modals/modal";
import { FormField } from "@/components/forms/form-field";
import { CurrencyInput } from "@/components/forms/currency-input";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";

const schema = z.object({
  categoryId: z.string().min(1, "Select a category."),
  name: z.string().trim().min(1, "A name is required.").max(180),
  foodType: z.enum(["vegetarian", "non_vegetarian"]),
  priceRupees: z
    .string()
    .trim()
    .min(1, "A price is required.")
    .refine((v) => Number.isFinite(Number(v)) && Number(v) >= 0, "Enter a valid price."),
  description: z.string().trim().max(4000).optional(),
});
type Values = z.infer<typeof schema>;

export function ProductCreateModal({
  open,
  onOpenChange,
}: {
  open: boolean;
  onOpenChange: (open: boolean) => void;
}) {
  const router = useRouter();
  const [formError, setFormError] = useState<string | null>(null);
  const { data: categories } = useCategoryList({ page: 1, pageSize: 100, sort: "sort_order" });
  const createProduct = useCreateProduct();

  const {
    register,
    handleSubmit,
    watch,
    setValue,
    reset,
    formState: { errors },
  } = useForm<Values>({ resolver: zodResolver(schema), defaultValues: { foodType: "vegetarian" } });

  function resetForm() {
    reset({ foodType: "vegetarian" });
    setFormError(null);
  }

  async function onSubmit(values: Values) {
    setFormError(null);
    try {
      const created = await createProduct.mutateAsync({
        category_id: values.categoryId,
        name: values.name,
        food_type: values.foodType,
        base_price_minor: Math.round(Number(values.priceRupees) * 100),
        description: values.description || null,
      });
      resetForm();
      onOpenChange(false);
      router.push(`/menu/products/${created.data.id}`);
    } catch (error) {
      setFormError(error instanceof ApiError ? error.message : "The product could not be created.");
    }
  }

  return (
    <Modal
      open={open}
      onOpenChange={(next) => {
        if (!next) resetForm();
        onOpenChange(next);
      }}
      title="New product"
      description="Full pricing, dietary detail, variants, and images can be filled in after creating the product."
      footer={
        <>
          <Button type="button" variant="outline" onClick={() => onOpenChange(false)}>
            Cancel
          </Button>
          <Button type="submit" form="product-create-form" disabled={createProduct.isPending}>
            {createProduct.isPending ? "Creating…" : "Create product"}
          </Button>
        </>
      }
    >
      <form
        id="product-create-form"
        onSubmit={handleSubmit(onSubmit)}
        className="grid gap-4 sm:grid-cols-2"
        noValidate
      >
        <FormField label="Name" htmlFor="product-name" required error={errors.name?.message} className="sm:col-span-2">
          <Input id="product-name" {...register("name")} />
        </FormField>

        <FormField label="Category" htmlFor="product-category" required error={errors.categoryId?.message}>
          <Select
            value={watch("categoryId")}
            onValueChange={(value) => setValue("categoryId", value, { shouldDirty: true })}
          >
            <SelectTrigger id="product-category">
              <SelectValue placeholder="Select a category" />
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

        <FormField label="Food type" htmlFor="product-food-type" required>
          <Select
            value={watch("foodType")}
            onValueChange={(value) => setValue("foodType", value as Values["foodType"])}
          >
            <SelectTrigger id="product-food-type">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="vegetarian">Vegetarian</SelectItem>
              <SelectItem value="non_vegetarian">Non-vegetarian</SelectItem>
            </SelectContent>
          </Select>
        </FormField>

        <FormField label="Base price" htmlFor="product-price" required error={errors.priceRupees?.message}>
          <CurrencyInput id="product-price" {...register("priceRupees")} />
        </FormField>

        <FormField label="Description" htmlFor="product-description" className="sm:col-span-2">
          <Textarea id="product-description" rows={3} {...register("description")} />
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
