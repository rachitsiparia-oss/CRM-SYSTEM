import { LineChart, type ChartSeries } from "./line-chart";

export interface AreaChartProps {
  categories: string[];
  series: ChartSeries[];
  loading?: boolean;
  height?: number;
}

/** Thin named alias over LineChart with area fill on — kept as its own
 * component so callers reaching for "an area chart" find one directly. */
export function AreaChart(props: AreaChartProps) {
  return <LineChart {...props} area smooth />;
}
