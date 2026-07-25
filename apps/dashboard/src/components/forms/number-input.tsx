import * as React from "react";

import { cn } from "@/lib/utils";
import { Input } from "@/components/ui/input";

export const NumberInput = React.forwardRef<HTMLInputElement, React.InputHTMLAttributes<HTMLInputElement>>(
  ({ className, ...props }, ref) => (
    <Input
      ref={ref}
      type="number"
      inputMode="numeric"
      className={cn("text-right", className)}
      {...props}
    />
  ),
);
NumberInput.displayName = "NumberInput";
