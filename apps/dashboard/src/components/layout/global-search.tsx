"use client";

import { useEffect, useState } from "react";
import { Search } from "lucide-react";

import {
  CommandDialog,
  CommandEmpty,
  CommandGroup,
  CommandInput,
  CommandItem,
  CommandList,
} from "@/components/ui/command";
import { NAV_SECTIONS } from "./nav-config";

/**
 * UI-only global search / command palette foundation
 * (PROJECT_PLAN.md Phase 4 scope: "Only UI. No backend search."). Today
 * it can only jump between the twelve nav sections via keyboard; wiring
 * real cross-module search results is a later phase's job.
 */
export function GlobalSearch() {
  const [open, setOpen] = useState(false);

  useEffect(() => {
    function handleKeyDown(event: KeyboardEvent) {
      if (event.key === "k" && (event.metaKey || event.ctrlKey)) {
        event.preventDefault();
        setOpen((prev) => !prev);
      }
    }
    document.addEventListener("keydown", handleKeyDown);
    return () => document.removeEventListener("keydown", handleKeyDown);
  }, []);

  return (
    <>
      <button
        type="button"
        onClick={() => setOpen(true)}
        className="text-muted-foreground hover:bg-accent hover:text-accent-foreground flex h-9 w-full max-w-sm items-center gap-2 rounded-md border px-3 text-sm transition-colors"
      >
        <Search className="size-4" aria-hidden="true" />
        <span className="flex-1 text-left">Search…</span>
        <kbd className="bg-muted pointer-events-none hidden rounded border px-1.5 py-0.5 text-[10px] font-medium sm:inline-block">
          ⌘K
        </kbd>
      </button>
      <CommandDialog open={open} onOpenChange={setOpen} title="Search" description="Jump to a section">
        <CommandInput placeholder="Search sections…" />
        <CommandList>
          <CommandEmpty>No results found.</CommandEmpty>
          <CommandGroup heading="Sections">
            {NAV_SECTIONS.map((section) => (
              <CommandItem
                key={section.href}
                value={section.label}
                onSelect={() => {
                  setOpen(false);
                  window.location.assign(section.href);
                }}
              >
                <section.icon className="size-4" aria-hidden="true" />
                {section.label}
              </CommandItem>
            ))}
          </CommandGroup>
        </CommandList>
      </CommandDialog>
    </>
  );
}
