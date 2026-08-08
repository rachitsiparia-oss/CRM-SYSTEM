"use client";

import { useEffect, useState } from "react";

const CHART_VARS = ["--chart-1", "--chart-2", "--chart-3", "--chart-4", "--chart-5"] as const;
const TEXT_VARS = ["--muted-foreground", "--border", "--brand-primary", "--brand-yellow"] as const;

function readVars(): {
  series: string[];
  mutedForeground: string;
  border: string;
  brandPrimary: string;
  brandYellow: string;
} {
  if (typeof window === "undefined") {
    return { series: [], mutedForeground: "", border: "", brandPrimary: "", brandYellow: "" };
  }
  const styles = getComputedStyle(document.documentElement);
  return {
    series: CHART_VARS.map((name) => styles.getPropertyValue(name).trim()),
    mutedForeground: styles.getPropertyValue(TEXT_VARS[0]).trim(),
    border: styles.getPropertyValue(TEXT_VARS[1]).trim(),
    brandPrimary: styles.getPropertyValue(TEXT_VARS[2]).trim(),
    brandYellow: styles.getPropertyValue(TEXT_VARS[3]).trim(),
  };
}

/** Resolves the --chart-1..5 design tokens to concrete color strings for
 * ECharts (which renders to canvas/SVG and cannot read CSS custom
 * properties itself). Re-reads when the OS color scheme flips, since
 * there's no in-app theme toggle to hook into instead.
 *
 * The lazy useState initializer already gets real values on the client's
 * first render (by then `window` exists, unlike during SSR) — the effect
 * below exists only to subscribe to *future* prefers-color-scheme
 * changes, not to set the initial value, so it never calls setState
 * synchronously in its own body. */
export function useChartColors() {
  const [colors, setColors] = useState(readVars);

  useEffect(() => {
    const media = window.matchMedia("(prefers-color-scheme: dark)");
    const handler = () => setColors(readVars());
    media.addEventListener("change", handler);
    return () => media.removeEventListener("change", handler);
  }, []);

  return colors;
}
