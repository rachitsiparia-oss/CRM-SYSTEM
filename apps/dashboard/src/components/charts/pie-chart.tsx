"use client";

import ReactECharts from "echarts-for-react";

import { ChartSkeleton } from "./chart-skeleton";
import { useChartColors } from "./use-chart-colors";

export interface PieDatum {
  name: string;
  value: number;
}

export interface PieChartProps {
  data: PieDatum[];
  loading?: boolean;
  height?: number;
  /** Renders a donut (ring) instead of a filled pie. */
  donut?: boolean;
}

export function PieChart({ data, loading, height = 280, donut }: PieChartProps) {
  const colors = useChartColors();

  if (loading) return <ChartSkeleton height={height} />;

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
