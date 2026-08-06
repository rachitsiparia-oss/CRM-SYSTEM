"use client";

import ReactECharts from "echarts-for-react";

import { useChartColors } from "./use-chart-colors";
import type { PieChartProps } from "./pie-chart";

export function PieChartImpl({ data, height = 280, donut }: PieChartProps) {
  const colors = useChartColors();

  const option = {
    color: colors.series,
    tooltip: { trigger: "item" },
    legend: { bottom: 0 },
    series: [
      {
        type: "pie",
        radius: donut ? ["45%", "70%"] : "70%",
        avoidLabelOverlap: true,
        itemStyle: { borderRadius: donut ? 4 : 0, borderColor: colors.border || "transparent", borderWidth: 1 },
        label: { show: true, formatter: "{b}: {d}%" },
        data,
      },
    ],
  };

  return <ReactECharts option={option} style={{ height }} notMerge />;
}
