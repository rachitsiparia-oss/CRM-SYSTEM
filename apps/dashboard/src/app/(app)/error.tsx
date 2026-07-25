"use client";

import { useEffect } from "react";

import { ErrorState } from "@/components/error-state";

export default function GlobalError({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  useEffect(() => {
    // Sentry wiring lands with observability setup later in Phase 1/2; for
    // now, keep the failure visible in server logs via console.error.
    console.error(error);
  }, [error]);

  return (
    <div role="alert" className="flex flex-1 items-center justify-center p-8">
      <ErrorState
        variant="500"
        description={
          error.digest ? `Reference: ${error.digest}` : "No further details are available."
        }
        onRetry={reset}
      />
    </div>
  );
}
