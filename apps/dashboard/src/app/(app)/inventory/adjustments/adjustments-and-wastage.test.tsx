import type { ReactElement } from "react";
import { describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import type { CurrentUser, PaginatedResponse, InventoryItemListItem } from "@rkpr/contracts";

import { AdjustmentsAndWastage } from "./adjustments-and-wastage";
import * as useCurrentUserModule from "@/lib/hooks/use-current-user";
import * as useInventoryReferenceModule from "@/lib/hooks/use-inventory-reference";
import * as useInventoryItemsModule from "@/lib/hooks/use-inventory-items";
import * as useInventoryOperationsModule from "@/lib/hooks/use-inventory-operations";

function renderWithQueryClient(ui: ReactElement) {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(<QueryClientProvider client={queryClient}>{ui}</QueryClientProvider>);
}

const EMPTY_ITEMS: PaginatedResponse<InventoryItemListItem> = {
  data: [],
  pagination: { page: 1, page_size: 100, total: 0 },
  meta: { request_id: "test" },
};

function mockCurrentUser(permissions: string[]) {
  vi.spyOn(useCurrentUserModule, "useCurrentUser").mockReturnValue({
    data: { permissions } as CurrentUser,
    isLoading: false,
  } as ReturnType<typeof useCurrentUserModule.useCurrentUser>);
}

function mockHooks() {
  vi.spyOn(useInventoryItemsModule, "useInventoryItemList").mockReturnValue({
    data: EMPTY_ITEMS,
    isLoading: false,
  } as unknown as ReturnType<typeof useInventoryItemsModule.useInventoryItemList>);
  vi.spyOn(useInventoryReferenceModule, "useInventoryLocations").mockReturnValue({
    data: [],
    isLoading: false,
  } as unknown as ReturnType<typeof useInventoryReferenceModule.useInventoryLocations>);
  vi.spyOn(useInventoryOperationsModule, "useInventoryAdjustments").mockReturnValue({
    data: { data: [], pagination: { page: 1, page_size: 25, total: 0 }, meta: { request_id: "t" } },
  } as unknown as ReturnType<typeof useInventoryOperationsModule.useInventoryAdjustments>);
  vi.spyOn(useInventoryOperationsModule, "useInventoryWastage").mockReturnValue({
    data: { data: [], pagination: { page: 1, page_size: 25, total: 0 }, meta: { request_id: "t" } },
  } as unknown as ReturnType<typeof useInventoryOperationsModule.useInventoryWastage>);
}

describe("AdjustmentsAndWastage", () => {
  it("shows the adjustment form for a user with inventory.adjustments.create", () => {
    mockCurrentUser(["inventory.view", "inventory.adjustments.create"]);
    mockHooks();
    renderWithQueryClient(<AdjustmentsAndWastage />);
    expect(screen.getByText(/record a manual adjustment/i)).toBeInTheDocument();
  });

  it("hides the adjustment form for a user without inventory.adjustments.create", () => {
    mockCurrentUser(["inventory.view"]);
    mockHooks();
    renderWithQueryClient(<AdjustmentsAndWastage />);
    expect(screen.queryByText(/record a manual adjustment/i)).not.toBeInTheDocument();
  });

  it("shows the empty state when there are no adjustments recorded", () => {
    mockCurrentUser(["inventory.view"]);
    mockHooks();
    renderWithQueryClient(<AdjustmentsAndWastage />);
    expect(screen.getByText(/no adjustments yet/i)).toBeInTheDocument();
  });
});
