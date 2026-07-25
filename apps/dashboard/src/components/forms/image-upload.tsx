"use client";

import { useEffect, useMemo, useRef } from "react";
import Image from "next/image";
import { ImagePlus, X } from "lucide-react";

import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";

export interface ImageUploadProps {
  value: File | null;
  onChange: (file: File | null) => void;
  disabled?: boolean;
  className?: string;
}

/** Presentation-only single-image picker with a live preview. No upload
 * transport — Supabase Storage wiring belongs to whichever business
 * feature uses this later (CLAUDE.md section 9.3, private-by-default
 * storage, is enforced server-side, not here). */
export function ImageUpload({ value, onChange, disabled, className }: ImageUploadProps) {
  const inputRef = useRef<HTMLInputElement>(null);
  // Derived, not stored state — the object URL is a pure function of
  // `value`; only its cleanup needs an effect.
  const previewUrl = useMemo(() => (value ? URL.createObjectURL(value) : null), [value]);

  useEffect(() => {
    return () => {
      if (previewUrl) URL.revokeObjectURL(previewUrl);
    };
  }, [previewUrl]);

  return (
    <div className={cn("flex items-center gap-4", className)}>
      <div
        role="button"
        tabIndex={0}
        aria-disabled={disabled}
        onClick={() => inputRef.current?.click()}
        onKeyDown={(e) => (e.key === "Enter" || e.key === " ") && inputRef.current?.click()}
        className={cn(
          "bg-muted relative flex size-20 shrink-0 cursor-pointer items-center justify-center overflow-hidden rounded-full border",
          disabled && "cursor-not-allowed opacity-50",
        )}
      >
        {previewUrl ? (
          <Image src={previewUrl} alt="Preview" fill className="object-cover" unoptimized />
        ) : (
          <ImagePlus className="text-muted-foreground size-6" aria-hidden="true" />
        )}
        <input
          ref={inputRef}
          type="file"
          accept="image/*"
          disabled={disabled}
          onChange={(e) => onChange(e.target.files?.[0] ?? null)}
          className="sr-only"
        />
      </div>
      <div className="flex flex-col gap-1">
        <Button
          type="button"
          variant="outline"
          size="sm"
          disabled={disabled}
          onClick={() => inputRef.current?.click()}
        >
          {value ? "Replace image" : "Upload image"}
        </Button>
        {value && (
          <Button
            type="button"
            variant="ghost"
            size="sm"
            disabled={disabled}
            onClick={() => onChange(null)}
            className="text-muted-foreground"
          >
            <X className="size-3.5" /> Remove
          </Button>
        )}
      </div>
    </div>
  );
}
