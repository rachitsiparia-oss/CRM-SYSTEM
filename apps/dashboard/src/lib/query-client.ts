import { QueryClient } from "@tanstack/react-query";

/**
 * One QueryClient per browser session. Server-state caching, retries, and
 * invalidation live here rather than in component state — see CLAUDE.md
 * section 5.1 and ARCHITECTURE_AND_TECH_STACK.md section 6.5.
 */
export function createQueryClient() {
  return new QueryClient({
    defaultOptions: {
      queries: {
        staleTime: 30_000,
        retry: (failureCount, error) => {
          const status = (error as { status?: number } | undefined)?.status;
          if (status !== undefined && status >= 400 && status < 500) {
            return false;
          }
          return failureCount < 2;
        },
      },
    },
  });
}
