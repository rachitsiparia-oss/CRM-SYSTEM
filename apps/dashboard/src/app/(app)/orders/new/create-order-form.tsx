"use client";

import { useMemo, useState } from "react";
import { useRouter } from "next/navigation";
import { Plus, Trash2 } from "lucide-react";

import { useCreateOrder, useSearchOrderCustomers } from "@/lib/hooks/use-orders";
import { useProductList, useProductVariants } from "@/lib/hooks/use-menu-products";
import { useModifierList } from "@/lib/hooks/use-menu-modifiers";
import { useCurrentUser } from "@/lib/hooks/use-current-user";
import { useDebouncedValue } from "@/lib/hooks/use-debounced-value";
import { formatMinorUnits, humanize } from "@/lib/crm-display";
import { ApiError } from "@/lib/api/errors";
import { PageHeader } from "@/components/page-header";
import { SectionCard } from "@/components/section-card";
import { FormField } from "@/components/forms/form-field";
import { SearchInput } from "@/components/forms/search-input";
import { CurrencyInput } from "@/components/forms/currency-input";
import { MultiSelect } from "@/components/forms/multi-select";
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

const SOURCES = ["pos", "walk_in", "website", "whatsapp", "phone_call", "zomato", "swiggy", "manual"];
const ORDER_TYPES = ["dine_in", "takeaway", "delivery"];
const DISCOUNT_TYPES = ["flat", "percentage", "manual", "coupon_placeholder", "manager_override"];
const CHARGE_TYPES = ["packaging", "delivery", "service", "other"];

interface DraftItem {
  key: string;
  productId: string;
  productName: string;
  basePriceMinor: number;
  variantId: string | null;
  modifierIds: string[];
  quantity: number;
}

interface DraftDiscount {
  key: string;
  discountType: string;
  amountRupees: string;
  reason: string;
}

interface DraftTax {
  key: string;
  taxName: string;
  ratePercentage: string;
}

interface DraftCharge {
  key: string;
  chargeType: string;
  amountRupees: string;
}

function toMinorUnits(rupees: string): number {
  const parsed = Number(rupees);
  if (!Number.isFinite(parsed) || parsed < 0) return 0;
  return Math.round(parsed * 100);
}

function ItemRow({
  item,
  modifierOptions,
  modifierPriceByModifierId,
  onChange,
  onRemove,
}: {
  item: DraftItem;
  modifierOptions: { label: string; value: string }[];
  modifierPriceByModifierId: Map<string, number>;
  onChange: (next: DraftItem) => void;
  onRemove: () => void;
}) {
  const { data: variants } = useProductVariants(item.productId);

  const unitPriceMinor =
    (item.variantId ? variants?.find((v) => v.id === item.variantId)?.price_minor : undefined) ??
    item.basePriceMinor;
  const modifiersTotalPerUnit = item.modifierIds.reduce(
    (sum, id) => sum + (modifierPriceByModifierId.get(id) ?? 0),
    0,
  );
  const lineTotalMinor = item.quantity * (unitPriceMinor + modifiersTotalPerUnit);

  return (
    <div className="flex flex-col gap-3 rounded-md border p-3">
      <div className="flex items-start justify-between gap-3">
        <div>
          <p className="font-medium">{item.productName}</p>
          <p className="text-muted-foreground text-xs">{formatMinorUnits(unitPriceMinor)} each</p>
        </div>
        <Button type="button" variant="ghost" size="icon" onClick={onRemove} aria-label="Remove item">
          <Trash2 className="size-4" />
        </Button>
      </div>

      <div className="flex flex-wrap items-end gap-3">
        {variants && variants.length > 0 && (
          <FormField label="Variant" htmlFor={`variant-${item.key}`} className="w-40">
            <Select
              value={item.variantId ?? "__base"}
              onValueChange={(value) =>
                onChange({ ...item, variantId: value === "__base" ? null : value })
              }
            >
              <SelectTrigger id={`variant-${item.key}`}>
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="__base">Base price</SelectItem>
                {variants.map((variant) => (
                  <SelectItem key={variant.id} value={variant.id}>
                    {variant.name} ({formatMinorUnits(variant.price_minor)})
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </FormField>
        )}

        <FormField label="Quantity" htmlFor={`qty-${item.key}`} className="w-24">
          <Input
            id={`qty-${item.key}`}
            type="number"
            min={1}
            value={item.quantity}
            onChange={(e) => onChange({ ...item, quantity: Math.max(1, Number(e.target.value) || 1) })}
          />
        </FormField>

        <FormField label="Modifiers" htmlFor={`mods-${item.key}`} className="min-w-56 flex-1">
          <MultiSelect
            options={modifierOptions}
            value={item.modifierIds}
            onChange={(modifierIds) => onChange({ ...item, modifierIds })}
            placeholder="Add-ons…"
          />
        </FormField>
      </div>

      <p className="text-right text-sm font-medium">Line total: {formatMinorUnits(lineTotalMinor)}</p>
    </div>
  );
}

export function CreateOrderForm() {
  const router = useRouter();
  const { data: currentUser } = useCurrentUser();
  const createOrder = useCreateOrder();

  const [source, setSource] = useState("manual");
  const [orderType, setOrderType] = useState("takeaway");
  const [customerQuery, setCustomerQuery] = useState("");
  const [selectedCustomerId, setSelectedCustomerId] = useState<string | null>(null);
  const [selectedCustomerName, setSelectedCustomerName] = useState<string | null>(null);
  const [productQuery, setProductQuery] = useState("");
  const [items, setItems] = useState<DraftItem[]>([]);
  const [discounts, setDiscounts] = useState<DraftDiscount[]>([]);
  const [taxes, setTaxes] = useState<DraftTax[]>([]);
  const [charges, setCharges] = useState<DraftCharge[]>([]);
  const [internalNotes, setInternalNotes] = useState("");
  const [customerNotes, setCustomerNotes] = useState("");
  const [formError, setFormError] = useState<string | null>(null);

  const debouncedCustomerQuery = useDebouncedValue(customerQuery, 300);
  const debouncedProductQuery = useDebouncedValue(productQuery, 300);

  const { data: customerMatches } = useSearchOrderCustomers(debouncedCustomerQuery);
  const { data: productPage } = useProductList({
    page: 1,
    pageSize: 8,
    search: debouncedProductQuery || undefined,
    isActive: true,
  });
  const { data: modifiers } = useModifierList();

  const modifierOptions = useMemo(
    () => (modifiers ?? []).map((m) => ({ label: `${m.name} (${formatMinorUnits(m.default_price_minor)})`, value: m.id })),
    [modifiers],
  );
  const modifierPriceByModifierId = useMemo(
    () => new Map((modifiers ?? []).map((m) => [m.id, m.default_price_minor])),
    [modifiers],
  );

  function addItem(product: { id: string; name: string; base_price_minor: number }) {
    const key = crypto.randomUUID();
    setItems((prev) => [
      ...prev,
      {
        key,
        productId: product.id,
        productName: product.name,
        basePriceMinor: product.base_price_minor,
        variantId: null,
        modifierIds: [],
        quantity: 1,
      },
    ]);
  }

  function addDiscount() {
    setDiscounts((prev) => [
      ...prev,
      { key: crypto.randomUUID(), discountType: "flat", amountRupees: "", reason: "" },
    ]);
  }

  function addTax() {
    setTaxes((prev) => [...prev, { key: crypto.randomUUID(), taxName: "GST", ratePercentage: "5" }]);
  }

  function addCharge() {
    setCharges((prev) => [
      ...prev,
      { key: crypto.randomUUID(), chargeType: "packaging", amountRupees: "" },
    ]);
  }

  const estimatedSubtotalMinor = items.reduce((sum, item) => {
    const modifiersTotal = item.modifierIds.reduce(
      (s, id) => s + (modifierPriceByModifierId.get(id) ?? 0),
      0,
    );
    return sum + item.quantity * (item.basePriceMinor + modifiersTotal);
  }, 0);

  async function onSubmit() {
    setFormError(null);
    if (items.length === 0) {
      setFormError("Add at least one item to the order.");
      return;
    }
    try {
      const created = await createOrder.mutateAsync({
        customerId: selectedCustomerId,
        source,
        orderType,
        items: items.map((item) => ({
          product_id: item.productId,
          variant_id: item.variantId,
          quantity: item.quantity,
          modifiers: item.modifierIds.map((modifier_id) => ({ modifier_id })),
        })),
        discounts: discounts
          .filter((d) => d.reason.trim() && d.amountRupees)
          .map((d) => ({
            discount_type: d.discountType as never,
            amount_minor: toMinorUnits(d.amountRupees),
            reason: d.reason.trim(),
            approved_by: currentUser?.id ?? "",
          })),
        taxes: taxes
          .filter((t) => t.taxName.trim())
          .map((t) => ({
            tax_name: t.taxName.trim(),
            rate_percentage: t.ratePercentage ? Number(t.ratePercentage) : null,
          })),
        charges: charges
          .filter((c) => c.amountRupees)
          .map((c) => ({ charge_type: c.chargeType as never, amount_minor: toMinorUnits(c.amountRupees) })),
        internalNotes: internalNotes.trim() || null,
        customerNotes: customerNotes.trim() || null,
        idempotencyKey: crypto.randomUUID(),
      });
      router.push(`/orders/${created.data.id}`);
    } catch (error) {
      setFormError(error instanceof ApiError ? error.message : "The order could not be created.");
    }
  }

  return (
    <div className="flex flex-1 flex-col gap-6 p-6">
      <PageHeader
        title="New order"
        description="Build the order from the live menu. Totals shown here are an estimate — the server computes the authoritative total on submit."
      />

      <SectionCard title="Order details">
        <div className="grid gap-4 sm:grid-cols-3">
          <FormField label="Source" htmlFor="order-source" required>
            <Select value={source} onValueChange={setSource}>
              <SelectTrigger id="order-source">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {SOURCES.map((option) => (
                  <SelectItem key={option} value={option}>
                    {humanize(option)}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </FormField>

          <FormField label="Order type" htmlFor="order-type" required>
            <Select value={orderType} onValueChange={setOrderType}>
              <SelectTrigger id="order-type">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {ORDER_TYPES.map((option) => (
                  <SelectItem key={option} value={option}>
                    {humanize(option)}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </FormField>

          <FormField label="Customer (optional)" htmlFor="order-customer">
            {selectedCustomerId ? (
              <div className="flex items-center gap-2">
                <span className="text-sm">{selectedCustomerName}</span>
                <Button
                  type="button"
                  variant="ghost"
                  size="sm"
                  onClick={() => {
                    setSelectedCustomerId(null);
                    setSelectedCustomerName(null);
                  }}
                >
                  Clear
                </Button>
              </div>
            ) : (
              <div className="relative">
                <SearchInput
                  id="order-customer"
                  value={customerQuery}
                  onChange={setCustomerQuery}
                  placeholder="Search by name, number, or phone…"
                />
                {customerMatches && customerMatches.length > 0 && (
                  <ul className="bg-popover absolute z-10 mt-1 w-full rounded-md border shadow-md">
                    {customerMatches.map((customer) => (
                      <li key={customer.id}>
                        <button
                          type="button"
                          className="hover:bg-muted w-full px-3 py-2 text-left text-sm"
                          onClick={() => {
                            setSelectedCustomerId(customer.id);
                            setSelectedCustomerName(customer.display_name);
                            setCustomerQuery("");
                          }}
                        >
                          {customer.display_name}{" "}
                          <span className="text-muted-foreground">{customer.customer_number}</span>
                        </button>
                      </li>
                    ))}
                  </ul>
                )}
              </div>
            )}
          </FormField>
        </div>
      </SectionCard>

      <SectionCard title="Items" description="Search the live menu and add items to the order.">
        <div className="flex flex-col gap-4">
          <div className="relative">
            <SearchInput
              value={productQuery}
              onChange={setProductQuery}
              placeholder="Search products…"
            />
            {productPage && productPage.data.length > 0 && (
              <ul className="bg-popover absolute z-10 mt-1 w-full rounded-md border shadow-md">
                {productPage.data.map((product) => (
                  <li key={product.id}>
                    <button
                      type="button"
                      className="hover:bg-muted flex w-full items-center justify-between px-3 py-2 text-left text-sm"
                      onClick={() => addItem(product)}
                    >
                      <span>{product.display_name ?? product.name}</span>
                      <span className="text-muted-foreground">
                        {formatMinorUnits(product.base_price_minor)}
                      </span>
                    </button>
                  </li>
                ))}
              </ul>
            )}
          </div>

          {items.length === 0 ? (
            <p className="text-muted-foreground text-sm">No items added yet.</p>
          ) : (
            <div className="flex flex-col gap-3">
              {items.map((item) => (
                <ItemRow
                  key={item.key}
                  item={item}
                  modifierOptions={modifierOptions}
                  modifierPriceByModifierId={modifierPriceByModifierId}
                  onChange={(next) => setItems((prev) => prev.map((i) => (i.key === next.key ? next : i)))}
                  onRemove={() => setItems((prev) => prev.filter((i) => i.key !== item.key))}
                />
              ))}
            </div>
          )}

          <p className="text-right text-sm font-semibold">
            Estimated subtotal: {formatMinorUnits(estimatedSubtotalMinor)}
          </p>
        </div>
      </SectionCard>

      <SectionCard
        title="Discounts, taxes, and charges"
        description="Discounts require a reason and are audited. The server recomputes the final total regardless of what is entered here."
        actions={
          <div className="flex gap-2">
            <Button type="button" variant="outline" size="sm" onClick={addDiscount}>
              <Plus className="size-4" /> Discount
            </Button>
            <Button type="button" variant="outline" size="sm" onClick={addTax}>
              <Plus className="size-4" /> Tax
            </Button>
            <Button type="button" variant="outline" size="sm" onClick={addCharge}>
              <Plus className="size-4" /> Charge
            </Button>
          </div>
        }
      >
        <div className="flex flex-col gap-3">
          {discounts.map((discount) => (
            <div key={discount.key} className="flex flex-wrap items-end gap-3 rounded-md border p-3">
              <FormField label="Type" htmlFor={`disc-type-${discount.key}`} className="w-40">
                <Select
                  value={discount.discountType}
                  onValueChange={(value) =>
                    setDiscounts((prev) =>
                      prev.map((d) => (d.key === discount.key ? { ...d, discountType: value } : d)),
                    )
                  }
                >
                  <SelectTrigger id={`disc-type-${discount.key}`}>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    {DISCOUNT_TYPES.map((option) => (
                      <SelectItem key={option} value={option}>
                        {humanize(option)}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </FormField>
              <FormField label="Amount" htmlFor={`disc-amt-${discount.key}`} className="w-32">
                <CurrencyInput
                  id={`disc-amt-${discount.key}`}
                  value={discount.amountRupees}
                  onChange={(e) =>
                    setDiscounts((prev) =>
                      prev.map((d) =>
                        d.key === discount.key ? { ...d, amountRupees: e.target.value } : d,
                      ),
                    )
                  }
                />
              </FormField>
              <FormField label="Reason" htmlFor={`disc-reason-${discount.key}`} className="min-w-48 flex-1">
                <Input
                  id={`disc-reason-${discount.key}`}
                  value={discount.reason}
                  onChange={(e) =>
                    setDiscounts((prev) =>
                      prev.map((d) => (d.key === discount.key ? { ...d, reason: e.target.value } : d)),
                    )
                  }
                />
              </FormField>
              <Button
                type="button"
                variant="ghost"
                size="icon"
                onClick={() => setDiscounts((prev) => prev.filter((d) => d.key !== discount.key))}
              >
                <Trash2 className="size-4" />
              </Button>
            </div>
          ))}

          {taxes.map((tax) => (
            <div key={tax.key} className="flex flex-wrap items-end gap-3 rounded-md border p-3">
              <FormField label="Tax name" htmlFor={`tax-name-${tax.key}`} className="w-40">
                <Input
                  id={`tax-name-${tax.key}`}
                  value={tax.taxName}
                  onChange={(e) =>
                    setTaxes((prev) =>
                      prev.map((t) => (t.key === tax.key ? { ...t, taxName: e.target.value } : t)),
                    )
                  }
                />
              </FormField>
              <FormField label="Rate %" htmlFor={`tax-rate-${tax.key}`} className="w-28">
                <Input
                  id={`tax-rate-${tax.key}`}
                  type="number"
                  min={0}
                  max={100}
                  value={tax.ratePercentage}
                  onChange={(e) =>
                    setTaxes((prev) =>
                      prev.map((t) =>
                        t.key === tax.key ? { ...t, ratePercentage: e.target.value } : t,
                      ),
                    )
                  }
                />
              </FormField>
              <Button
                type="button"
                variant="ghost"
                size="icon"
                onClick={() => setTaxes((prev) => prev.filter((t) => t.key !== tax.key))}
              >
                <Trash2 className="size-4" />
              </Button>
            </div>
          ))}

          {charges.map((charge) => (
            <div key={charge.key} className="flex flex-wrap items-end gap-3 rounded-md border p-3">
              <FormField label="Type" htmlFor={`charge-type-${charge.key}`} className="w-40">
                <Select
                  value={charge.chargeType}
                  onValueChange={(value) =>
                    setCharges((prev) =>
                      prev.map((c) => (c.key === charge.key ? { ...c, chargeType: value } : c)),
                    )
                  }
                >
                  <SelectTrigger id={`charge-type-${charge.key}`}>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    {CHARGE_TYPES.map((option) => (
                      <SelectItem key={option} value={option}>
                        {humanize(option)}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </FormField>
              <FormField label="Amount" htmlFor={`charge-amt-${charge.key}`} className="w-32">
                <CurrencyInput
                  id={`charge-amt-${charge.key}`}
                  value={charge.amountRupees}
                  onChange={(e) =>
                    setCharges((prev) =>
                      prev.map((c) =>
                        c.key === charge.key ? { ...c, amountRupees: e.target.value } : c,
                      ),
                    )
                  }
                />
              </FormField>
              <Button
                type="button"
                variant="ghost"
                size="icon"
                onClick={() => setCharges((prev) => prev.filter((c) => c.key !== charge.key))}
              >
                <Trash2 className="size-4" />
              </Button>
            </div>
          ))}
        </div>
      </SectionCard>

      <SectionCard title="Notes">
        <div className="grid gap-4 sm:grid-cols-2">
          <FormField label="Internal notes" htmlFor="order-internal-notes">
            <Textarea
              id="order-internal-notes"
              rows={3}
              value={internalNotes}
              onChange={(e) => setInternalNotes(e.target.value)}
            />
          </FormField>
          <FormField label="Customer notes" htmlFor="order-customer-notes">
            <Textarea
              id="order-customer-notes"
              rows={3}
              value={customerNotes}
              onChange={(e) => setCustomerNotes(e.target.value)}
            />
          </FormField>
        </div>
      </SectionCard>

      {formError && (
        <p role="alert" className="text-destructive text-sm">
          {formError}
        </p>
      )}

      <div className="flex justify-end gap-2">
        <Button type="button" variant="outline" onClick={() => router.push("/orders/list")}>
          Cancel
        </Button>
        <Button type="button" disabled={createOrder.isPending} onClick={() => void onSubmit()}>
          {createOrder.isPending ? "Creating…" : "Create order"}
        </Button>
      </div>
    </div>
  );
}
