import { describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import type { OrderTimelineEntry } from "@rkpr/contracts";

import { OrderTimelineTab } from "./order-timeline-tab";
import * as useOrdersModule from "@/lib/hooks/use-orders";

const ENTRIES: OrderTimelineEntry[] = [
  {
    id: "t-1",
    order_id: "order-1",
    event_type: "created",
    summary: "Order ORD-TEST0001 created via manual.",
    event_metadata: null,
    performed_by: "staff-1",
    occurred_at: "2026-07-26T10:00:00Z",
  },
  {
    id: "t-2",
    order_id: "order-1",
    event_type: "status_changed",
    summary: "Status changed from draft to pending_confirmation.",
    event_metadata: null,
    performed_by: "staff-1",
    occurred_at: "2026-07-26T10:05:00Z",
  },
];

function mockTimeline(data: OrderTimelineEntry[] | undefined, isLoading = false) {
  vi.spyOn(useOrdersModule, "useOrderTimeline").mockReturnValue({
    data,
    isLoading,
  } as unknown as ReturnType<typeof useOrdersModule.useOrderTimeline>);
}

describe("OrderTimelineTab", () => {
  it("renders every timeline event in order with its summary", () => {
    mockTimeline(ENTRIES);
    render(<OrderTimelineTab orderId="order-1" />);
    expect(screen.getByText(/order ord-test0001 created via manual/i)).toBeInTheDocument();
    expect(screen.getByText(/status changed from draft to pending_confirmation/i)).toBeInTheDocument();
  });

  it("shows an empty state when there is no activity yet", () => {
    mockTimeline([]);
    render(<OrderTimelineTab orderId="order-1" />);
    expect(screen.getByText(/no activity yet/i)).toBeInTheDocument();
  });
});
