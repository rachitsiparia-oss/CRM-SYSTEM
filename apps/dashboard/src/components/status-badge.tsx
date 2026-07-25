import { AlertCircle, CheckCircle2, CircleDot, Clock, XCircle } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { cn } from "@/lib/utils";

export type StatusTone = "neutral" | "info" | "success" | "warning" | "danger";

const TONE_STYLES: Record<StatusTone, string> = {
  neutral: "bg-muted text-muted-foreground border-transparent",
  info: "bg-blue-100 text-blue-800 border-transparent dark:bg-blue-950 dark:text-blue-300",
  success: "bg-success/15 text-success border-transparent",
  warning: "bg-warning/20 text-warning-foreground border-transparent",
  danger: "bg-destructive/15 text-destructive border-transparent",
};

const TONE_ICONS: Record<StatusTone, typeof CircleDot> = {
  neutral: CircleDot,
  info: Clock,
  success: CheckCircle2,
  warning: AlertCircle,
  danger: XCircle,
};

export interface StatusBadgeProps {
  label: string;
  tone?: StatusTone;
  className?: string;
}

/** A status pill that never relies on color alone — every tone pairs a
 * distinct icon with the color, so it still reads correctly for
 * colorblind users or in grayscale (CLAUDE.md section 22, "never rely on
 * color alone"). */
export function StatusBadge({ label, tone = "neutral", className }: StatusBadgeProps) {
  const Icon = TONE_ICONS[tone];
  return (
    <Badge variant="outline" className={cn("gap-1 font-medium", TONE_STYLES[tone], className)}>
      <Icon className="size-3" aria-hidden="true" />
      {label}
    </Badge>
  );
}
