"use client";

import { useState } from "react";

import { useCreateKnowledgeCategory, useKnowledgeCategories } from "@/lib/hooks/use-knowledge";
import { hasPermission, useCurrentUser } from "@/lib/hooks/use-current-user";
import { ApiError } from "@/lib/api/errors";
import { PageHeader } from "@/components/page-header";
import { SectionCard } from "@/components/section-card";
import { ErrorState } from "@/components/error-state";
import { EmptyState } from "@/components/empty-state";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Skeleton } from "@/components/ui/skeleton";

export function CategoriesView() {
  const { data: currentUser } = useCurrentUser();
  const { data: categories, isLoading, isError, refetch } = useKnowledgeCategories();
  const createCategory = useCreateKnowledgeCategory();

  const [name, setName] = useState("");
  const [code, setCode] = useState("");
  const [error, setError] = useState<string | null>(null);

  const canManage = hasPermission(currentUser, "knowledge.categories.manage");

  const byParent = new Map<string, typeof categories>();
  for (const category of categories ?? []) {
    const key = category.parent_id ?? "root";
    byParent.set(key, [...(byParent.get(key) ?? []), category]);
  }

  function renderChildren(parentKey: string, depth: number) {
    const children = byParent.get(parentKey) ?? [];
    return children.map((category) => (
      <div key={category.id}>
        <div className="flex items-center justify-between border-b py-2 text-sm" style={{ paddingLeft: depth * 16 }}>
          <span>{category.name}</span>
          <span className="text-muted-foreground text-xs">{category.code}</span>
        </div>
        {renderChildren(category.id, depth + 1)}
      </div>
    ));
  }

  return (
    <div className="flex flex-1 flex-col gap-6 p-6">
      <PageHeader
        title="Categories"
        description="Hierarchical grouping for knowledge articles. Tags are reused from the shared tag list."
      />

      {canManage && (
        <SectionCard title="New category">
          {error && <p className="mb-2 text-sm text-red-600">{error}</p>}
          <div className="flex flex-wrap items-end gap-2">
            <div className="flex flex-col gap-1">
              <label className="text-xs text-zinc-500">Name</label>
              <Input value={name} onChange={(e) => setName(e.target.value)} className="w-56" />
            </div>
            <div className="flex flex-col gap-1">
              <label className="text-xs text-zinc-500">Code</label>
              <Input value={code} onChange={(e) => setCode(e.target.value)} className="w-40" />
            </div>
            <Button
              disabled={!name.trim() || !code.trim() || createCategory.isPending}
              onClick={() =>
                createCategory.mutate(
                  { name: name.trim(), code: code.trim() },
                  {
                    onSuccess: () => {
                      setName("");
                      setCode("");
                      setError(null);
                    },
                    onError: (err) =>
                      setError(err instanceof ApiError ? err.message : "Could not create category."),
                  },
                )
              }
            >
              Create
            </Button>
          </div>
        </SectionCard>
      )}

      <SectionCard title="Category tree">
        {isError ? (
          <ErrorState title="Could not load categories" onRetry={() => void refetch()} />
        ) : isLoading ? (
          <Skeleton className="h-40 w-full" />
        ) : !categories?.length ? (
          <EmptyState title="No categories yet" description="Create the first category above." />
        ) : (
          <div>{renderChildren("root", 0)}</div>
        )}
      </SectionCard>
    </div>
  );
}
