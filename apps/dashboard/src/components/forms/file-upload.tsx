"use client";

import { useId, useRef, useState, type DragEvent } from "react";
import { File as FileIcon, Upload, X } from "lucide-react";

import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";

export interface FileUploadProps {
  accept?: string;
  multiple?: boolean;
  disabled?: boolean;
  files: File[];
  onFilesChange: (files: File[]) => void;
  helperText?: string;
  className?: string;
}

/** Presentation-only drag-and-drop file picker — no upload transport here.
 * Callers own what happens to `files` (Supabase Storage wiring is a later
 * phase's job; this is only the reusable UI). */
export function FileUpload({
  accept,
  multiple,
  disabled,
  files,
  onFilesChange,
  helperText,
  className,
}: FileUploadProps) {
  const inputId = useId();
  const inputRef = useRef<HTMLInputElement>(null);
  const [dragging, setDragging] = useState(false);

  function addFiles(list: FileList | null) {
    if (!list) return;
    const next = multiple ? [...files, ...Array.from(list)] : [list[0]];
    onFilesChange(next.filter(Boolean) as File[]);
  }

  function handleDrop(event: DragEvent<HTMLDivElement>) {
    event.preventDefault();
    setDragging(false);
    if (disabled) return;
    addFiles(event.dataTransfer.files);
  }

  return (
    <div className={cn("flex flex-col gap-2", className)}>
      <div
        role="button"
        tabIndex={0}
        aria-disabled={disabled}
        onClick={() => inputRef.current?.click()}
        onKeyDown={(e) => (e.key === "Enter" || e.key === " ") && inputRef.current?.click()}
        onDragOver={(e) => {
          e.preventDefault();
          if (!disabled) setDragging(true);
        }}
        onDragLeave={() => setDragging(false)}
        onDrop={handleDrop}
        className={cn(
          "flex cursor-pointer flex-col items-center justify-center gap-2 rounded-lg border border-dashed p-8 text-center transition-colors",
          dragging && "border-primary bg-accent",
          disabled && "cursor-not-allowed opacity-50",
        )}
      >
        <Upload className="text-muted-foreground size-6" aria-hidden="true" />
        <p className="text-sm">
          <span className="font-medium">Click to upload</span> or drag and drop
        </p>
        {helperText && <p className="text-muted-foreground text-xs">{helperText}</p>}
        <input
          ref={inputRef}
          id={inputId}
          type="file"
          accept={accept}
          multiple={multiple}
          disabled={disabled}
          onChange={(e) => addFiles(e.target.files)}
          className="sr-only"
        />
      </div>

      {files.length > 0 && (
        <ul className="flex flex-col gap-1.5">
          {files.map((file, index) => (
            <li
              key={`${file.name}-${index}`}
              className="bg-muted flex items-center justify-between gap-2 rounded-md px-3 py-1.5 text-sm"
            >
              <span className="flex min-w-0 items-center gap-2">
                <FileIcon className="text-muted-foreground size-4 shrink-0" />
                <span className="truncate">{file.name}</span>
              </span>
              <Button
                type="button"
                variant="ghost"
                size="icon"
                className="size-6"
                aria-label={`Remove ${file.name}`}
                onClick={() => onFilesChange(files.filter((_, i) => i !== index))}
              >
                <X className="size-3.5" />
              </Button>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
