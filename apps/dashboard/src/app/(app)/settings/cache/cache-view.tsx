"use client";

import { useState } from "react";
import type { CacheFamily } from "@rkpr/contracts";
import { Trash2 } from "lucide-react";

import { useCacheFamilyList, useInvalidateCacheFamily } from "@/lib/hooks/use-cache";
import { hasPermission, useCurrentUser } from "@/lib/hooks/use-current-user";
import { humanize } from "@/lib/crm-display";
import { PageHeader } from "@/components/page-header";
import { SectionCard } from "@/components/section-card";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";

export function CacheView() {
  const { data: currentUser } = useCurrentUser();
  const canInvalidate = hasPermission(currentUser, "cache.invalidate");
  const { data: families, isLoading } = useCacheFamilyList();

  return (
    <div className="flex flex-1 flex-col gap-6 p-6">
      <PageHeader
        title="Cache"
        description="Redis-backed L2 cache families and their TTLs. Invalidating a family forces every key under it to be recomputed on next read."
      />

      {isLoading ? (
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {Array.from({ length: 6 }).map((_, i) => (
            <Skeleton key={i} className="h-28 w-full" />
          ))}
        </div>
      ) : (
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {(families ?? []).map((family) => (
            <CacheFamilyCard key={family.family} family={family} canInvalidate={canInvalidate} />
          ))}
        </div>
      )}
    </div>
  );
}

function CacheFamilyCard({
  family,
  canInvalidate,
}: {
  family: CacheFamily;
  canInvalidate: boolean;
}) {
  const invalidate = useInvalidateCacheFamily();
  const [lastRemoved, setLastRemoved] = useState<number | null>(null);

  return (
    <SectionCard title={humanize(family.family)} description={`TTL: ${family.ttl_seconds}s`}>
      <div className="flex items-center justify-between">
        <span className="text-muted-foreground text-xs">
          {lastRemoved !== null ? `${lastRemoved} key(s) removed` : " "}
        </span>
        {canInvalidate && (
          <Button
            size="sm"
            variant="outline"
            disabled={invalidate.isPending}
            onClick={() =>
              invalidate.mutate(family.family, {
                onSuccess: (response) => setLastRemoved(response.data.keys_removed),
              })
            }
          >
            <Trash2 className="size-3.5" />
            Invalidate
          </Button>
        )}
      </div>
    </SectionCard>
  );
}
