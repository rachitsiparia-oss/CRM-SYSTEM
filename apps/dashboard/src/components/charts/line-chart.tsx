"use client";

import dynamic from "next/dynamic";

import { ChartSkeleton } from "./chart-skeleton";

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

// See bar-chart.tsx for why the real implementation is code-split out.
const LineChartImpl = dynamic(() => import("./line-chart-impl").then((m) => m.LineChartImpl), {
  ssr: false,
  loading: () => <ChartSkeleton />,
});

export function LineChart(props: LineChartProps) {
  if (props.loading) return <ChartSkeleton height={props.height ?? 280} />;
  return <LineChartImpl {...props} />;
}
