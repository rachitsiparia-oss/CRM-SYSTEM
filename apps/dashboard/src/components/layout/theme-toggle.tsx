"use client";

import { useEffect, useState } from "react";
import { Moon, Sun } from "lucide-react";

import { Switch } from "@/components/ui/switch";
import { cn } from "@/lib/utils";
import { THEME_STORAGE_KEY, type Theme } from "@/lib/theme";

function applyTheme(theme: Theme) {
  document.documentElement.setAttribute("data-theme", theme);
  window.localStorage.setItem(THEME_STORAGE_KEY, theme);
}

/** Sliding light/dark switch for the header, next to Notifications. Defaults
 * to light on the very first render — same "one-frame flash, corrected on
 * mount" tradeoff already accepted for the sidebar's collapsed state
 * (components/layout/sidebar.tsx) — because the real theme lives in
 * localStorage/DOM, neither of which SSR can see; the root layout's
 * blocking script has already applied the correct theme to <html> by the
 * time this reads it. */
export function ThemeToggle() {
  const [isDark, setIsDark] = useState(false);

  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect
    setIsDark(document.documentElement.getAttribute("data-theme") === "dark");
  }, []);

  function toggle(checked: boolean) {
    const next: Theme = checked ? "dark" : "light";
    applyTheme(next);
    setIsDark(checked);
  }

  return (
    <div className="bg-muted/60 flex items-center gap-2 rounded-full px-3 py-1.5">
      <Sun
        className={cn("size-4", !isDark ? "text-primary" : "text-muted-foreground")}
        aria-hidden="true"
      />
      <Switch
        checked={isDark}
        onCheckedChange={toggle}
        aria-label={isDark ? "Switch to light theme" : "Switch to dark theme"}
      />
      <Moon
        className={cn("size-4", isDark ? "text-primary" : "text-muted-foreground")}
        aria-hidden="true"
      />
    </div>
  );
}
