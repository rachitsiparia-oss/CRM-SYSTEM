import type { ReactElement } from "react";
import { describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import type { CurrentUser, MenuCategory } from "@rkpr/contracts";

import { CategoryDirectory } from "./category-directory";
import * as useCurrentUserModule from "@/lib/hooks/use-current-user";
import * as useCategoriesModule from "@/lib/hooks/use-menu-categories";

// Each rendered category row mounts useUpdateCategory/useArchiveCategory/
// useRestoreCategory, and the create modal mounts useCreateCategory — every
// TanStack useMutation() call needs a QueryClient in context to exist at
// all, whether or not it's ever triggered. Real hooks run against this
// provider instead of being individually mocked one by one.
function renderWithQueryClient(ui: ReactElement) {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(<QueryClientProvider client={queryClient}>{ui}</QueryClientProvider>);
}

const TWO_CATEGORIES: MenuCategory[] = [
  {
    id: "cat-1",
    code: "burgers",
    name: "Burgers",
    description: null,
    sort_order: 0,
    is_active: true,
    version: 1,
  },
  {
    id: "cat-2",
    code: "pizzas",
    name: "Pizzas",
    description: "Hand-tossed.",
    sort_order: 1,
    is_active: true,
    version: 1,
  },
];

function mockCurrentUser(permissions: string[]) {
  vi.spyOn(useCurrentUserModule, "useCurrentUser").mockReturnValue({
    data: { permissions } as CurrentUser,
    isLoading: false,
  } as ReturnType<typeof useCurrentUserModule.useCurrentUser>);
}

function mockCategoryHooks(categories: MenuCategory[]) {
  vi.spyOn(useCategoriesModule, "useCategoryList").mockReturnValue({
    data: {
      data: categories,
      pagination: { page: 1, page_size: 100, total: categories.length },
      meta: { request_id: "test" },
    },
    isLoading: false,
    isError: false,
    refetch: vi.fn(),
  } as unknown as ReturnType<typeof useCategoriesModule.useCategoryList>);
}

describe("CategoryDirectory", () => {
  it("renders a real (non-empty) category list without throwing", () => {
    mockCurrentUser(["menu.view", "menu.categories.manage"]);
    mockCategoryHooks(TWO_CATEGORIES);
    renderWithQueryClient(<CategoryDirectory />);
    expect(screen.getByText("Burgers")).toBeInTheDocument();
    expect(screen.getByText("Pizzas")).toBeInTheDocument();
  });

  it("shows the create button for a user with menu.categories.manage", () => {
    mockCurrentUser(["menu.view", "menu.categories.manage"]);
    mockCategoryHooks([]);
    renderWithQueryClient(<CategoryDirectory />);
    expect(screen.getByRole("button", { name: /new category/i })).toBeInTheDocument();
  });

  it("hides management controls for a user without menu.categories.manage", () => {
    mockCurrentUser(["menu.view"]);
    mockCategoryHooks(TWO_CATEGORIES);
    renderWithQueryClient(<CategoryDirectory />);
    expect(screen.queryByRole("button", { name: /new category/i })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /archive/i })).not.toBeInTheDocument();
  });

  it("shows the empty state when there are no categories", () => {
    mockCurrentUser(["menu.view"]);
    mockCategoryHooks([]);
    renderWithQueryClient(<CategoryDirectory />);
    expect(screen.getByText(/no categories found/i)).toBeInTheDocument();
  });
});
