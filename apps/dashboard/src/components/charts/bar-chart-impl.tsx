"use client";

import ReactECharts from "echarts-for-react";

import { useChartColors } from "./use-chart-colors";
import type { BarChartProps } from "./bar-chart";

export function BarChartImpl({
  categories,
  series,
  height = 280,
  horizontal,
  stacked,
  highlightIndex,
}: BarChartProps) {
  const colors = useChartColors();

  const categoryAxis = { type: "category" as const, data: categories, axisLine: { lineStyle: { color: colors.border } } };
  const valueAxis = { type: "value" as const, splitLine: { lineStyle: { color: colors.border } } };

  const option = {
    color: colors.series,
    grid: { left: 8, right: 8, top: 24, bottom: 8, containLabel: true },
    tooltip: {
      trigger: "axis",
      axisPointer: { type: "shadow" },
      backgroundColor: "#18181b",
      borderWidth: 0,
      borderRadius: 8,
      textStyle: { color: "#fafafa" },
      padding: [8, 12],
    },
    legend: series.length > 1 ? { top: 0 } : undefined,
    xAxis: horizontal ? valueAxis : categoryAxis,
    yAxis: horizontal ? categoryAxis : valueAxis,
    series: series.map((s, seriesIndex) => ({
      name: s.name,
      type: "bar",
      data:
        seriesIndex === 0 && highlightIndex !== undefined
          ? s.data.map((value, index) => ({
              value,
              itemStyle:
                index === highlightIndex
                  ? { color: colors.brandYellow, borderRadius: [4, 4, 0, 0] }
                  : { color: colors.brandPrimary, opacity: 0.18, borderRadius: [4, 4, 0, 0] },
            }))
          : s.data,
      stack: stacked ? "total" : undefined,
      barMaxWidth: 32,
      itemStyle: seriesIndex === 0 && highlightIndex !== undefined ? undefined : { borderRadius: [4, 4, 0, 0] },
    })),
  };

  return <ReactECharts option={option} style={{ height }} notMerge />;
}
