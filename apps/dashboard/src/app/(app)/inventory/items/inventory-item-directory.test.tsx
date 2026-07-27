import type { ReactElement } from "react";
import { describe, expect, it, vi, beforeEach } from "vitest";
import { render, screen } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import type { CurrentUser, InventoryItemListItem, PaginatedResponse } from "@rkpr/contracts";

import { InventoryItemDirectory } from "./inventory-item-directory";
import * as useCurrentUserModule from "@/lib/hooks/use-current-user";
import * as useInventoryReferenceModule from "@/lib/hooks/use-inventory-reference";
import * as useInventoryItemsModule from "@/lib/hooks/use-inventory-items";

vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: vi.fn() }),
  usePathname: () => "/inventory/items",
  useSearchParams: () => new URLSearchParams(),
}));

// InventoryItemDirectory always mounts InventoryItemCreateModal, whose form
// calls useCreateInventoryItem() (and reference-data hooks) unconditionally
// at render time — every TanStack useMutation() needs a QueryClient in
// context to exist at all, whether or not it's ever triggered.
function renderWithQueryClient(ui: ReactElement) {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(<QueryClientProvider client={queryClient}>{ui}</QueryClientProvider>);
}

const EMPTY_LIST: PaginatedResponse<InventoryItemListItem> = {
  data: [],
  pagination: { page: 1, page_size: 25, total: 0 },
  meta: { request_id: "test" },
};

const TWO_ITEMS: PaginatedResponse<InventoryItemListItem> = {
  data: [
    {
      id: "11111111-1111-1111-1111-111111111111",
      item_code: "ITM-AAAA1111",
      name: "Burger Buns",
      category_id: "cat-1",
      current_stock: "420.000",
      reserved_stock: "0.000",
      reorder_level: "120.000",
      stock_status: "in_stock",
      preferred_supplier_id: null,
      is_active: true,
      is_perishable: true,
      requires_batch_tracking: false,
      requires_expiry_tracking: false,
    },
    {
      id: "22222222-2222-2222-2222-222222222222",
      item_code: "ITM-BBBB2222",
      name: "Black Beans",
      category_id: "cat-2",
      current_stock: "0.000",
      reserved_stock: "0.000",
      reorder_level: "5.000",
      stock_status: "out_of_stock",
      preferred_supplier_id: null,
      is_active: true,
      is_perishable: false,
      requires_batch_tracking: false,
      requires_expiry_tracking: false,
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

function mockReferenceData() {
  vi.spyOn(useInventoryReferenceModule, "useInventoryCategories").mockReturnValue({
    data: [],
    isLoading: false,
  } as unknown as ReturnType<typeof useInventoryReferenceModule.useInventoryCategories>);
  vi.spyOn(useInventoryReferenceModule, "useInventoryLocations").mockReturnValue({
    data: [],
    isLoading: false,
  } as unknown as ReturnType<typeof useInventoryReferenceModule.useInventoryLocations>);
}

function mockItemList(list: PaginatedResponse<InventoryItemListItem>) {
  vi.spyOn(useInventoryItemsModule, "useInventoryItemList").mockReturnValue({
    data: list,
    isLoading: false,
    isError: false,
    refetch: vi.fn(),
  } as unknown as ReturnType<typeof useInventoryItemsModule.useInventoryItemList>);
}

describe("InventoryItemDirectory", () => {
  beforeEach(() => {
    mockReferenceData();
  });

  it("renders a real (non-empty) item list without throwing", () => {
    mockCurrentUser(["inventory.view", "inventory.items.create"]);
    mockItemList(TWO_ITEMS);
    renderWithQueryClient(<InventoryItemDirectory />);
    expect(screen.getByText("Burger Buns")).toBeInTheDocument();
    expect(screen.getByText("Black Beans")).toBeInTheDocument();
  });

  it("shows the create button for a user with inventory.items.create", () => {
    mockCurrentUser(["inventory.view", "inventory.items.create"]);
    mockItemList(EMPTY_LIST);
    renderWithQueryClient(<InventoryItemDirectory />);
    expect(screen.getByRole("button", { name: /new item/i })).toBeInTheDocument();
  });

  it("hides the create button for a user without inventory.items.create", () => {
    mockCurrentUser(["inventory.view"]);
    mockItemList(EMPTY_LIST);
    renderWithQueryClient(<InventoryItemDirectory />);
    expect(screen.queryByRole("button", { name: /new item/i })).not.toBeInTheDocument();
  });

  it("shows the empty state when there are no items", () => {
    mockCurrentUser(["inventory.view"]);
    mockItemList(EMPTY_LIST);
    renderWithQueryClient(<InventoryItemDirectory />);
    expect(screen.getByText(/no items match these filters/i)).toBeInTheDocument();
  });

  it("shows the out-of-stock status badge for an item with zero stock", () => {
    mockCurrentUser(["inventory.view"]);
    mockItemList(TWO_ITEMS);
    renderWithQueryClient(<InventoryItemDirectory />);
    expect(screen.getByText(/out of stock/i)).toBeInTheDocument();
  });
});
