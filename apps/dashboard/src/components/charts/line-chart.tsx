"use client";

import ReactECharts from "echarts-for-react";

import { ChartSkeleton } from "./chart-skeleton";
import { useChartColors } from "./use-chart-colors";

export interface ChartSeries {
  name: string;
  data: number[];
}

export interface LineChartProps {
  categories: string[];
  series: ChartSeries[];
  loading?: boolean;
  height?: number;
  smooth?: boolean;
  area?: boolean;
}

/** Generic line/area chart wrapper — no analytics logic, just rendering.
 * Callers supply already-aggregated data from a bounded API endpoint
 * (CLAUDE.md section 5.1, "never send raw massive datasets to the chart
 * library"). */
export function LineChart({ categories, series, loading, height = 280, smooth = true, area }: LineChartProps) {
  const colors = useChartColors();

  if (loading) return <ChartSkeleton height={height} />;

  const option = {
    color: colors.series,
    grid: { left: 8, right: 8, top: 24, bottom: 8, containLabel: true },
    tooltip: { trigger: "axis" },
    legend: series.length > 1 ? { top: 0 } : undefined,
    xAxis: { type: "category", data: categories, axisLine: { lineStyle: { color: colors.border } } },
    yAxis: { type: "value", splitLine: { lineStyle: { color: colors.border } } },
    series: series.map((s) => ({
      name: s.name,
      type: "line",
      smooth,
      data: s.data,
      areaStyle: area ? { opacity: 0.15 } : undefined,
    })),
  };

  return <ReactECharts option={option} style={{ height }} notMerge />;
}
