import { AlertTriangle, Ban, FileQuestion, ServerCrash, WifiOff } from "lucide-react";

import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

export type ErrorStateVariant = "404" | "403" | "500" | "offline" | "generic";

const VARIANT_CONTENT: Record<
  ErrorStateVariant,
  { icon: typeof FileQuestion; title: string; description: string }
> = {
  "404": {
    icon: FileQuestion,
    title: "Page not found",
    description: "The page you're looking for doesn't exist or may have moved.",
  },
  "403": {
    icon: Ban,
    title: "You don't have access to this",
    description: "Your account doesn't have the permission required for this page.",
  },
  "500": {
    icon: ServerCrash,
    title: "Something went wrong",
    description: "An unexpected error occurred. Try again, or come back later.",
  },
  offline: {
    icon: WifiOff,
    title: "You're offline",
    description: "Check your internet connection and try again.",
  },
  generic: {
    icon: AlertTriangle,
    title: "Something went wrong",
    description: "This couldn't be loaded right now.",
  },
};

export interface ErrorStateProps {
  variant?: ErrorStateVariant;
  title?: string;
  description?: string;
  onRetry?: () => void;
  className?: string;
}

/** Reusable full-panel error state — 404/403/500/offline/generic, all
 * sharing one layout so every failure mode looks consistent. */
export function ErrorState({ variant = "generic", title, description, onRetry, className }: ErrorStateProps) {
  const content = VARIANT_CONTENT[variant];
  const Icon = content.icon;

  return (
    <div
      className={cn(
        "flex flex-col items-center justify-center gap-3 rounded-lg border border-dashed p-12 text-center",
        className,
      )}
    >
      <Icon className="text-muted-foreground size-10" aria-hidden="true" />
      <div>
        <p className="font-medium">{title ?? content.title}</p>
        <p className="text-muted-foreground mt-1 max-w-sm text-sm">
          {description ?? content.description}
        </p>
      </div>
      {onRetry && (
        <Button variant="outline" size="sm" onClick={onRetry} className="mt-2">
          Retry
        </Button>
      )}
    </div>
  );
}
