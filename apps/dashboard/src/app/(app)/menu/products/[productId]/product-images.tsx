"use client";

import { useState } from "react";
import Image from "next/image";
import { ImageIcon, Star, X } from "lucide-react";

import {
  useDeleteProductImage,
  useProductImages,
  useSetThumbnail,
  useUploadProductImage,
} from "@/lib/hooks/use-menu-products";
import { ApiError } from "@/lib/api/errors";
import { SectionCard } from "@/components/section-card";
import { EmptyState } from "@/components/empty-state";
import { ConfirmDialog } from "@/components/modals/confirm-dialog";
import { ImageUpload } from "@/components/forms/image-upload";
import { Skeleton } from "@/components/ui/skeleton";
import { Button } from "@/components/ui/button";

export function ProductImages({ productId }: { productId: string }) {
  const { data: images, isLoading } = useProductImages(productId);
  const uploadImage = useUploadProductImage(productId);
  const deleteImage = useDeleteProductImage(productId);
  const setThumbnail = useSetThumbnail(productId);

  const [pendingFile, setPendingFile] = useState<File | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [pendingDeleteId, setPendingDeleteId] = useState<string | null>(null);

  async function handleFileSelected(file: File | null) {
    setPendingFile(file);
    if (!file) return;
    setError(null);
    try {
      await uploadImage.mutateAsync({ file });
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "The image could not be uploaded.");
    } finally {
      setPendingFile(null);
    }
  }

  return (
    <SectionCard
      title="Images"
      description="JPEG, PNG, or WEBP, up to 5 MB. The first image uploaded becomes the thumbnail automatically."
    >
      <div className="flex flex-col gap-4">
        <ImageUpload
          value={pendingFile}
          onChange={(file) => void handleFileSelected(file)}
          disabled={uploadImage.isPending}
        />
        {uploadImage.isPending && <p className="text-muted-foreground text-sm">Uploading…</p>}
        {error && (
          <p role="alert" className="text-destructive text-sm">
            {error}
          </p>
        )}

        {isLoading ? (
          <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
            <Skeleton className="aspect-square w-full" />
            <Skeleton className="aspect-square w-full" />
          </div>
        ) : !images || images.length === 0 ? (
          <EmptyState icon={ImageIcon} title="No images yet" description="Upload a photo above." />
        ) : (
          <ul className="grid grid-cols-2 gap-3 sm:grid-cols-4">
            {images.map((image) => (
              <li key={image.id} className="group relative overflow-hidden rounded-md border">
                <div className="relative aspect-square w-full">
                  <Image
                    src={image.signed_url}
                    alt={image.alt_text ?? "Product image"}
                    fill
                    className="object-cover"
                    unoptimized
                  />
                </div>
                <div className="absolute inset-x-0 top-0 flex items-center justify-between p-1.5">
                  {image.is_thumbnail ? (
                    <span className="bg-background/90 flex items-center gap-1 rounded px-1.5 py-0.5 text-xs font-medium">
                      <Star className="size-3 fill-current" /> Thumbnail
                    </span>
                  ) : (
                    <Button
                      variant="outline"
                      size="icon"
                      className="bg-background size-6 opacity-0 group-hover:opacity-100"
                      aria-label="Set as thumbnail"
                      disabled={setThumbnail.isPending}
                      onClick={() => setThumbnail.mutate(image.id)}
                    >
                      <Star className="size-3.5" />
                    </Button>
                  )}
                  <Button
                    variant="destructive"
                    size="icon"
                    className="size-6"
                    aria-label="Delete image"
                    onClick={() => setPendingDeleteId(image.id)}
                  >
                    <X className="size-3.5" />
                  </Button>
                </div>
              </li>
            ))}
          </ul>
        )}
      </div>

      <ConfirmDialog
        open={pendingDeleteId !== null}
        onOpenChange={(open) => {
          if (!open) setPendingDeleteId(null);
        }}
        variant="delete"
        title="Delete this image?"
        description="This removes the image permanently — it cannot be restored."
        confirmLabel="Delete image"
        onConfirm={async () => {
          if (!pendingDeleteId) return;
          try {
            await deleteImage.mutateAsync(pendingDeleteId);
            setPendingDeleteId(null);
          } catch (err) {
            setError(err instanceof ApiError ? err.message : "The image could not be deleted.");
          }
        }}
      />
    </SectionCard>
  );
}
