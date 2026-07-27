"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";

import { useCreateInventoryRecipe } from "@/lib/hooks/use-inventory-recipes";
import { useInventoryUnits } from "@/lib/hooks/use-inventory-reference";
import { useProductList, useProductVariants } from "@/lib/hooks/use-menu-products";
import { ApiError } from "@/lib/api/errors";
import { Modal } from "@/components/modals/modal";
import { FormField } from "@/components/forms/form-field";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";

const NONE = "__none";

export function RecipeCreateModal({
  open,
  onOpenChange,
}: {
  open: boolean;
  onOpenChange: (open: boolean) => void;
}) {
  const router = useRouter();
  const { data: products } = useProductList({ page: 1, pageSize: 200, sort: "alphabetical" });
  const { data: units } = useInventoryUnits();
  const createRecipe = useCreateInventoryRecipe();

  const [productId, setProductId] = useState("");
  const [variantId, setVariantId] = useState(NONE);
  const [yieldQuantity, setYieldQuantity] = useState("1");
  const [yieldUnitId, setYieldUnitId] = useState("");
  const [preparationLoss, setPreparationLoss] = useState("0");
  const [error, setError] = useState<string | null>(null);

  const { data: variants } = useProductVariants(productId || undefined);

  function resetForm() {
    setProductId("");
    setVariantId(NONE);
    setYieldQuantity("1");
    setYieldUnitId("");
    setPreparationLoss("0");
    setError(null);
  }

  async function handleSubmit() {
    setError(null);
    if (!productId) {
      setError("Select a product.");
      return;
    }
    try {
      const created = await createRecipe.mutateAsync({
        product_id: productId,
        variant_id: variantId === NONE ? null : variantId,
        yield_quantity: yieldQuantity,
        yield_unit_id: yieldUnitId || null,
        preparation_loss_percentage: preparationLoss,
      });
      resetForm();
      onOpenChange(false);
      router.push(`/inventory/recipes/${created.data.id}`);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "The recipe could not be created.");
    }
  }

  return (
    <Modal
      open={open}
      onOpenChange={(next) => {
        if (!next) resetForm();
        onOpenChange(next);
      }}
      title="New recipe"
      description="Ingredients are added after creating the recipe."
      footer={
        <>
          <Button variant="outline" onClick={() => onOpenChange(false)}>
            Cancel
          </Button>
          <Button disabled={createRecipe.isPending} onClick={() => void handleSubmit()}>
            {createRecipe.isPending ? "Creating…" : "Create recipe"}
          </Button>
        </>
      }
    >
      <div className="grid gap-4">
        <FormField label="Product" htmlFor="recipe-product" required>
          <Select
            value={productId}
            onValueChange={(value) => {
              setProductId(value);
              setVariantId(NONE);
            }}
          >
            <SelectTrigger id="recipe-product">
              <SelectValue placeholder="Select a product" />
            </SelectTrigger>
            <SelectContent>
              {(products?.data ?? []).map((product) => (
                <SelectItem key={product.id} value={product.id}>
                  {product.display_name ?? product.name}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </FormField>

        {variants && variants.length > 0 && (
          <FormField label="Variant" htmlFor="recipe-variant">
            <Select value={variantId} onValueChange={setVariantId}>
              <SelectTrigger id="recipe-variant">
                <SelectValue placeholder="Base recipe (no variant)" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value={NONE}>Base recipe (no variant)</SelectItem>
                {variants.map((variant) => (
                  <SelectItem key={variant.id} value={variant.id}>
                    {variant.name}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </FormField>
        )}

        <FormField label="Yield quantity" htmlFor="recipe-yield" required>
          <Input
            id="recipe-yield"
            inputMode="decimal"
            value={yieldQuantity}
            onChange={(e) => setYieldQuantity(e.target.value)}
          />
        </FormField>

        <FormField label="Yield unit" htmlFor="recipe-yield-unit">
          <Select value={yieldUnitId} onValueChange={setYieldUnitId}>
            <SelectTrigger id="recipe-yield-unit">
              <SelectValue placeholder="Select a unit" />
            </SelectTrigger>
            <SelectContent>
              {(units ?? []).map((unit) => (
                <SelectItem key={unit.id} value={unit.id}>
                  {unit.name} ({unit.symbol})
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </FormField>

        <FormField label="Preparation loss %" htmlFor="recipe-loss">
          <Input
            id="recipe-loss"
            inputMode="decimal"
            value={preparationLoss}
            onChange={(e) => setPreparationLoss(e.target.value)}
          />
        </FormField>

        {error && (
          <p role="alert" className="text-destructive text-sm">
            {error}
          </p>
        )}
      </div>
    </Modal>
  );
}
