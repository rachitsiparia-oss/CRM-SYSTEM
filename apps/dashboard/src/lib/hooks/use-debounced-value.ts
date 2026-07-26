"use client";

import { useEffect, useState } from "react";

/** Debounces a rapidly-changing value (a search box) so list queries fire
 * once the user pauses rather than per keystroke — CLAUDE.md section 5.1
 * ("debounce high-frequency searches and filters"). */
export function useDebouncedValue<T>(value: T, delayMs = 300): T {
  const [debounced, setDebounced] = useState(value);

  useEffect(() => {
    const timer = setTimeout(() => setDebounced(value), delayMs);
    return () => clearTimeout(timer);
  }, [value, delayMs]);

  return debounced;
}
