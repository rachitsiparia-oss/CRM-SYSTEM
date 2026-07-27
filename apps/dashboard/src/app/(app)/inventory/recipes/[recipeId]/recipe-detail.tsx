"use client";

import { useState } from "react";
import Link from "next/link";
import { ArrowLeft, Plus } from "lucide-react";

import {
  useAddRecipeItem,
  useArchiveInventoryRecipe,
  useInventoryRecipe,
  useInventoryRecipeCost,
} from "@/lib/hooks/use-inventory-recipes";
import { useInventoryItemList } from "@/lib/hooks/use-inventory-items";
import { useInventoryUnits } from "@/lib/hooks/use-inventory-reference";
import { useProductList } from "@/lib/hooks/use-menu-products";
import { hasPermission, useCurrentUser } from "@/lib/hooks/use-current-user";
import { formatMinorUnits, formatQuantity } from "@/lib/crm-display";
import { ApiError } from "@/lib/api/errors";
import { PageHeader } from "@/components/page-header";
import { PageSkeleton } from "@/components/skeletons/page-skeleton";
import { ErrorState } from "@/components/error-state";
import { EmptyState } from "@/components/empty-state";
import { StatusBadge } from "@/components/status-badge";
import { SectionCard } from "@/components/section-card";
import { ConfirmDialog } from "@/components/modals/confirm-dialog";
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
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";

function Field({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <dt className="text-muted-foreground text-xs">{label}</dt>
      <dd className="text-sm">{value}</dd>
    </div>
  );
}

function AddIngredientModal({
  recipeId,
  open,
  onOpenChange,
}: {
  recipeId: string;
  open: boolean;
  onOpenChange: (open: boolean) => void;
}) {
  const { data: itemsPage } = useInventoryItemList({ page: 1, pageSize: 200, sort: "name" });
  const { data: units } = useInventoryUnits();
  const addItem = useAddRecipeItem(recipeId);

  const [inventoryItemId, setInventoryItemId] = useState("");
  const [quantity, setQuantity] = useState("");
  const [unitId, setUnitId] = useState("");
  const [wasteFactor, setWasteFactor] = useState("0");
  const [error, setError] = useState<string | null>(null);

  function resetForm() {
    setInventoryItemId("");
    setQuantity("");
    setUnitId("");
    setWasteFactor("0");
    setError(null);
  }

  async function handleSubmit() {
    setError(null);
    if (!inventoryItemId || !quantity || !unitId) {
      setError("Ingredient, quantity, and unit are required.");
      return;
    }
    try {
      await addItem.mutateAsync({
        inventory_item_id: inventoryItemId,
        quantity_required: quantity,
        unit_id: unitId,
        waste_factor: wasteFactor,
      });
      resetForm();
      onOpenChange(false);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "The ingredient could not be added.");
    }
  }

  return (
    <Modal
      open={open}
      onOpenChange={(next) => {
        if (!next) resetForm();
        onOpenChange(next);
      }}
      title="Add ingredient"
      footer={
        <>
          <Button variant="outline" onClick={() => onOpenChange(false)}>
            Cancel
          </Button>
          <Button disabled={addItem.isPending} onClick={() => void handleSubmit()}>
            {addItem.isPending ? "Adding…" : "Add ingredient"}
          </Button>
        </>
      }
    >
      <div className="grid gap-4">
        <FormField label="Ingredient" htmlFor="ingredient-item" required>
          <Select value={inventoryItemId} onValueChange={setInventoryItemId}>
            <SelectTrigger id="ingredient-item">
              <SelectValue placeholder="Select an inventory item" />
            </SelectTrigger>
            <SelectContent>
              {(itemsPage?.data ?? []).map((item) => (
                <SelectItem key={item.id} value={item.id}>
                  {item.name}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </FormField>
        <FormField label="Quantity required" htmlFor="ingredient-qty" required>
          <Input
            id="ingredient-qty"
            inputMode="decimal"
            value={quantity}
            onChange={(e) => setQuantity(e.target.value)}
          />
        </FormField>
        <FormField label="Unit" htmlFor="ingredient-unit" required>
          <Select value={unitId} onValueChange={setUnitId}>
            <SelectTrigger id="ingredient-unit">
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
        <FormField label="Waste factor (0–1)" htmlFor="ingredient-waste">
          <Input
            id="ingredient-waste"
            inputMode="decimal"
            value={wasteFactor}
            onChange={(e) => setWasteFactor(e.target.value)}
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

export function RecipeDetail({ recipeId }: { recipeId: string }) {
  const { data: currentUser } = useCurrentUser();
  const { data: recipe, isLoading, isError, refetch } = useInventoryRecipe(recipeId);
  const { data: cost } = useInventoryRecipeCost(recipeId);
  const { data: products } = useProductList({ page: 1, pageSize: 200, sort: "alphabetical" });
  const { data: units } = useInventoryUnits();
  const archiveRecipe = useArchiveInventoryRecipe(recipeId);

  const [showAddIngredient, setShowAddIngredient] = useState(false);
  const [confirmArchive, setConfirmArchive] = useState(false);
  const [actionError, setActionError] = useState<string | null>(null);

  const canManage = hasPermission(currentUser, "inventory.recipes.manage");
  const canViewCost = hasPermission(currentUser, "inventory.cost.view");

  if (isLoading) {
    return (
      <div className="flex-1 p-6">
        <PageSkeleton />
      </div>
    );
  }

  if (isError || !recipe) {
    return (
      <div className="flex-1 p-6">
        <ErrorState variant="404" title="Recipe not found" onRetry={() => void refetch()} />
      </div>
    );
  }

  const productName = products?.data.find((p) => p.id === recipe.product_id)?.display_name ??
    products?.data.find((p) => p.id === recipe.product_id)?.name ??
    "—";
  const unitSymbol = (id: string) => units?.find((u) => u.id === id)?.symbol ?? "";

  return (
    <div className="flex flex-1 flex-col gap-6 p-6">
      <div>
        <Link
          href="/inventory/recipes"
          className="text-muted-foreground inline-flex items-center gap-1 text-sm hover:underline"
        >
          <ArrowLeft className="size-3.5" />
          Recipes
        </Link>
      </div>

      <PageHeader
        title={productName}
        description={`${recipe.recipe_code} · ${recipe.variant_id ? "Variant-specific" : "Base recipe"}`}
        actions={
          <div className="flex items-center gap-2">
            <StatusBadge
              label={recipe.is_active ? "Active" : "Archived"}
              tone={recipe.is_active ? "success" : "neutral"}
            />
            {canManage && recipe.is_active && (
              <Button variant="outline" size="sm" onClick={() => setShowAddIngredient(true)}>
                <Plus className="size-4" />
                Add ingredient
              </Button>
            )}
            {canManage && recipe.is_active && (
              <Button variant="destructive" size="sm" onClick={() => setConfirmArchive(true)}>
                Archive
              </Button>
            )}
          </div>
        }
      />

      <SectionCard title="Recipe details">
        <dl className="grid grid-cols-2 gap-4 sm:grid-cols-4">
          <Field label="Yield" value={formatQuantity(recipe.yield_quantity)} />
          <Field label="Preparation loss" value={`${recipe.preparation_loss_percentage}%`} />
          <Field
            label="Effective from"
            value={new Date(recipe.effective_from).toLocaleDateString("en-IN")}
          />
          <Field label="Notes" value={recipe.notes ?? "—"} />
        </dl>
      </SectionCard>

      <SectionCard title="Ingredients">
        {recipe.items.length === 0 ? (
          <EmptyState title="No ingredients yet" description="Add ingredients to define this recipe." />
        ) : (
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Ingredient</TableHead>
                <TableHead>Required quantity</TableHead>
                <TableHead>Base quantity</TableHead>
                <TableHead>Waste factor</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {recipe.items.map((item) => (
                <TableRow key={item.id}>
                  <TableCell>
                    {cost?.ingredients.find((i) => i.recipe_item_id === item.id)
                      ?.inventory_item_name ?? item.inventory_item_id}
                  </TableCell>
                  <TableCell>
                    {formatQuantity(item.quantity_required, unitSymbol(item.unit_id))}
                  </TableCell>
                  <TableCell>{formatQuantity(item.base_quantity)}</TableCell>
                  <TableCell>{item.waste_factor}</TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        )}
      </SectionCard>

      {canViewCost && cost && (
        <SectionCard title="Costing" description="Uses standard cost, falling back to latest purchase cost.">
          {cost.missing_cost_item_names.length > 0 ? (
            <EmptyState
              title="Cost cannot be calculated"
              description={`Missing cost data for: ${cost.missing_cost_item_names.join(", ")}`}
            />
          ) : (
            <dl className="grid grid-cols-2 gap-4 sm:grid-cols-4">
              <Field
                label="Total ingredient cost"
                value={formatMinorUnits(cost.total_ingredient_cost_minor)}
              />
              <Field label="Cost per yield" value={formatMinorUnits(cost.cost_per_yield_minor)} />
              <Field label="Selling price" value={formatMinorUnits(cost.selling_price_minor)} />
              <Field
                label="Gross margin"
                value={
                  cost.gross_margin_percentage !== null
                    ? `${formatMinorUnits(cost.gross_margin_minor)} (${cost.gross_margin_percentage}%)`
                    : "—"
                }
              />
            </dl>
          )}
        </SectionCard>
      )}

      {actionError && (
        <p role="alert" className="text-destructive text-sm">
          {actionError}
        </p>
      )}

      <AddIngredientModal recipeId={recipeId} open={showAddIngredient} onOpenChange={setShowAddIngredient} />

      <ConfirmDialog
        open={confirmArchive}
        onOpenChange={setConfirmArchive}
        variant="warning"
        title="Archive this recipe?"
        description="Order-to-inventory integration will treat this product as not inventory-tracked once archived."
        confirmLabel="Archive recipe"
        onConfirm={async () => {
          setActionError(null);
          try {
            await archiveRecipe.mutateAsync();
          } catch (err) {
            setActionError(err instanceof ApiError ? err.message : "The recipe could not be archived.");
          }
        }}
      />
    </div>
  );
}
