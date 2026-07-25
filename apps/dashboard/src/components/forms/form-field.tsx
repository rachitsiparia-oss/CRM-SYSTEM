import type { ReactNode } from "react";
import { useId } from "react";
import { CheckCircle2 } from "lucide-react";

import { cn } from "@/lib/utils";
import { Label } from "@/components/ui/label";

export interface FormFieldProps {
  label: string;
  htmlFor?: string;
  description?: string;
  error?: string;
  success?: string;
  required?: boolean;
  children: ReactNode;
  className?: string;
}

/** Generic label + input + error/success/description slot, wired for
 * React Hook Form: pass the same `id` you pass to `register()`'s
 * underlying input as `htmlFor`, and this renders the matching
 * `aria-describedby` wiring for validation messages automatically. */
export function FormField({
  label,
  htmlFor,
  description,
  error,
  success,
  required,
  children,
  className,
}: FormFieldProps) {
  const generatedId = useId();
  const fieldId = htmlFor ?? generatedId;
  const descriptionId = description ? `${fieldId}-description` : undefined;
  const errorId = error ? `${fieldId}-error` : undefined;

  return (
    <div className={cn("flex flex-col gap-1.5", className)}>
      <Label htmlFor={fieldId}>
        {label}
        {required && (
          <span className="text-destructive ml-0.5" aria-hidden="true">
            *
          </span>
        )}
      </Label>
      {children}
      {description && !error && (
        <p id={descriptionId} className="text-muted-foreground text-xs">
          {description}
        </p>
      )}
      {error && (
        <p id={errorId} role="alert" className="text-destructive text-sm">
          {error}
        </p>
      )}
      {success && !error && (
        <p className="text-success flex items-center gap-1 text-sm">
          <CheckCircle2 className="size-3.5" /> {success}
        </p>
      )}
    </div>
  );
}
