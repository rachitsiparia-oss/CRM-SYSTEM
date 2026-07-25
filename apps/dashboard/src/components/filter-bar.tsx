"use client";

import type { ReactNode } from "react";
import { RotateCcw } from "lucide-react";

import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import { SearchInput } from "@/components/forms/search-input";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";

export interface FilterPreset {
  label: string;
  value: string;
}

export interface FilterBarProps {
  search: string;
  onSearchChange: (value: string) => void;
  searchPlaceholder?: string;
  /** Additional filter controls (Select, MultiSelect, DatePicker, …) —
   * business-specific filter fields belong to the calling module, not
   * here. */
  filters?: ReactNode;
  hasActiveFilters?: boolean;
  onReset?: () => void;
  /** Explicit apply button — omit for tables that filter as you type. */
  onApply?: () => void;
  presets?: FilterPreset[];
  activePreset?: string;
  onPresetSelect?: (value: string) => void;
  className?: string;
}

/** The generic filter bar every table/list page composes: search, an
 * arbitrary set of caller-supplied filter controls, optional named
 * presets ("saved filter state"), and reset/apply actions. */
export function FilterBar({
  search,
  onSearchChange,
  searchPlaceholder,
  filters,
  hasActiveFilters,
  onReset,
  onApply,
  presets,
  activePreset,
  onPresetSelect,
  className,
}: FilterBarProps) {
  return (
    <div className={cn("flex flex-wrap items-center gap-2", className)}>
      <SearchInput
        value={search}
        onChange={onSearchChange}
        placeholder={searchPlaceholder}
        className="max-w-xs"
      />
      {filters}

      {presets && presets.length > 0 && onPresetSelect && (
        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <Button variant="outline" size="sm">
              {presets.find((p) => p.value === activePreset)?.label ?? "Saved views"}
            </Button>
          </DropdownMenuTrigger>
          <DropdownMenuContent align="start">
            <DropdownMenuLabel>Saved views</DropdownMenuLabel>
            <DropdownMenuSeparator />
            {presets.map((preset) => (
              <DropdownMenuItem key={preset.value} onSelect={() => onPresetSelect(preset.value)}>
                {preset.label}
              </DropdownMenuItem>
            ))}
          </DropdownMenuContent>
        </DropdownMenu>
      )}

      {hasActiveFilters && onReset && (
        <Button variant="ghost" size="sm" onClick={onReset}>
          <RotateCcw className="size-3.5" />
          Reset
        </Button>
      )}

      {onApply && (
        <Button size="sm" onClick={onApply}>
          Apply filters
        </Button>
      )}
    </div>
  );
}
