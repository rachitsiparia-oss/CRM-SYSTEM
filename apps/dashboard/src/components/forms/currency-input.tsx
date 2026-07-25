import * as React from "react";

import { cn } from "@/lib/utils";
import { Input } from "@/components/ui/input";

export interface CurrencyInputProps extends React.InputHTMLAttributes<HTMLInputElement> {
  currencySymbol?: string;
}

/** Presentation only — decimal rupee display for humans to type into.
 * Converting to/from integer minor units for storage is the calling
 * business form's job, backend-verified either way (CLAUDE.md section 7,
 * "the frontend may format rupees and paise for display but is never the
 * calculation authority"). This component has no currency-math opinions. */
export const CurrencyInput = React.forwardRef<HTMLInputElement, CurrencyInputProps>(
  ({ className, currencySymbol = "₹", ...props }, ref) => (
    <div className="relative">
      <span className="text-muted-foreground pointer-events-none absolute top-1/2 left-3 -translate-y-1/2 text-sm">
        {currencySymbol}
      </span>
      <Input
        ref={ref}
        type="number"
        inputMode="decimal"
        step="0.01"
        className={cn("pl-7 text-right", className)}
        {...props}
      />
    </div>
  ),
);
CurrencyInput.displayName = "CurrencyInput";
