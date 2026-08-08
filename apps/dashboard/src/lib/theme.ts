export type Theme = "light" | "dark";

/** Must match the literal string hardcoded in the blocking inline script in
 * apps/dashboard/src/app/layout.tsx — that script can't import this module
 * (it runs standalone, before any JS bundle loads), so the key is
 * duplicated there deliberately; keep both in sync if it ever changes. */
export const THEME_STORAGE_KEY = "rkpr:theme";
