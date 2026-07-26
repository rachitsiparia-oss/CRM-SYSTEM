import type { ReactElement } from "react";
import { describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import type { CurrentUser, OrderPayment } from "@rkpr/contracts";

import { OrderPaymentsTab } from "./order-payments-tab";
import * as useCurrentUserModule from "@/lib/hooks/use-current-user";
import * as useOrdersModule from "@/lib/hooks/use-orders";

function renderWithQueryClient(ui: ReactElement) {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(<QueryClientProvider client={queryClient}>{ui}</QueryClientProvider>);
}

const PAYMENTS: OrderPayment[] = [
  {
    id: "pay-1",
    order_id: "order-1",
    method: "cash",
    status: "paid",
    amount_minor: 10000,
    reference: null,
    notes: null,
    recorded_by: "staff-1",
    recorded_at: "2026-07-26T10:00:00Z",
    updated_at: null,
    updated_by: null,
  },
];

function mockCurrentUser(permissions: string[]) {
  vi.spyOn(useCurrentUserModule, "useCurrentUser").mockReturnValue({
    data: { permissions } as CurrentUser,
    isLoading: false,
  } as ReturnType<typeof useCurrentUserModule.useCurrentUser>);
}

function mockHooks(payments: OrderPayment[]) {
  vi.spyOn(useOrdersModule, "useOrderPayments").mockReturnValue({
    data: payments,
    isLoading: false,
  } as unknown as ReturnType<typeof useOrdersModule.useOrderPayments>);
  vi.spyOn(useOrdersModule, "useAddOrderPayment").mockReturnValue({
    mutateAsync: vi.fn(),
    isPending: false,
  } as unknown as ReturnType<typeof useOrdersModule.useAddOrderPayment>);
  vi.spyOn(useOrdersModule, "useUpdateOrderPaymentStatus").mockReturnValue({
    mutate: vi.fn(),
    isPending: false,
  } as unknown as ReturnType<typeof useOrdersModule.useUpdateOrderPaymentStatus>);
}

describe("OrderPaymentsTab", () => {
  it("shows the record-payment form for a user with orders.payments.manage", () => {
    mockCurrentUser(["orders.view", "orders.payments.manage"]);
    mockHooks(PAYMENTS);
    renderWithQueryClient(<OrderPaymentsTab orderId="order-1" />);
    expect(screen.getByRole("button", { name: /record payment/i })).toBeInTheDocument();
  });

  it("hides the record-payment form for a user without orders.payments.manage", () => {
    mockCurrentUser(["orders.view"]);
    mockHooks(PAYMENTS);
    renderWithQueryClient(<OrderPaymentsTab orderId="order-1" />);
    expect(screen.queryByRole("button", { name: /record payment/i })).not.toBeInTheDocument();
  });

  it("renders recorded payment history", () => {
    mockCurrentUser(["orders.view"]);
    mockHooks(PAYMENTS);
    renderWithQueryClient(<OrderPaymentsTab orderId="order-1" />);
    expect(screen.getByText(/via cash/i)).toBeInTheDocument();
  });

  it("shows an empty state when there are no payments", () => {
    mockCurrentUser(["orders.view"]);
    mockHooks([]);
    renderWithQueryClient(<OrderPaymentsTab orderId="order-1" />);
    expect(screen.getByText(/no payments recorded/i)).toBeInTheDocument();
  });
});
