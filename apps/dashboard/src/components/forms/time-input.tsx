import * as React from "react";
import { Clock } from "lucide-react";

import { cn } from "@/lib/utils";
import { Input } from "@/components/ui/input";

export const TimeInput = React.forwardRef<HTMLInputElement, React.InputHTMLAttributes<HTMLInputElement>>(
  ({ className, ...props }, ref) => (
    <div className="relative">
      <Clock className="text-muted-foreground pointer-events-none absolute top-1/2 left-3 size-4 -translate-y-1/2" />
      <Input ref={ref} type="time" className={cn("pl-9", className)} {...props} />
    </div>
  ),
);
TimeInput.displayName = "TimeInput";
