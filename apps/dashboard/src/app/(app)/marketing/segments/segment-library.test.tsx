import type { ReactElement } from "react";
import { describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import type { CurrentUser, PaginatedResponse, Segment } from "@rkpr/contracts";

import { SegmentLibrary } from "./segment-library";
import * as useCurrentUserModule from "@/lib/hooks/use-current-user";
import * as useSegmentsModule from "@/lib/hooks/use-segments";

vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: vi.fn() }),
  usePathname: () => "/marketing/segments",
  useSearchParams: () => new URLSearchParams(),
}));

function renderWithQueryClient(ui: ReactElement) {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(<QueryClientProvider client={queryClient}>{ui}</QueryClientProvider>);
}

function makeSegment(overrides: Partial<Segment>): Segment {
  return {
    id: "11111111-1111-1111-1111-111111111111",
    code: "HIGH_VALUE",
    name: "High value customers",
    description: null,
    segment_type: "dynamic",
    status: "active",
    rule_definition: null,
    rule_version: 1,
    refresh_strategy: null,
    estimated_count: 100,
    last_computed_count: 100,
    last_refreshed_at: "2026-07-30T10:00:00Z",
    owner_staff_id: null,
    is_seed_builtin: false,
    created_at: "2026-07-30T10:00:00Z",
    updated_at: "2026-07-30T10:00:00Z",
    ...overrides,
  };
}

const EMPTY_LIST: PaginatedResponse<Segment> = {
  data: [],
  pagination: { page: 1, page_size: 25, total: 0 },
  meta: { request_id: "test" },
};

const TWO_SEGMENTS: PaginatedResponse<Segment> = {
  data: [
    makeSegment({ id: "1", name: "High value customers" }),
    makeSegment({ id: "2", code: "LAPSED", name: "Lapsed customers", segment_type: "static" }),
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

function mockSegmentList(list: PaginatedResponse<Segment>) {
  vi.spyOn(useSegmentsModule, "useSegmentList").mockReturnValue({
    data: list,
    isLoading: false,
    isError: false,
    refetch: vi.fn(),
  } as unknown as ReturnType<typeof useSegmentsModule.useSegmentList>);
}

describe("SegmentLibrary", () => {
  it("renders a real (non-empty) segment list without throwing", () => {
    mockCurrentUser(["segments.view"]);
    mockSegmentList(TWO_SEGMENTS);
    renderWithQueryClient(<SegmentLibrary />);
    expect(screen.getByText("High value customers")).toBeInTheDocument();
    expect(screen.getByText("Lapsed customers")).toBeInTheDocument();
  });

  it("shows the create button for a user with segments.manage", () => {
    mockCurrentUser(["segments.view", "segments.manage"]);
    mockSegmentList(EMPTY_LIST);
    renderWithQueryClient(<SegmentLibrary />);
    expect(screen.getByRole("button", { name: /new segment/i })).toBeInTheDocument();
  });

  it("hides the create button for a user without segments.manage", () => {
    mockCurrentUser(["segments.view"]);
    mockSegmentList(EMPTY_LIST);
    renderWithQueryClient(<SegmentLibrary />);
    expect(screen.queryByRole("button", { name: /new segment/i })).not.toBeInTheDocument();
  });
});
