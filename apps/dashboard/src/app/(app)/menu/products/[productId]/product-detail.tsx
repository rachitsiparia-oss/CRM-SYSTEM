"use client";

import { useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { ArrowLeft, Copy } from "lucide-react";

import {
  useArchiveProduct,
  useDuplicateProduct,
  useProductDetail,
  useRestoreProduct,
} from "@/lib/hooks/use-menu-products";
import { useCategoryList } from "@/lib/hooks/use-menu-categories";
import { hasPermission, useCurrentUser } from "@/lib/hooks/use-current-user";
import {
  FOOD_TYPE_TONES,
  PRODUCT_ACTIVE_TONE,
  PRODUCT_AVAILABILITY_TONE,
  formatMinorUnits,
  humanize,
} from "@/lib/crm-display";
import { ApiError } from "@/lib/api/errors";
import { PageHeader } from "@/components/page-header";
import { PageSkeleton } from "@/components/skeletons/page-skeleton";
import { ErrorState } from "@/components/error-state";
import { StatusBadge } from "@/components/status-badge";
import { ConfirmDialog } from "@/components/modals/confirm-dialog";
import { Button } from "@/components/ui/button";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { ProductEditForm } from "./product-edit-form";
import { ProductVariants } from "./product-variants";
import { ProductModifiers } from "./product-modifiers";
import { ProductImages } from "./product-images";

export function ProductDetail({ productId }: { productId: string }) {
  const router = useRouter();
  const { data: currentUser } = useCurrentUser();
  const { data: product, isLoading, isError, refetch } = useProductDetail(productId);
  const { data: categories } = useCategoryList({ page: 1, pageSize: 100, sort: "sort_order" });
  const archiveProduct = useArchiveProduct(productId);
  const restoreProduct = useRestoreProduct(productId);
  const duplicateProduct = useDuplicateProduct(productId);

  const [confirmArchive, setConfirmArchive] = useState(false);
  const [actionError, setActionError] = useState<string | null>(null);

  const canUpdate = hasPermission(currentUser, "menu.update");
  const canCreate = hasPermission(currentUser, "menu.create");
  const canArchive = hasPermission(currentUser, "menu.archive");
  const canRestore = hasPermission(currentUser, "menu.restore");
  const canManageModifiers = hasPermission(currentUser, "menu.modifiers.manage");
  const canManageImages = hasPermission(currentUser, "menu.images.manage");

  if (isLoading) {
    return (
      <div className="flex-1 p-6">
        <PageSkeleton />
      </div>
    );
  }

  if (isError || !product) {
    return (
      <div className="flex-1 p-6">
        <ErrorState
          variant="404"
          title="Product not found"
          description="This product may have been archived or never existed."
          onRetry={() => void refetch()}
        />
      </div>
    );
  }

  const category = categories?.data.find((c) => c.id === product.category_id);

  function reportError(fallback: string) {
    return (error: unknown) =>
      setActionError(error instanceof ApiError ? error.message : fallback);
  }

  return (
    <div className="flex flex-1 flex-col gap-6 p-6">
      <div>
        <Link
          href="/menu"
          className="text-muted-foreground inline-flex items-center gap-1 text-sm hover:underline"
        >
          <ArrowLeft className="size-3.5" />
          Menu Products
        </Link>
      </div>

      <PageHeader
        title={product.display_name ?? product.name}
        description={`${product.product_code} · ${category?.name ?? humanize(null)}`}
        actions={
          <div className="flex flex-wrap items-center gap-2">
            <StatusBadge
              label={humanize(product.food_type)}
              tone={FOOD_TYPE_TONES[product.food_type]}
            />
            <StatusBadge
              label={product.is_active ? "Active" : "Inactive"}
              tone={PRODUCT_ACTIVE_TONE[product.is_active ? "active" : "inactive"]}
            />
            <StatusBadge
              label={product.is_available ? "Available" : "Unavailable"}
              tone={
                PRODUCT_AVAILABILITY_TONE[product.is_available ? "available" : "unavailable"]
              }
            />
            {canCreate && (
              <Button
                variant="outline"
                size="sm"
                disabled={duplicateProduct.isPending}
                onClick={() =>
                  duplicateProduct.mutate(undefined, {
                    onSuccess: (result) => router.push(`/menu/products/${result.data.id}`),
                    onError: reportError("The product could not be duplicated."),
                  })
                }
              >
                <Copy className="size-3.5" />
                Duplicate
              </Button>
            )}
            {product.is_active === false && canRestore ? (
              <Button
                variant="outline"
                size="sm"
                disabled={restoreProduct.isPending}
                onClick={() =>
                  restoreProduct.mutate(undefined, {
                    onError: reportError("The product could not be restored."),
                  })
                }
              >
                Restore
              </Button>
            ) : (
              canArchive && (
                <Button variant="outline" size="sm" onClick={() => setConfirmArchive(true)}>
                  Archive
                </Button>
              )
            )}
          </div>
        }
      />

      {actionError && (
        <p role="alert" className="text-destructive text-sm">
          {actionError}
        </p>
      )}

      <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
        <div className="rounded-md border p-3">
          <p className="text-muted-foreground text-xs">Base price</p>
          <p className="text-lg font-semibold">{formatMinorUnits(product.base_price_minor)}</p>
        </div>
        <div className="rounded-md border p-3">
          <p className="text-muted-foreground text-xs">Preparation time</p>
          <p className="text-lg font-semibold">
            {product.preparation_minutes ? `${product.preparation_minutes} min` : "—"}
          </p>
        </div>
        <div className="rounded-md border p-3">
          <p className="text-muted-foreground text-xs">Calories</p>
          <p className="text-lg font-semibold">{product.calories ?? "—"}</p>
        </div>
        <div className="rounded-md border p-3">
          <p className="text-muted-foreground text-xs">Availability source</p>
          <p className="text-lg font-semibold">{humanize(product.availability_source)}</p>
        </div>
      </div>

      <Tabs defaultValue="profile">
        <TabsList>
          <TabsTrigger value="profile">Profile &amp; Pricing</TabsTrigger>
          <TabsTrigger value="variants">Variants</TabsTrigger>
          <TabsTrigger value="modifiers">Modifiers</TabsTrigger>
          <TabsTrigger value="images">Images</TabsTrigger>
        </TabsList>

        <TabsContent value="profile" className="mt-4">
          {canUpdate ? (
            <ProductEditForm product={product} />
          ) : (
            <p className="text-muted-foreground text-sm">
              You can view this product but not edit it — editing requires the{" "}
              <code className="font-mono text-xs">menu.update</code> permission.
            </p>
          )}
        </TabsContent>

        <TabsContent value="variants" className="mt-4">
          <ProductVariants productId={productId} />
        </TabsContent>

        <TabsContent value="modifiers" className="mt-4">
          {canManageModifiers ? (
            <ProductModifiers productId={productId} />
          ) : (
            <p className="text-muted-foreground text-sm">
              Managing modifier groups requires the{" "}
              <code className="font-mono text-xs">menu.modifiers.manage</code> permission.
            </p>
          )}
        </TabsContent>

        <TabsContent value="images" className="mt-4">
          {canManageImages ? (
            <ProductImages productId={productId} />
          ) : (
            <p className="text-muted-foreground text-sm">
              Managing images requires the{" "}
              <code className="font-mono text-xs">menu.images.manage</code> permission.
            </p>
          )}
        </TabsContent>
      </Tabs>

      <ConfirmDialog
        open={confirmArchive}
        onOpenChange={setConfirmArchive}
        variant="warning"
        title="Archive this product?"
        description="It stays in the system with full history and can be restored later. It is hidden from the default product list."
        confirmLabel="Archive product"
        onConfirm={async () => {
          setActionError(null);
          try {
            await archiveProduct.mutateAsync("Archived from the product profile page.");
          } catch (error) {
            reportError("The product could not be archived.")(error);
          }
        }}
      />
    </div>
  );
}
