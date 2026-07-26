import { describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import type { CurrentUser, LeadListItem, PaginatedResponse } from "@rkpr/contracts";

import { LeadPipeline } from "./lead-pipeline";
import * as useCurrentUserModule from "@/lib/hooks/use-current-user";
import * as useLeadsModule from "@/lib/hooks/use-leads";

vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: vi.fn() }),
  usePathname: () => "/leads",
}));

// The exact payload captured from the live production API for GET
// /api/v1/leads as the owner — reproducing a real "Something went wrong"
// crash reported against the deployed dashboard.
const REAL_LEADS_RESPONSE: PaginatedResponse<LeadListItem> = {
  data: [
    {
      id: "c75c8db5-a8e9-4a67-b846-87b1fd3b85a2",
      lead_number: "LEAD-338A0E33",
      display_name: "BrightWave Technologies",
      organization_name: "BrightWave Technologies",
      lead_type: "corporate_catering",
      source: "website",
      status: "qualified",
      priority: "high",
      estimated_value_minor: 1800000,
      requested_date: null,
      party_size: 60,
      assigned_staff_id: null,
      next_follow_up_at: null,
      last_contact_at: null,
      created_at: "2026-07-26T02:43:44.011454Z",
    },
    {
      id: "8ac28478-173d-439b-a825-2052abeac2a2",
      lead_number: "LEAD-B0D2CCD4",
      display_name: "Zomato Walk-in Enquiry",
      organization_name: null,
      lead_type: "general_sales_enquiry",
      source: "zomato_import",
      status: "new",
      priority: "low",
      estimated_value_minor: null,
      requested_date: null,
      party_size: null,
      assigned_staff_id: null,
      next_follow_up_at: null,
      last_contact_at: null,
      created_at: "2026-07-26T02:43:44.011454Z",
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

describe("LeadPipeline against a real captured API response", () => {
  it("renders the real payload without throwing", () => {
    mockCurrentUser(["leads.view", "leads.create"]);
    vi.spyOn(useLeadsModule, "useLeadList").mockReturnValue({
      data: REAL_LEADS_RESPONSE,
      isLoading: false,
      isError: false,
      refetch: vi.fn(),
    } as unknown as ReturnType<typeof useLeadsModule.useLeadList>);
    vi.spyOn(useLeadsModule, "useLeadDuplicates").mockReturnValue({
      data: undefined,
    } as unknown as ReturnType<typeof useLeadsModule.useLeadDuplicates>);
    vi.spyOn(useLeadsModule, "useCreateLead").mockReturnValue({
      mutateAsync: vi.fn(),
      isPending: false,
    } as unknown as ReturnType<typeof useLeadsModule.useCreateLead>);

    render(<LeadPipeline />);

    expect(screen.getByText("BrightWave Technologies")).toBeInTheDocument();
    expect(screen.getByText("Zomato Walk-in Enquiry")).toBeInTheDocument();
  });
});
