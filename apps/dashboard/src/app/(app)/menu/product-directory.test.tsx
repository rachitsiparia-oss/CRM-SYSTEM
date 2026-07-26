import type { ReactElement } from "react";
import { describe, expect, it, vi, beforeEach } from "vitest";
import { render, screen } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import type { CurrentUser, PaginatedResponse, ProductListItem } from "@rkpr/contracts";

import { ProductDirectory } from "./product-directory";
import * as useCurrentUserModule from "@/lib/hooks/use-current-user";
import * as useCategoriesModule from "@/lib/hooks/use-menu-categories";
import * as useProductsModule from "@/lib/hooks/use-menu-products";

vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: vi.fn() }),
  usePathname: () => "/menu",
}));

// ProductDirectory always mounts ProductCreateModal, whose form calls
// useCreateProduct() (and other menu mutation hooks) unconditionally at
// render time — every TanStack `useMutation()` needs a QueryClient in
// context to exist at all, whether or not it's ever triggered. Real hooks
// run against this provider instead of being individually mocked one by
// one, since the number of mutation hooks mounted per row/modal here would
// make that brittle.
function renderWithQueryClient(ui: ReactElement) {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(<QueryClientProvider client={queryClient}>{ui}</QueryClientProvider>);
}

const EMPTY_LIST: PaginatedResponse<ProductListItem> = {
  data: [],
  pagination: { page: 1, page_size: 25, total: 0 },
  meta: { request_id: "test" },
};

// Two real rows, not zero — Phase 5's DataTable component had a latent bug
// (uncontrolled rowSelection state) that only threw once at least one row
// actually rendered; an empty-list-only test suite never caught it. This
// fixture exists specifically so the product table is exercised with real
// row rendering, the same way the Phase 5 regression test was written
// after that bug shipped.
const TWO_PRODUCTS: PaginatedResponse<ProductListItem> = {
  data: [
    {
      id: "11111111-1111-1111-1111-111111111111",
      product_code: "PROD-AAAA1111",
      name: "Margherita Pizza",
      display_name: null,
      category_id: "cat-1",
      food_type: "vegetarian",
      base_price_minor: 21900,
      is_active: true,
      is_available: true,
      is_featured: false,
      sort_order: 0,
      image_storage_path: null,
    },
    {
      id: "22222222-2222-2222-2222-222222222222",
      product_code: "PROD-BBBB2222",
      name: "BBQ Chicken Pizza",
      display_name: null,
      category_id: "cat-1",
      food_type: "non_vegetarian",
      base_price_minor: 34900,
      is_active: true,
      is_available: false,
      is_featured: true,
      sort_order: 1,
      image_storage_path: null,
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

function mockCategories() {
  vi.spyOn(useCategoriesModule, "useCategoryList").mockReturnValue({
    data: { data: [], pagination: { page: 1, page_size: 100, total: 0 }, meta: { request_id: "t" } },
    isLoading: false,
  } as unknown as ReturnType<typeof useCategoriesModule.useCategoryList>);
}

function mockProductHooks(list: PaginatedResponse<ProductListItem>) {
  vi.spyOn(useProductsModule, "useProductList").mockReturnValue({
    data: list,
    isLoading: false,
    isError: false,
    refetch: vi.fn(),
  } as unknown as ReturnType<typeof useProductsModule.useProductList>);
  vi.spyOn(useProductsModule, "useDuplicateProduct").mockReturnValue({
    mutate: vi.fn(),
    isPending: false,
  } as unknown as ReturnType<typeof useProductsModule.useDuplicateProduct>);
}

describe("ProductDirectory", () => {
  beforeEach(() => {
    mockCategories();
  });

  it("renders a real (non-empty) product list without throwing", () => {
    mockCurrentUser(["menu.view", "menu.create"]);
    mockProductHooks(TWO_PRODUCTS);
    renderWithQueryClient(<ProductDirectory />);
    expect(screen.getByText("Margherita Pizza")).toBeInTheDocument();
    expect(screen.getByText("BBQ Chicken Pizza")).toBeInTheDocument();
  });

  it("shows the create button for a user with menu.create", () => {
    mockCurrentUser(["menu.view", "menu.create"]);
    mockProductHooks(EMPTY_LIST);
    renderWithQueryClient(<ProductDirectory />);
    expect(screen.getByRole("button", { name: /new product/i })).toBeInTheDocument();
  });

  it("hides the create button for a user without menu.create", () => {
    mockCurrentUser(["menu.view"]);
    mockProductHooks(EMPTY_LIST);
    renderWithQueryClient(<ProductDirectory />);
    expect(screen.queryByRole("button", { name: /new product/i })).not.toBeInTheDocument();
  });

  it("shows the empty state when there are no products", () => {
    mockCurrentUser(["menu.view"]);
    mockProductHooks(EMPTY_LIST);
    renderWithQueryClient(<ProductDirectory />);
    expect(screen.getByText(/no products match these filters/i)).toBeInTheDocument();
  });
});
