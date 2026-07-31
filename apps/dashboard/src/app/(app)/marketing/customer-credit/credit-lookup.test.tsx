import type { ReactElement } from "react";
import { describe, expect, it, vi } from "vitest";
import { fireEvent, render, screen } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import type {
  CurrentUser,
  CustomerCreditAccount,
  CustomerCreditLedgerEntry,
  PaginatedResponse,
} from "@rkpr/contracts";

import { CreditLookup } from "./credit-lookup";
import * as useCurrentUserModule from "@/lib/hooks/use-current-user";
import * as useCustomerCreditModule from "@/lib/hooks/use-customer-credit";

vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: vi.fn() }),
  usePathname: () => "/marketing/customer-credit",
  useSearchParams: () => new URLSearchParams(),
}));

function renderWithQueryClient(ui: ReactElement) {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(<QueryClientProvider client={queryClient}>{ui}</QueryClientProvider>);
}

const ACCOUNT: CustomerCreditAccount = {
  id: "account-1",
  customer_id: "customer-1",
  status: "active",
  current_balance_minor: 50000,
  created_at: "2026-07-30T10:00:00Z",
  updated_at: "2026-07-30T10:00:00Z",
};

const EMPTY_LEDGER: PaginatedResponse<CustomerCreditLedgerEntry> = {
  data: [],
  pagination: { page: 1, page_size: 20, total: 0 },
  meta: { request_id: "test" },
};

function mockCurrentUser(permissions: string[]) {
  vi.spyOn(useCurrentUserModule, "useCurrentUser").mockReturnValue({
    data: { permissions } as CurrentUser,
    isLoading: false,
  } as ReturnType<typeof useCurrentUserModule.useCurrentUser>);
}

function mockAccount(account: CustomerCreditAccount | null) {
  vi.spyOn(useCustomerCreditModule, "useCustomerCreditAccount").mockReturnValue({
    data: account,
    isLoading: false,
    isError: false,
    refetch: vi.fn(),
  } as unknown as ReturnType<typeof useCustomerCreditModule.useCustomerCreditAccount>);
}

function mockLedger() {
  vi.spyOn(useCustomerCreditModule, "useCustomerCreditLedger").mockReturnValue({
    data: EMPTY_LEDGER,
    isLoading: false,
    isError: false,
    refetch: vi.fn(),
  } as unknown as ReturnType<typeof useCustomerCreditModule.useCustomerCreditLedger>);
}

function mockAnalytics() {
  vi.spyOn(useCustomerCreditModule, "useCustomerCreditAnalytics").mockReturnValue({
    data: undefined,
    isLoading: false,
  } as unknown as ReturnType<typeof useCustomerCreditModule.useCustomerCreditAnalytics>);
}

function lookUp() {
  fireEvent.change(screen.getByLabelText(/customer id/i), { target: { value: "customer-1" } });
  fireEvent.click(screen.getByRole("button", { name: /look up/i }));
}

describe("CreditLookup", () => {
  it("renders a real (found) credit account without throwing", () => {
    mockCurrentUser(["customer_credit.view"]);
    mockAnalytics();
    mockAccount(ACCOUNT);
    mockLedger();
    renderWithQueryClient(<CreditLookup />);
    lookUp();
    expect(screen.getByText("₹500.00")).toBeInTheDocument();
  });

  it("shows the issue-credit button for a user with customer_credit.issue", () => {
    mockCurrentUser(["customer_credit.view", "customer_credit.issue"]);
    mockAnalytics();
    mockAccount(ACCOUNT);
    mockLedger();
    renderWithQueryClient(<CreditLookup />);
    lookUp();
    expect(screen.getByRole("button", { name: /issue credit/i })).toBeInTheDocument();
  });

  it("hides the issue-credit button for a user without customer_credit.issue", () => {
    mockCurrentUser(["customer_credit.view"]);
    mockAnalytics();
    mockAccount(ACCOUNT);
    mockLedger();
    renderWithQueryClient(<CreditLookup />);
    lookUp();
    expect(screen.queryByRole("button", { name: /issue credit/i })).not.toBeInTheDocument();
  });
});
