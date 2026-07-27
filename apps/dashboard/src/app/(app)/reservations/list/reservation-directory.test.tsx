import type { ReactElement } from "react";
import { describe, expect, it, vi, beforeEach } from "vitest";
import { render, screen } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import type { CurrentUser, PaginatedResponse, Reservation } from "@rkpr/contracts";

import { ReservationDirectory } from "./reservation-directory";
import * as useCurrentUserModule from "@/lib/hooks/use-current-user";
import * as useReservationsModule from "@/lib/hooks/use-reservations";

vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: vi.fn() }),
  usePathname: () => "/reservations/list",
  useSearchParams: () => new URLSearchParams(),
}));

// ReservationDirectory always mounts ReservationCreateModal, whose form
// calls useCreateReservation() (and dining-area reference data)
// unconditionally at render time — every TanStack useMutation() needs a
// QueryClient in context to exist at all, whether or not it's ever
// triggered.
function renderWithQueryClient(ui: ReactElement) {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(<QueryClientProvider client={queryClient}>{ui}</QueryClientProvider>);
}

function makeReservation(overrides: Partial<Reservation>): Reservation {
  return {
    id: "11111111-1111-1111-1111-111111111111",
    reservation_number: "RES-AAAA1111",
    customer_id: null,
    guest_name: "Ananya Rao",
    phone_e164: "+919845012345",
    email: null,
    party_size: 4,
    reservation_date: "2026-08-10",
    start_time: "19:00:00",
    end_time: null,
    dining_area_id: null,
    status: "requested",
    source: "phone",
    is_walk_in: false,
    special_requests: null,
    order_id: null,
    assigned_staff_id: null,
    approved_by: null,
    approved_at: null,
    rejected_by: null,
    rejected_at: null,
    rejection_reason: null,
    arrived_at: null,
    seated_at: null,
    completed_at: null,
    no_show_at: null,
    cancelled_at: null,
    cancellation_source: null,
    cancellation_reason: null,
    expires_at: null,
    deposit_required: false,
    deposit_amount_minor: null,
    version: 1,
    created_at: "2026-07-27T10:00:00Z",
    updated_at: "2026-07-27T10:00:00Z",
    ...overrides,
  };
}

const EMPTY_LIST: PaginatedResponse<Reservation> = {
  data: [],
  pagination: { page: 1, page_size: 25, total: 0 },
  meta: { request_id: "test" },
};

const TWO_RESERVATIONS: PaginatedResponse<Reservation> = {
  data: [
    makeReservation({ id: "1", guest_name: "Ananya Rao", status: "requested" }),
    makeReservation({
      id: "2",
      reservation_number: "RES-BBBB2222",
      guest_name: "Rahul Mehta",
      status: "confirmed",
    }),
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

function mockDiningAreas() {
  vi.spyOn(useReservationsModule, "useDiningAreas").mockReturnValue({
    data: [],
    isLoading: false,
  } as unknown as ReturnType<typeof useReservationsModule.useDiningAreas>);
}

function mockReservationList(list: PaginatedResponse<Reservation>) {
  vi.spyOn(useReservationsModule, "useReservationList").mockReturnValue({
    data: list,
    isLoading: false,
    isError: false,
    refetch: vi.fn(),
  } as unknown as ReturnType<typeof useReservationsModule.useReservationList>);
}

describe("ReservationDirectory", () => {
  beforeEach(() => {
    mockDiningAreas();
  });

  it("renders a real (non-empty) reservation list without throwing", () => {
    mockCurrentUser(["reservations.view", "reservations.create"]);
    mockReservationList(TWO_RESERVATIONS);
    renderWithQueryClient(<ReservationDirectory />);
    expect(screen.getByText("Ananya Rao")).toBeInTheDocument();
    expect(screen.getByText("Rahul Mehta")).toBeInTheDocument();
  });

  it("shows the create button for a user with reservations.create", () => {
    mockCurrentUser(["reservations.view", "reservations.create"]);
    mockReservationList(EMPTY_LIST);
    renderWithQueryClient(<ReservationDirectory />);
    expect(screen.getByRole("button", { name: /new reservation/i })).toBeInTheDocument();
  });

  it("hides the create button for a user without reservations.create", () => {
    mockCurrentUser(["reservations.view"]);
    mockReservationList(EMPTY_LIST);
    renderWithQueryClient(<ReservationDirectory />);
    expect(screen.queryByRole("button", { name: /new reservation/i })).not.toBeInTheDocument();
  });

  it("shows the empty state when there are no reservations", () => {
    mockCurrentUser(["reservations.view"]);
    mockReservationList(EMPTY_LIST);
    renderWithQueryClient(<ReservationDirectory />);
    expect(screen.getByText(/no reservations match these filters/i)).toBeInTheDocument();
  });

  it("shows the status badge for a confirmed reservation", () => {
    mockCurrentUser(["reservations.view"]);
    mockReservationList(TWO_RESERVATIONS);
    renderWithQueryClient(<ReservationDirectory />);
    expect(screen.getByText(/confirmed/i)).toBeInTheDocument();
  });
});
