"use client";

import { useEffect } from "react";

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
    <div role="alert" className="flex flex-1 flex-col items-start gap-3 p-8">
      <h1 className="text-lg font-semibold text-zinc-900 dark:text-zinc-50">
        Something went wrong
      </h1>
      <p className="text-sm text-zinc-500 dark:text-zinc-400">
        {error.digest
          ? `Reference: ${error.digest}`
          : "No further details are available."}
      </p>
      <button
        type="button"
        onClick={reset}
        className="rounded-md border border-zinc-300 px-3 py-1.5 text-sm font-medium text-zinc-700 hover:bg-zinc-100 dark:border-zinc-700 dark:text-zinc-200 dark:hover:bg-zinc-900"
      >
        Try again
      </button>
    </div>
  );
}
