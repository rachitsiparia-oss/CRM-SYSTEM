import { describe, expect, it, vi, beforeEach } from "vitest";
import { render, screen } from "@testing-library/react";
import type { CurrentUser, PaginatedResponse, CustomerListItem } from "@rkpr/contracts";

import { CustomerDirectory } from "./customer-directory";
import * as useCurrentUserModule from "@/lib/hooks/use-current-user";
import * as useCustomersModule from "@/lib/hooks/use-customers";

vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: vi.fn() }),
  usePathname: () => "/customers",
}));

const EMPTY_LIST: PaginatedResponse<CustomerListItem> = {
  data: [],
  pagination: { page: 1, page_size: 25, total: 0 },
  meta: { request_id: "test" },
};

function mockCurrentUser(permissions: string[]) {
  vi.spyOn(useCurrentUserModule, "useCurrentUser").mockReturnValue({
    data: { permissions } as CurrentUser,
    isLoading: false,
  } as ReturnType<typeof useCurrentUserModule.useCurrentUser>);
}

function mockCustomerHooks() {
  vi.spyOn(useCustomersModule, "useCustomerList").mockReturnValue({
    data: EMPTY_LIST,
    isLoading: false,
    isError: false,
    refetch: vi.fn(),
  } as unknown as ReturnType<typeof useCustomersModule.useCustomerList>);
  vi.spyOn(useCustomersModule, "useCreateCustomer").mockReturnValue({
    mutateAsync: vi.fn(),
    isPending: false,
  } as unknown as ReturnType<typeof useCustomersModule.useCreateCustomer>);
  vi.spyOn(useCustomersModule, "useCustomerDuplicates").mockReturnValue({
    data: undefined,
  } as unknown as ReturnType<typeof useCustomersModule.useCustomerDuplicates>);
}

describe("CustomerDirectory", () => {
  beforeEach(() => {
    mockCustomerHooks();
  });

  it("shows the create button for a user with customers.create", () => {
    mockCurrentUser(["customers.view", "customers.create"]);
    render(<CustomerDirectory />);
    expect(screen.getByRole("button", { name: /new customer/i })).toBeInTheDocument();
  });

  it("hides the create button for a user without customers.create", () => {
    // Frontend hiding is usability only — the backend independently
    // rejects POST /customers without the permission
    // (ARCHITECTURE_AND_TECH_STACK.md section 6.9). This test covers the
    // usability half.
    mockCurrentUser(["customers.view"]);
    render(<CustomerDirectory />);
    expect(screen.queryByRole("button", { name: /new customer/i })).not.toBeInTheDocument();
  });

  it("shows the empty state when there are no customers", () => {
    mockCurrentUser(["customers.view"]);
    render(<CustomerDirectory />);
    expect(screen.getByText(/no customers match these filters/i)).toBeInTheDocument();
  });
});
