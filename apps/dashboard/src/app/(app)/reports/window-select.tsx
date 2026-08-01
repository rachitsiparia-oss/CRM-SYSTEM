"use client";

import type { ReportWindowCode } from "@rkpr/contracts";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";

export const WINDOW_OPTIONS: { value: ReportWindowCode; label: string }[] = [
  { value: "today", label: "Today" },
  { value: "yesterday", label: "Yesterday" },
  { value: "current_week", label: "This week" },
  { value: "previous_week", label: "Last week" },
  { value: "current_month", label: "This month" },
  { value: "previous_month", label: "Last month" },
  { value: "current_quarter", label: "This quarter" },
  { value: "previous_quarter", label: "Last quarter" },
  { value: "custom", label: "Custom range" },
];

export interface CustomRange {
  start: string;
  end: string;
}

export interface WindowSelectProps {
  value: string;
  onChange: (value: ReportWindowCode) => void;
  customRange: CustomRange;
  onCustomRangeChange: (range: CustomRange) => void;
}

/** Shared window-code picker for every Phase 14 dashboard/report/forecast
 * surface — keeps the nine window codes (analytics_core/windows.py) and
 * the custom-range date inputs in one place. */
export function WindowSelect({
  value,
  onChange,
  customRange,
  onCustomRangeChange,
}: WindowSelectProps) {
  return (
    <div className="flex flex-wrap items-end gap-2">
      <div className="flex flex-col gap-1.5">
        <Label className="text-muted-foreground text-xs">Window</Label>
        <Select value={value} onValueChange={(v) => onChange(v as ReportWindowCode)}>
          <SelectTrigger className="w-44">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            {WINDOW_OPTIONS.map((option) => (
              <SelectItem key={option.value} value={option.value}>
                {option.label}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>
      {value === "custom" && (
        <>
          <div className="flex flex-col gap-1.5">
            <Label className="text-muted-foreground text-xs">From</Label>
            <Input
              type="date"
              value={customRange.start}
              onChange={(e) => onCustomRangeChange({ ...customRange, start: e.target.value })}
              className="w-40"
            />
          </div>
          <div className="flex flex-col gap-1.5">
            <Label className="text-muted-foreground text-xs">To</Label>
            <Input
              type="date"
              value={customRange.end}
              onChange={(e) => onCustomRangeChange({ ...customRange, end: e.target.value })}
              className="w-40"
            />
          </div>
        </>
      )}
    </div>
  );
}
