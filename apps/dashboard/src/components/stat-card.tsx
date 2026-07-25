import type { ComponentType, SVGProps } from "react";

import { Card, CardContent } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { cn } from "@/lib/utils";

export interface StatCardProps {
  label: string;
  value: string | number;
  icon?: ComponentType<SVGProps<SVGSVGElement>>;
  loading?: boolean;
  className?: string;
}

/** A single KPI value with a label — the plain form (no trend). See
 * MetricCard for the version with a delta/trend indicator. */
export function StatCard({ label, value, icon: Icon, loading, className }: StatCardProps) {
  return (
    <Card className={cn(className)}>
      <CardContent className="flex items-center justify-between gap-3">
        <div>
          <p className="text-muted-foreground text-sm">{label}</p>
          {loading ? (
            <Skeleton className="mt-1 h-7 w-20" />
          ) : (
            <p className="text-2xl font-semibold tracking-tight">{value}</p>
          )}
        </div>
        {Icon && (
          <div className="bg-muted text-muted-foreground rounded-full p-2.5">
            <Icon className="size-5" aria-hidden="true" />
          </div>
        )}
      </CardContent>
    </Card>
  );
}
