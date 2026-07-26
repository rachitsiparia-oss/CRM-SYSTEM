import { describe, expect, it } from "vitest";
import { formatMinorUnits, humanize, isOverdue } from "./crm-display";

describe("formatMinorUnits", () => {
  it("formats integer minor units as rupees — the backend's authoritative units", () => {
    expect(formatMinorUnits(150000)).toBe("₹1,500.00");
  });

  it("renders a dash for null or undefined rather than ₹0.00", () => {
    // Distinguishing "no value recorded" from "zero rupees" matters for an
    // unset estimated_value_minor on a lead — CLAUDE.md section 7.
    expect(formatMinorUnits(null)).toBe("—");
    expect(formatMinorUnits(undefined)).toBe("—");
  });

  it("formats zero as an actual amount, not a dash", () => {
    expect(formatMinorUnits(0)).toBe("₹0.00");
  });
});

describe("humanize", () => {
  it("converts a snake_case enum value into title case", () => {
    expect(humanize("follow_up_scheduled")).toBe("Follow up scheduled");
  });

  it("returns a dash for empty input", () => {
    expect(humanize(null)).toBe("—");
    expect(humanize(undefined)).toBe("—");
    expect(humanize("")).toBe("—");
  });
});

describe("isOverdue", () => {
  it("flags a past timestamp as overdue", () => {
    expect(isOverdue(new Date(Date.now() - 60_000).toISOString())).toBe(true);
  });

  it("does not flag a future timestamp", () => {
    expect(isOverdue(new Date(Date.now() + 60_000).toISOString())).toBe(false);
  });

  it("treats a missing timestamp as not overdue", () => {
    expect(isOverdue(null)).toBe(false);
    expect(isOverdue(undefined)).toBe(false);
  });
});
