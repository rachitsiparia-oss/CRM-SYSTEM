import { describe, expect, it } from "vitest";
import type { LeadStatus } from "@rkpr/contracts";
import { ALLOWED_TRANSITIONS } from "./lead-status-control";

const ALL_STATUSES: LeadStatus[] = [
  "new",
  "contacted",
  "qualified",
  "interested",
  "follow_up_scheduled",
  "proposal_shared",
  "negotiating",
  "won",
  "lost",
  "closed",
];

describe("ALLOWED_TRANSITIONS (frontend mirror of app/leads/states.py)", () => {
  it("covers every lead status with no gaps", () => {
    expect(Object.keys(ALLOWED_TRANSITIONS).sort()).toEqual([...ALL_STATUSES].sort());
  });

  it("never offers 'won' as a transition target from any status", () => {
    // `won` is only reachable through the conversion service
    // (app/leads/states.py::is_transition_allowed always returns False for
    // it) — a UI regression here would let staff try a direct transition
    // the backend then rejects with a confusing 400.
    for (const targets of Object.values(ALLOWED_TRANSITIONS)) {
      expect(targets).not.toContain("won");
    }
  });

  it("has no terminal transitions out of 'closed'", () => {
    expect(ALLOWED_TRANSITIONS.closed).toEqual([]);
  });

  it("allows reopening a lost lead only back to 'new', not skipping qualification", () => {
    expect(ALLOWED_TRANSITIONS.lost).toEqual(["new", "closed"]);
  });
});
