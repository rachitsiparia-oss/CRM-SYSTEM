"use client";

import { useState } from "react";
import Link from "next/link";
import { X } from "lucide-react";

import { useModifierGroupList } from "@/lib/hooks/use-menu-modifiers";
import {
  useAttachModifierGroup,
  useDetachModifierGroup,
  useProductModifierGroups,
} from "@/lib/hooks/use-menu-products";
import { ApiError } from "@/lib/api/errors";
import { SectionCard } from "@/components/section-card";
import { EmptyState } from "@/components/empty-state";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";

export function ProductModifiers({ productId }: { productId: string }) {
  const { data: allGroups } = useModifierGroupList();
  const { data: mappings, isLoading } = useProductModifierGroups(productId);
  const attachGroup = useAttachModifierGroup(productId);
  const detachGroup = useDetachModifierGroup(productId);

  const [selectedGroupId, setSelectedGroupId] = useState("");
  const [error, setError] = useState<string | null>(null);

  const attachedIds = new Set((mappings ?? []).map((m) => m.modifier_group_id));
  const availableGroups = (allGroups ?? []).filter((g) => !attachedIds.has(g.id));

  return (
    <SectionCard
      title="Modifier groups"
      description="Which reusable option groups (add-ons, spice level, etc.) apply to this product."
    >
      <div className="flex flex-col gap-4">
        {availableGroups.length > 0 && (
          <div className="flex items-center gap-2">
            <Select value={selectedGroupId} onValueChange={setSelectedGroupId}>
              <SelectTrigger className="w-56">
                <SelectValue placeholder="Attach a modifier group…" />
              </SelectTrigger>
              <SelectContent>
                {availableGroups.map((group) => (
                  <SelectItem key={group.id} value={group.id}>
                    {group.name}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
            <Button
              size="sm"
              disabled={!selectedGroupId || attachGroup.isPending}
              onClick={() => {
                setError(null);
                attachGroup.mutate(
                  { modifierGroupId: selectedGroupId },
                  {
                    onSuccess: () => setSelectedGroupId(""),
                    onError: (err) =>
                      setError(err instanceof ApiError ? err.message : "Could not attach group."),
                  },
                );
              }}
            >
              Attach
            </Button>
          </div>
        )}

        {error && (
          <p role="alert" className="text-destructive text-sm">
            {error}
          </p>
        )}

        {isLoading ? (
          <Skeleton className="h-10 w-64" />
        ) : !mappings || mappings.length === 0 ? (
          <EmptyState
            title="No modifier groups attached"
            description="Attach a group above, or create one from the Modifier Groups page."
            action={
              <Button variant="outline" size="sm" asChild>
                <Link href="/menu/modifier-groups">Manage modifier groups</Link>
              </Button>
            }
          />
        ) : (
          <ul className="flex flex-wrap gap-2">
            {mappings.map((mapping) => {
              const group = allGroups?.find((g) => g.id === mapping.modifier_group_id);
              return (
                <li key={mapping.modifier_group_id}>
                  <Badge variant="secondary" className="gap-1.5 py-1">
                    {group?.name ?? mapping.modifier_group_id}
                    <button
                      type="button"
                      aria-label={`Detach ${group?.name ?? "modifier group"}`}
                      className="hover:text-destructive"
                      onClick={() => {
                        setError(null);
                        detachGroup.mutate(mapping.modifier_group_id, {
                          onError: (err) =>
                            setError(
                              err instanceof ApiError ? err.message : "Could not detach group.",
                            ),
                        });
                      }}
                    >
                      <X className="size-3" />
                    </button>
                  </Badge>
                </li>
              );
            })}
          </ul>
        )}
      </div>
    </SectionCard>
  );
}
