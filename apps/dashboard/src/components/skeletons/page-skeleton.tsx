import { Skeleton } from "@/components/ui/skeleton";
import { CardSkeleton } from "./card-skeleton";
import { TableSkeleton } from "./table-skeleton";

/** Full-page loading placeholder: header + a row of stat cards + a table.
 * Used as a route's `loading.tsx` when the page's real shape isn't known
 * yet, or as a manual fallback while the first query is in flight. */
export function PageSkeleton() {
  return (
    <div className="flex flex-col gap-6">
      <div>
        <Skeleton className="h-7 w-48" />
        <Skeleton className="mt-2 h-4 w-72" />
      </div>
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <CardSkeleton />
        <CardSkeleton />
        <CardSkeleton />
        <CardSkeleton />
      </div>
      <TableSkeleton />
    </div>
  );
}
