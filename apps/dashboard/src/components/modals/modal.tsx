import type { ReactNode } from "react";

import { cn } from "@/lib/utils";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";

export type ModalSize = "sm" | "md" | "lg" | "fullscreen";

const SIZE_CLASSES: Record<ModalSize, string> = {
  sm: "sm:max-w-sm",
  md: "sm:max-w-lg",
  lg: "sm:max-w-3xl",
  fullscreen: "h-screen w-screen max-w-none sm:max-w-none",
};

export interface ModalProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  title: string;
  description?: string;
  size?: ModalSize;
  footer?: ReactNode;
  children: ReactNode;
}

/** Generic modal for Create/Edit/Information dialogs — Radix Dialog under
 * the hood, so focus trap, ESC-to-close, and overlay click are all free.
 * For destructive confirmations, use ConfirmDialog instead (it uses
 * AlertDialog, which cannot be dismissed by an accidental outside click). */
export function Modal({ open, onOpenChange, title, description, size = "md", footer, children }: ModalProps) {
  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className={cn(SIZE_CLASSES[size], size === "fullscreen" && "flex flex-col")}>
        <DialogHeader>
          <DialogTitle>{title}</DialogTitle>
          {description && <DialogDescription>{description}</DialogDescription>}
        </DialogHeader>
        <div className={cn(size === "fullscreen" && "flex-1 overflow-y-auto")}>{children}</div>
        {footer && <DialogFooter>{footer}</DialogFooter>}
      </DialogContent>
    </Dialog>
  );
}
