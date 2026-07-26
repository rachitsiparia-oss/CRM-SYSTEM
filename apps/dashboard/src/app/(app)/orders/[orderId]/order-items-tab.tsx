import type { Order } from "@rkpr/contracts";

import { formatMinorUnits } from "@/lib/crm-display";
import { SectionCard } from "@/components/section-card";
import { EmptyState } from "@/components/empty-state";
import { Package } from "lucide-react";

export function OrderItemsTab({ order }: { order: Order }) {
  if (order.items.length === 0) {
    return (
      <SectionCard title="Items">
        <EmptyState icon={Package} title="No items" description="This order has no line items." />
      </SectionCard>
    );
  }

  return (
    <SectionCard title="Items" description="Product, variant, and modifier prices are snapshots taken at order time — later menu changes never alter them.">
      <div className="flex flex-col gap-3">
        {order.items.map((item) => (
          <div key={item.id} className="flex items-start justify-between gap-3 rounded-md border p-3">
            <div>
              <p className="font-medium">
                {item.product_name_snapshot}
                {item.variant_name_snapshot ? ` (${item.variant_name_snapshot})` : ""}
                {item.status === "cancelled" && (
                  <span className="text-destructive ml-2 text-xs font-normal">Cancelled</span>
                )}
              </p>
              <p className="text-muted-foreground text-xs">
                {item.quantity} × {formatMinorUnits(item.unit_price_minor)}
              </p>
              {item.modifiers.length > 0 && (
                <ul className="text-muted-foreground mt-1 text-xs">
                  {item.modifiers.map((modifier) => (
                    <li key={modifier.id}>
                      + {modifier.modifier_name_snapshot} ({formatMinorUnits(modifier.price_minor_snapshot)}
                      {modifier.quantity > 1 ? ` × ${modifier.quantity}` : ""})
                    </li>
                  ))}
                </ul>
              )}
              {item.kitchen_note && (
                <p className="text-muted-foreground mt-1 text-xs italic">Note: {item.kitchen_note}</p>
              )}
            </div>
            <span className="text-sm font-medium">{formatMinorUnits(item.final_price_minor)}</span>
          </div>
        ))}

        <div className="mt-2 flex flex-col gap-1 border-t pt-3 text-sm">
          <div className="flex justify-between">
            <span className="text-muted-foreground">Subtotal</span>
            <span>{formatMinorUnits(order.subtotal_minor)}</span>
          </div>
          {order.discounts.map((discount) => (
            <div key={discount.id} className="flex justify-between">
              <span className="text-muted-foreground">Discount ({discount.reason})</span>
              <span>-{formatMinorUnits(discount.amount_minor)}</span>
            </div>
          ))}
          {order.taxes.map((tax) => (
            <div key={tax.id} className="flex justify-between">
              <span className="text-muted-foreground">{tax.tax_name}</span>
              <span>{formatMinorUnits(tax.amount_minor)}</span>
            </div>
          ))}
          {order.charges.map((charge) => (
            <div key={charge.id} className="flex justify-between">
              <span className="text-muted-foreground">{charge.charge_type}</span>
              <span>{formatMinorUnits(charge.amount_minor)}</span>
            </div>
          ))}
          <div className="flex justify-between text-base font-semibold">
            <span>Grand total</span>
            <span>{formatMinorUnits(order.grand_total_minor)}</span>
          </div>
        </div>
      </div>
    </SectionCard>
  );
}
