import { LineChart } from './LineChart'

const SECTOR_COLORS: Record<string, string> = {
  imports: '#2980b9',
  electricity: '#27ae60',
  industrial_va: '#8e44ad',
  retail_sales: '#e67e22',
  fixed_asset_investment: '#e74c3c',
}
const DEFAULT_SECTOR_COLOR = '#2980b9'

type SectorDecompositionChartProps = {
  labels: string[]
  sectorName: string
  observed?: Array<number | null>
  trend?: number[]
  cycleSector?: number[]
  cycleAgg?: number[]
}

export function SectorDecompositionChart({
  labels,
  sectorName,
  observed,
  trend,
  cycleSector,
  cycleAgg,
}: SectorDecompositionChartProps) {
  const label = formatSectorLabel(sectorName)
  const sectorColor = SECTOR_COLORS[sectorName] ?? DEFAULT_SECTOR_COLOR

  const trendSeries = []
  if (observed) {
    trendSeries.push({
      name: 'Observed',
      values: observed,
      color: '#999999',
      dashed: true,
    })
  }
  if (trend) {
    trendSeries.push({
      name: 'Trend',
      values: trend,
      color: '#1a5276',
    })
  }

  const cycleSeries = []
  if (cycleAgg) {
    cycleSeries.push({
      name: 'Output gap',
      values: cycleAgg,
      color: '#666666',
      dashed: true,
    })
  }
  if (cycleSector) {
    cycleSeries.push({
      name: `${label} contribution`,
      values: cycleSector,
      color: sectorColor,
    })
  }

  return (
    <>
      {trendSeries.length > 0 ? (
        <LineChart
          labels={labels}
          series={trendSeries}
          yAxisLabel="Log level"
          yFormatter={(v) => v.toFixed(2)}
          sourceNote="Source: Authors' calculations. Trend = μt + θi (aggregate trend + sector drift)."
        />
      ) : null}
      {cycleSeries.length > 0 ? (
        <LineChart
          labels={labels}
          series={cycleSeries}
          sourceNote="Source: Authors' calculations. Sector cycle = λi × ct. Output gap = ct. Both in percent."
        />
      ) : null}
    </>
  )
}

function formatSectorLabel(value: string): string {
  return value
    .split('_')
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
    .join(' ')
}
