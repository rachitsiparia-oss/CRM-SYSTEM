import type { ReactNode } from "react";

import { cn } from "@/lib/utils";

export interface PageHeaderProps {
  title: string;
  description?: string;
  actions?: ReactNode;
  className?: string;
}

/** Consistent page title + description + action-buttons row, used at the
 * top of every module page (CLAUDE.md section 22, "keep common actions
 * visible and predictable"). When `actions` is present, the row is framed
 * as a rounded toolbar bar (Phase 17.5 redesign) — pages with no actions
 * keep the plain bare-title layout so this doesn't box in every one of the
 * 118 routes that just show a title. */
export function PageHeader({ title, description, actions, className }: PageHeaderProps) {
  return (
    <div
      className={cn(
        "flex flex-wrap items-start justify-between gap-3",
        actions && "rounded-2xl border border-border/60 bg-card px-4 py-3 shadow-sm",
        className,
      )}
    >
      <div>
        <h1 className="text-xl font-semibold tracking-tight">{title}</h1>
        {description && <p className="text-muted-foreground mt-1 text-sm">{description}</p>}
      </div>
      {actions && <div className="flex shrink-0 items-center gap-2">{actions}</div>}
    </div>
  );
}
