import type { ComponentType, SVGProps } from "react";
import { ArrowDown, ArrowUp, Minus } from "lucide-react";

import { Card, CardContent } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { cn } from "@/lib/utils";

export interface MetricCardProps {
  label: string;
  value: string | number;
  icon?: ComponentType<SVGProps<SVGSVGElement>>;
  /** Percentage change vs. the prior period; omit when there's nothing to compare against. */
  changePercent?: number;
  changeLabel?: string;
  loading?: boolean;
  className?: string;
}

/** A KPI value with a trend indicator vs. a prior period. Trend direction
 * is never conveyed by color alone — an arrow icon + numeric sign both
 * carry the meaning (CLAUDE.md section 22). */
export function MetricCard({
  label,
  value,
  icon: Icon,
  changePercent,
  changeLabel = "vs. previous period",
  loading,
  className,
}: MetricCardProps) {
  const trend = changePercent === undefined ? "flat" : changePercent > 0 ? "up" : changePercent < 0 ? "down" : "flat";
  const TrendIcon = trend === "up" ? ArrowUp : trend === "down" ? ArrowDown : Minus;

  return (
    <Card className={cn(className)}>
      <CardContent className="flex items-start justify-between gap-3">
        <div className="flex flex-col gap-1">
          <p className="text-muted-foreground text-sm">{label}</p>
          {loading ? (
            <Skeleton className="h-8 w-24" />
          ) : (
            <p className="text-3xl font-semibold tracking-tight">{value}</p>
          )}
          {!loading && changePercent !== undefined && (
            <p
              className={cn(
                "flex items-center gap-1 text-xs font-medium",
                trend === "up" && "text-success",
                trend === "down" && "text-destructive",
                trend === "flat" && "text-muted-foreground",
              )}
            >
              <TrendIcon className="size-3" aria-hidden="true" />
              <span>
                {changePercent > 0 ? "+" : ""}
                {changePercent}%
              </span>
              <span className="text-muted-foreground font-normal">{changeLabel}</span>
            </p>
          )}
        </div>
        {Icon && (
          <div className="bg-primary/10 text-primary rounded-full p-2.5">
            <Icon className="size-5" aria-hidden="true" />
          </div>
        )}
      </CardContent>
    </Card>
  );
}
