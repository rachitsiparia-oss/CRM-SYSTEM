"use client";

import ReactECharts from "echarts-for-react";

import type { ChartSeries } from "./line-chart";
import { ChartSkeleton } from "./chart-skeleton";
import { useChartColors } from "./use-chart-colors";

export interface BarChartProps {
  categories: string[];
  series: ChartSeries[];
  loading?: boolean;
  height?: number;
  horizontal?: boolean;
  stacked?: boolean;
}

export function BarChart({ categories, series, loading, height = 280, horizontal, stacked }: BarChartProps) {
  const colors = useChartColors();

  if (loading) return <ChartSkeleton height={height} />;

  const categoryAxis = { type: "category" as const, data: categories, axisLine: { lineStyle: { color: colors.border } } };
  const valueAxis = { type: "value" as const, splitLine: { lineStyle: { color: colors.border } } };

  const option = {
    color: colors.series,
    grid: { left: 8, right: 8, top: 24, bottom: 8, containLabel: true },
    tooltip: { trigger: "axis", axisPointer: { type: "shadow" } },
    legend: series.length > 1 ? { top: 0 } : undefined,
    xAxis: horizontal ? valueAxis : categoryAxis,
    yAxis: horizontal ? categoryAxis : valueAxis,
    series: series.map((s) => ({
      name: s.name,
      type: "bar",
      data: s.data,
      stack: stacked ? "total" : undefined,
      barMaxWidth: 32,
    })),
  };

  return <ReactECharts option={option} style={{ height }} notMerge />;
}
