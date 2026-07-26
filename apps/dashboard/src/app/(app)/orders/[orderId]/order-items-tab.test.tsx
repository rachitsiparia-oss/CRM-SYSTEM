import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";
import type { Order } from "@rkpr/contracts";

import { OrderItemsTab } from "./order-items-tab";

function makeOrder(): Order {
  return {
    id: "order-1",
    order_number: "ORD-TEST0001",
    customer_id: null,
    lead_id: null,
    source: "manual",
    order_type: "takeaway",
    status: "draft",
    payment_status: "pending",
    assigned_staff_id: null,
    subtotal_minor: 24000,
    discount_minor: 1000,
    tax_minor: 450,
    charges_minor: 500,
    grand_total_minor: 23950,
    internal_notes: null,
    customer_notes: null,
    estimated_completion_time: null,
    version: 1,
    created_at: "2026-07-26T10:00:00Z",
    updated_at: "2026-07-26T10:00:00Z",
    items: [
      {
        id: "item-1",
        order_id: "order-1",
        product_id: "product-1",
        variant_id: null,
        product_name_snapshot: "RKPR Classic Veg Burger",
        variant_name_snapshot: null,
        product_code_snapshot: "PROD-0001",
        quantity: 2,
        unit_price_minor: 10000,
        discount_minor: 0,
        tax_minor: 0,
        final_price_minor: 24000,
        kitchen_note: null,
        status: "active",
        modifiers: [
          {
            id: "mod-1",
            modifier_id: "modifier-1",
            modifier_name_snapshot: "Cheese slice",
            price_minor_snapshot: 2000,
            quantity: 1,
          },
        ],
      },
    ],
    discounts: [
      {
        id: "disc-1",
        discount_type: "flat",
        amount_minor: 1000,
        percentage: null,
        reason: "Loyalty discount",
        approved_by: "staff-1",
        created_by: "staff-1",
        created_at: "2026-07-26T10:00:00Z",
      },
    ],
    taxes: [
      { id: "tax-1", tax_name: "GST", rate_percentage: 5, amount_minor: 450, created_at: "2026-07-26T10:00:00Z" },
    ],
    charges: [
      { id: "charge-1", charge_type: "packaging", amount_minor: 500, created_at: "2026-07-26T10:00:00Z" },
    ],
  };
}

describe("OrderItemsTab", () => {
  it("renders each item with its modifiers and the server-computed totals breakdown", () => {
    render(<OrderItemsTab order={makeOrder()} />);

    expect(screen.getByText("RKPR Classic Veg Burger")).toBeInTheDocument();
    expect(screen.getByText(/cheese slice/i)).toBeInTheDocument();
    // Appears twice: once as the item's own line total, once as the
    // subtotal — correct, since this fixture has exactly one item.
    expect(screen.getAllByText("₹240.00")).toHaveLength(2);
    expect(screen.getByText(/loyalty discount/i)).toBeInTheDocument();
    expect(screen.getByText("₹239.50")).toBeInTheDocument();
  });
});
