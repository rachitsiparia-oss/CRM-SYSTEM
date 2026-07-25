"use client";

import { useState } from "react";
import { AlertTriangle, CheckCircle2, Info, ShieldAlert, Trash2 } from "lucide-react";

import { cn } from "@/lib/utils";
import { buttonVariants } from "@/components/ui/button";
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from "@/components/ui/alert-dialog";

export type ConfirmDialogVariant = "confirm" | "delete" | "info" | "warning" | "success" | "danger";

const VARIANT_META: Record<ConfirmDialogVariant, { icon: typeof Info; iconClass: string; destructive: boolean }> = {
  confirm: { icon: CheckCircle2, iconClass: "text-primary", destructive: false },
  delete: { icon: Trash2, iconClass: "text-destructive", destructive: true },
  info: { icon: Info, iconClass: "text-blue-600", destructive: false },
  warning: { icon: AlertTriangle, iconClass: "text-warning-foreground", destructive: false },
  success: { icon: CheckCircle2, iconClass: "text-success", destructive: false },
  danger: { icon: ShieldAlert, iconClass: "text-destructive", destructive: true },
};

export interface ConfirmDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  title: string;
  description?: string;
  variant?: ConfirmDialogVariant;
  confirmLabel?: string;
  cancelLabel?: string;
  onConfirm: () => void | Promise<void>;
  /** Require the user to type this exact text before confirming — for the
   * highest-risk deletes. Purely a UI safeguard; the backend remains the
   * authority (CLAUDE.md section 10, "confirm dangerous or irreversible
   * actions"). */
  requireTypedConfirmation?: string;
}

/** Uses AlertDialog (not Dialog): it cannot be dismissed by clicking the
 * overlay, which is exactly the behavior a destructive confirmation
 * needs. Covers Confirmation/Delete/Information/Warning/Success/Danger —
 * all the same shape, only the icon, tone, and copy change. */
export function ConfirmDialog({
  open,
  onOpenChange,
  title,
  description,
  variant = "confirm",
  confirmLabel = "Confirm",
  cancelLabel = "Cancel",
  onConfirm,
  requireTypedConfirmation,
}: ConfirmDialogProps) {
  const [pending, setPending] = useState(false);
  const [typedValue, setTypedValue] = useState("");
  const meta = VARIANT_META[variant];
  const Icon = meta.icon;
  const confirmDisabled =
    pending || (!!requireTypedConfirmation && typedValue !== requireTypedConfirmation);

  async function handleConfirm() {
    setPending(true);
    try {
      await onConfirm();
      onOpenChange(false);
      setTypedValue("");
    } finally {
      setPending(false);
    }
  }

  return (
    <AlertDialog open={open} onOpenChange={onOpenChange}>
      <AlertDialogContent>
        <AlertDialogHeader>
          <div className="flex items-center gap-2">
            <Icon className={cn("size-5", meta.iconClass)} aria-hidden="true" />
            <AlertDialogTitle>{title}</AlertDialogTitle>
          </div>
          {description && <AlertDialogDescription>{description}</AlertDialogDescription>}
        </AlertDialogHeader>
        {requireTypedConfirmation && (
          <input
            value={typedValue}
            onChange={(e) => setTypedValue(e.target.value)}
            placeholder={`Type "${requireTypedConfirmation}" to confirm`}
            className="border-input h-9 rounded-md border bg-transparent px-3 text-sm"
          />
        )}
        <AlertDialogFooter>
          <AlertDialogCancel disabled={pending}>{cancelLabel}</AlertDialogCancel>
          <AlertDialogAction
            disabled={confirmDisabled}
            onClick={(e) => {
              e.preventDefault();
              void handleConfirm();
            }}
            className={cn(meta.destructive && buttonVariants({ variant: "destructive" }))}
          >
            {pending ? "Working…" : confirmLabel}
          </AlertDialogAction>
        </AlertDialogFooter>
      </AlertDialogContent>
    </AlertDialog>
  );
}
