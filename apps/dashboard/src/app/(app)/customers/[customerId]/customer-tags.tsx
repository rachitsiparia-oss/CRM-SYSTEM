"use client";

import { useState } from "react";
import { TagIcon, X } from "lucide-react";

import {
  useAddCustomerTag,
  useCustomerTags,
  useRemoveCustomerTag,
} from "@/lib/hooks/use-customers";
import { ApiError } from "@/lib/api/errors";
import { SectionCard } from "@/components/section-card";
import { EmptyState } from "@/components/empty-state";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";

export function CustomerTags({ customerId, canEdit }: { customerId: string; canEdit: boolean }) {
  const { data: tags, isLoading } = useCustomerTags(customerId);
  const addTag = useAddCustomerTag(customerId);
  const removeTag = useRemoveCustomerTag(customerId);

  const [name, setName] = useState("");
  const [error, setError] = useState<string | null>(null);

  async function handleAdd() {
    setError(null);
    try {
      await addTag.mutateAsync(name.trim());
      setName("");
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "The tag could not be added.");
    }
  }

  return (
    <SectionCard
      title="Tags"
      description="Tags are shared across customers; names differing only by case or spacing reuse the same tag."
    >
      <div className="flex flex-col gap-4">
        {canEdit && (
          <form
            className="flex flex-wrap items-center gap-2"
            onSubmit={(event) => {
              event.preventDefault();
              if (name.trim()) void handleAdd();
            }}
          >
            <Input
              value={name}
              onChange={(event) => setName(event.target.value)}
              placeholder="Add a tag…"
              aria-label="Tag name"
              className="max-w-xs"
            />
            <Button type="submit" size="sm" disabled={!name.trim() || addTag.isPending}>
              {addTag.isPending ? "Adding…" : "Add tag"}
            </Button>
          </form>
        )}

        {error && (
          <p role="alert" className="text-destructive text-sm">
            {error}
          </p>
        )}

        {isLoading ? (
          <Skeleton className="h-8 w-64" />
        ) : !tags || tags.length === 0 ? (
          <EmptyState
            icon={TagIcon}
            title="No tags applied"
            description="Tags group customers for filtering and future campaign targeting."
          />
        ) : (
          <ul className="flex flex-wrap gap-2">
            {tags.map((tag) => (
              <li key={tag.id}>
                <Badge variant="secondary" className="gap-1.5 py-1">
                  {tag.name}
                  {canEdit && (
                    <button
                      type="button"
                      aria-label={`Remove tag ${tag.name}`}
                      className="hover:text-destructive"
                      disabled={removeTag.isPending}
                      onClick={() => {
                        setError(null);
                        removeTag.mutate(tag.id, {
                          onError: (err) =>
                            setError(
                              err instanceof ApiError
                                ? err.message
                                : "The tag could not be removed.",
                            ),
                        });
                      }}
                    >
                      <X className="size-3" />
                    </button>
                  )}
                </Badge>
              </li>
            ))}
          </ul>
        )}
      </div>
    </SectionCard>
  );
}
