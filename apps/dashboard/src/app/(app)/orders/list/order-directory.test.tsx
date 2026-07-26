import type { ReactElement } from "react";
import { describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import type { CurrentUser, OrderListItem, PaginatedResponse } from "@rkpr/contracts";

import { OrderDirectory } from "./order-directory";
import * as useCurrentUserModule from "@/lib/hooks/use-current-user";
import * as useOrdersModule from "@/lib/hooks/use-orders";

vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: vi.fn() }),
  usePathname: () => "/orders/list",
}));

function renderWithQueryClient(ui: ReactElement) {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(<QueryClientProvider client={queryClient}>{ui}</QueryClientProvider>);
}

const EMPTY_LIST: PaginatedResponse<OrderListItem> = {
  data: [],
  pagination: { page: 1, page_size: 25, total: 0 },
  meta: { request_id: "test" },
};

// Two real rows, not zero — the DataTable component had a latent bug
// (uncontrolled rowSelection state) that only threw once at least one row
// actually rendered; this fixture exercises real row rendering rather than
// only the empty state, the same precedent Phase 5/6's tests established.
const TWO_ORDERS: PaginatedResponse<OrderListItem> = {
  data: [
    {
      id: "11111111-1111-1111-1111-111111111111",
      order_number: "ORD-AAAA1111",
      customer_id: null,
      source: "pos",
      order_type: "dine_in",
      status: "preparing",
      payment_status: "pending",
      assigned_staff_id: null,
      grand_total_minor: 45000,
      estimated_completion_time: null,
      created_at: "2026-07-26T10:00:00Z",
    },
    {
      id: "22222222-2222-2222-2222-222222222222",
      order_number: "ORD-BBBB2222",
      customer_id: "cust-1",
      source: "zomato",
      order_type: "delivery",
      status: "completed",
      payment_status: "paid",
      assigned_staff_id: null,
      grand_total_minor: 60800,
      estimated_completion_time: null,
      created_at: "2026-07-26T09:00:00Z",
    },
  ],
  pagination: { page: 1, page_size: 25, total: 2 },
  meta: { request_id: "test" },
};

function mockCurrentUser(permissions: string[]) {
  vi.spyOn(useCurrentUserModule, "useCurrentUser").mockReturnValue({
    data: { permissions } as CurrentUser,
    isLoading: false,
  } as ReturnType<typeof useCurrentUserModule.useCurrentUser>);
}

function mockOrderList(list: PaginatedResponse<OrderListItem>) {
  vi.spyOn(useOrdersModule, "useOrderList").mockReturnValue({
    data: list,
    isLoading: false,
    isError: false,
    refetch: vi.fn(),
  } as unknown as ReturnType<typeof useOrdersModule.useOrderList>);
}

describe("OrderDirectory", () => {
  it("renders a real (non-empty) order list without throwing", () => {
    mockCurrentUser(["orders.view", "orders.create"]);
    mockOrderList(TWO_ORDERS);
    renderWithQueryClient(<OrderDirectory />);
    expect(screen.getByText("ORD-AAAA1111")).toBeInTheDocument();
    expect(screen.getByText("ORD-BBBB2222")).toBeInTheDocument();
  });

  it("shows the create button for a user with orders.create", () => {
    mockCurrentUser(["orders.view", "orders.create"]);
    mockOrderList(EMPTY_LIST);
    renderWithQueryClient(<OrderDirectory />);
    expect(screen.getByRole("button", { name: /new order/i })).toBeInTheDocument();
  });

  it("hides the create button for a user without orders.create", () => {
    mockCurrentUser(["orders.view"]);
    mockOrderList(EMPTY_LIST);
    renderWithQueryClient(<OrderDirectory />);
    expect(screen.queryByRole("button", { name: /new order/i })).not.toBeInTheDocument();
  });

  it("shows the empty state when there are no orders", () => {
    mockCurrentUser(["orders.view"]);
    mockOrderList(EMPTY_LIST);
    renderWithQueryClient(<OrderDirectory />);
    expect(screen.getByText(/no orders match these filters/i)).toBeInTheDocument();
  });
});
