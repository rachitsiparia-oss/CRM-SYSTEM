"use client";

import dynamic from "next/dynamic";

import { ChartSkeleton } from "./chart-skeleton";
import type { ChartSeries } from "./line-chart";

export interface BarChartProps {
  categories: string[];
  series: ChartSeries[];
  loading?: boolean;
  height?: number;
  horizontal?: boolean;
  stacked?: boolean;
}

// Phase 16 hardening: echarts-for-react wraps the full echarts package
// (a large dependency — CLAUDE.md section 5.1, "avoid importing large
// libraries into shared client bundles"), so the real implementation is
// code-split out and only fetched when a chart actually needs to render —
// never during SSR (charts are canvas-based, client-only regardless) and
// never while `loading` is true (the skeleton below covers that case
// without even triggering the dynamic import).
const BarChartImpl = dynamic(() => import("./bar-chart-impl").then((m) => m.BarChartImpl), {
  ssr: false,
  loading: () => <ChartSkeleton />,
});

export function BarChart(props: BarChartProps) {
  if (props.loading) return <ChartSkeleton height={props.height ?? 280} />;
  return <BarChartImpl {...props} />;
}
