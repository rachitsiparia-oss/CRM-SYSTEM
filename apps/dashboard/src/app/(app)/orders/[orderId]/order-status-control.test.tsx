import type { ReactElement } from "react";
import { describe, expect, it, vi } from "vitest";
import { fireEvent, render, screen } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import type { Order } from "@rkpr/contracts";

import { OrderStatusControl } from "./order-status-control";
import * as useOrdersModule from "@/lib/hooks/use-orders";

function renderWithQueryClient(ui: ReactElement) {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(<QueryClientProvider client={queryClient}>{ui}</QueryClientProvider>);
}

function makeOrder(overrides: Partial<Order> = {}): Order {
  return {
    id: "order-1",
    order_number: "ORD-TEST0001",
    customer_id: null,
    lead_id: null,
    source: "manual",
    order_type: "takeaway",
    status: "pending_confirmation",
    payment_status: "pending",
    assigned_staff_id: null,
    subtotal_minor: 10000,
    discount_minor: 0,
    tax_minor: 0,
    charges_minor: 0,
    grand_total_minor: 10000,
    internal_notes: null,
    customer_notes: null,
    estimated_completion_time: null,
    version: 1,
    created_at: "2026-07-26T10:00:00Z",
    updated_at: "2026-07-26T10:00:00Z",
    items: [],
    discounts: [],
    taxes: [],
    charges: [],
    ...overrides,
  };
}

function mockTransitionOrder() {
  vi.spyOn(useOrdersModule, "useTransitionOrder").mockReturnValue({
    mutateAsync: vi.fn(),
    isPending: false,
  } as unknown as ReturnType<typeof useOrdersModule.useTransitionOrder>);
}

describe("OrderStatusControl", () => {
  it("offers only the two transitions app.orders.states allows from pending_confirmation", () => {
    mockTransitionOrder();
    renderWithQueryClient(<OrderStatusControl order={makeOrder({ status: "pending_confirmation" })} />);
    expect(screen.getByRole("button", { name: "Confirmed" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Cancelled" })).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Preparing" })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Completed" })).not.toBeInTheDocument();
  });

  it("does not offer cancellation from confirmed — matches the backend's strict transition table", () => {
    mockTransitionOrder();
    renderWithQueryClient(<OrderStatusControl order={makeOrder({ status: "confirmed" })} />);
    expect(screen.getByRole("button", { name: "Preparing" })).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Cancelled" })).not.toBeInTheDocument();
  });

  it("shows no available transitions once completed", () => {
    mockTransitionOrder();
    renderWithQueryClient(<OrderStatusControl order={makeOrder({ status: "completed" })} />);
    expect(screen.getByText(/reached the end of the workflow/i)).toBeInTheDocument();
    expect(screen.queryByRole("button")).not.toBeInTheDocument();
  });

  it("requires confirmation before cancelling", () => {
    mockTransitionOrder();
    renderWithQueryClient(<OrderStatusControl order={makeOrder({ status: "preparing" })} />);
    fireEvent.click(screen.getByRole("button", { name: "Cancelled" }));
    expect(screen.getByText(/cancel this order\?/i)).toBeInTheDocument();
  });
});
