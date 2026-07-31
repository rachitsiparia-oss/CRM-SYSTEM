import type { ReactElement } from "react";
import { describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import type { Achievement, CurrentUser, PaginatedResponse } from "@rkpr/contracts";

import { AchievementLibrary } from "./achievement-library";
import * as useCurrentUserModule from "@/lib/hooks/use-current-user";
import * as useAchievementsModule from "@/lib/hooks/use-achievements";

vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: vi.fn() }),
  usePathname: () => "/marketing/achievements",
  useSearchParams: () => new URLSearchParams(),
}));

function renderWithQueryClient(ui: ReactElement) {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(<QueryClientProvider client={queryClient}>{ui}</QueryClientProvider>);
}

function makeAchievement(overrides: Partial<Achievement>): Achievement {
  return {
    id: "11111111-1111-1111-1111-111111111111",
    code: "FIRST_ORDER",
    name: "First order",
    description: null,
    icon: null,
    condition_version: 1,
    condition: {
      kind: "condition",
      fact: "customer.completed_order_count",
      operator: "gte",
      value: 1,
    },
    is_active: true,
    is_hidden: false,
    reward_ledger: "loyalty_points",
    reward_amount: 50,
    is_repeatable: false,
    cooldown_days: null,
    created_at: "2026-07-30T10:00:00Z",
    updated_at: "2026-07-30T10:00:00Z",
    ...overrides,
  };
}

function mockCurrentUser(permissions: string[]) {
  vi.spyOn(useCurrentUserModule, "useCurrentUser").mockReturnValue({
    data: { permissions } as CurrentUser,
    isLoading: false,
  } as ReturnType<typeof useCurrentUserModule.useCurrentUser>);
}

function mockAchievementList(list: PaginatedResponse<Achievement>) {
  vi.spyOn(useAchievementsModule, "useAchievementList").mockReturnValue({
    data: list,
    isLoading: false,
    isError: false,
    refetch: vi.fn(),
  } as unknown as ReturnType<typeof useAchievementsModule.useAchievementList>);
}

const TWO_ACHIEVEMENTS: PaginatedResponse<Achievement> = {
  data: [
    makeAchievement({ id: "1", name: "First order" }),
    makeAchievement({ id: "2", name: "Big spender", code: "BIG_SPENDER" }),
  ],
  pagination: { page: 1, page_size: 25, total: 2 },
  meta: { request_id: "test" },
};

const EMPTY_LIST: PaginatedResponse<Achievement> = {
  data: [],
  pagination: { page: 1, page_size: 25, total: 0 },
  meta: { request_id: "test" },
};

describe("AchievementLibrary", () => {
  it("renders a real (non-empty) achievement list without throwing", () => {
    mockCurrentUser(["achievements.view"]);
    mockAchievementList(TWO_ACHIEVEMENTS);
    renderWithQueryClient(<AchievementLibrary />);
    expect(screen.getByText("First order")).toBeInTheDocument();
    expect(screen.getByText("Big spender")).toBeInTheDocument();
  });

  it("shows the create button for a user with achievements.manage", () => {
    mockCurrentUser(["achievements.view", "achievements.manage"]);
    mockAchievementList(EMPTY_LIST);
    renderWithQueryClient(<AchievementLibrary />);
    expect(screen.getByRole("button", { name: /new achievement/i })).toBeInTheDocument();
  });

  it("hides the create button for a user without achievements.manage", () => {
    mockCurrentUser(["achievements.view"]);
    mockAchievementList(EMPTY_LIST);
    renderWithQueryClient(<AchievementLibrary />);
    expect(screen.queryByRole("button", { name: /new achievement/i })).not.toBeInTheDocument();
  });
});
