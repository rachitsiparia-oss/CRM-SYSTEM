import * as React from "react";
import { Phone } from "lucide-react";

import { cn } from "@/lib/utils";
import { Input } from "@/components/ui/input";

/** E.164-oriented phone input (no locale-specific formatting library —
 * out of scope for a UI-only foundation component; backend validation
 * remains the authority per CLAUDE.md section 6.3). */
export const PhoneInput = React.forwardRef<HTMLInputElement, React.InputHTMLAttributes<HTMLInputElement>>(
  ({ className, placeholder = "+91 98765 43210", ...props }, ref) => (
    <div className="relative">
      <Phone className="text-muted-foreground pointer-events-none absolute top-1/2 left-3 size-4 -translate-y-1/2" />
      <Input
        ref={ref}
        type="tel"
        inputMode="tel"
        placeholder={placeholder}
        className={cn("pl-9", className)}
        {...props}
      />
    </div>
  ),
);
PhoneInput.displayName = "PhoneInput";
