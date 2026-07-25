import * as React from "react";
import { Mail } from "lucide-react";

import { cn } from "@/lib/utils";
import { Input } from "@/components/ui/input";

export const EmailInput = React.forwardRef<HTMLInputElement, React.InputHTMLAttributes<HTMLInputElement>>(
  ({ className, placeholder = "name@example.com", ...props }, ref) => (
    <div className="relative">
      <Mail className="text-muted-foreground pointer-events-none absolute top-1/2 left-3 size-4 -translate-y-1/2" />
      <Input
        ref={ref}
        type="email"
        inputMode="email"
        placeholder={placeholder}
        className={cn("pl-9", className)}
        {...props}
      />
    </div>
  ),
);
EmailInput.displayName = "EmailInput";
