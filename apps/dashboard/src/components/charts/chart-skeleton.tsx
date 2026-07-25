import { Skeleton } from "@/components/ui/skeleton";

export function ChartSkeleton({ height = 280 }: { height?: number }) {
  return <Skeleton style={{ height }} className="w-full rounded-lg" />;
}
