"use client";

import dynamic from "next/dynamic";

import { ChartSkeleton } from "./chart-skeleton";

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

// See bar-chart.tsx for why the real implementation is code-split out.
const PieChartImpl = dynamic(() => import("./pie-chart-impl").then((m) => m.PieChartImpl), {
  ssr: false,
  loading: () => <ChartSkeleton />,
});

export function PieChart(props: PieChartProps) {
  if (props.loading) return <ChartSkeleton height={props.height ?? 280} />;
  return <PieChartImpl {...props} />;
}
