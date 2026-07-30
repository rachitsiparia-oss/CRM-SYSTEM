import type { ReactElement } from "react";
import { describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import type { CurrentUser, KnowledgeArticle, PaginatedResponse } from "@rkpr/contracts";

import { ArticleLibrary } from "./article-library";
import * as useCurrentUserModule from "@/lib/hooks/use-current-user";
import * as useKnowledgeModule from "@/lib/hooks/use-knowledge";

vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: vi.fn() }),
  usePathname: () => "/knowledge-base/articles",
  useSearchParams: () => new URLSearchParams(),
}));

function renderWithQueryClient(ui: ReactElement) {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(<QueryClientProvider client={queryClient}>{ui}</QueryClientProvider>);
}

function makeArticle(overrides: Partial<KnowledgeArticle>): KnowledgeArticle {
  return {
    id: "11111111-1111-1111-1111-111111111111",
    article_number: "KB-AAAA1111",
    title: "Fire safety checklist",
    summary: null,
    content: "Content",
    article_type: "checklist",
    category_id: null,
    owner_staff_id: null,
    department_id: null,
    visibility_scope: "all_staff",
    status: "published",
    latest_version_number: 1,
    published_version_id: "version-1",
    effective_at: null,
    review_at: null,
    expiry_at: null,
    estimated_reading_minutes: null,
    requires_acknowledgement: false,
    requires_training: false,
    version: 1,
    created_at: "2026-07-30T10:00:00Z",
    updated_at: "2026-07-30T10:00:00Z",
    ...overrides,
  } as KnowledgeArticle;
}

const EMPTY_LIST: PaginatedResponse<KnowledgeArticle> = {
  data: [],
  pagination: { page: 1, page_size: 25, total: 0 },
  meta: { request_id: "test" },
};

const TWO_ARTICLES: PaginatedResponse<KnowledgeArticle> = {
  data: [
    makeArticle({ id: "1", title: "Fire safety checklist" }),
    makeArticle({ id: "2", article_number: "KB-BBBB2222", title: "Opening shift SOP", status: "draft" }),
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

function mockArticleList(list: PaginatedResponse<KnowledgeArticle>) {
  vi.spyOn(useKnowledgeModule, "useArticleList").mockReturnValue({
    data: list,
    isLoading: false,
    isError: false,
    refetch: vi.fn(),
  } as unknown as ReturnType<typeof useKnowledgeModule.useArticleList>);
}

describe("ArticleLibrary", () => {
  it("renders a real (non-empty) article list without throwing", () => {
    mockCurrentUser(["knowledge.view"]);
    mockArticleList(TWO_ARTICLES);
    renderWithQueryClient(<ArticleLibrary />);
    expect(screen.getByText("Fire safety checklist")).toBeInTheDocument();
    expect(screen.getByText("Opening shift SOP")).toBeInTheDocument();
  });

  it("shows the create button for a user with knowledge.create", () => {
    mockCurrentUser(["knowledge.view", "knowledge.create"]);
    mockArticleList(EMPTY_LIST);
    renderWithQueryClient(<ArticleLibrary />);
    expect(screen.getByRole("button", { name: /new article/i })).toBeInTheDocument();
  });

  it("hides the create button for a user without knowledge.create", () => {
    mockCurrentUser(["knowledge.view"]);
    mockArticleList(EMPTY_LIST);
    renderWithQueryClient(<ArticleLibrary />);
    expect(screen.queryByRole("button", { name: /new article/i })).not.toBeInTheDocument();
  });

  it("shows the empty state when there are no articles", () => {
    mockCurrentUser(["knowledge.view"]);
    mockArticleList(EMPTY_LIST);
    renderWithQueryClient(<ArticleLibrary />);
    expect(screen.getByText(/create the first knowledge article/i)).toBeInTheDocument();
  });
});
