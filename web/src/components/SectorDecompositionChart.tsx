import { LineChart } from './LineChart'

type SectorDecompositionChartProps = {
  labels: string[]
  contribution: number[]
  theta: number[]
  sectorName: string
}

export function SectorDecompositionChart({
  labels,
  contribution,
  theta,
  sectorName,
}: SectorDecompositionChartProps) {
  return (
    <LineChart
      labels={labels}
      series={[
        {
          name: `${formatSectorLabel(sectorName)} contribution`,
          values: contribution,
          color: 'var(--series-sector)',
        },
        {
          name: `${formatSectorLabel(sectorName)} theta`,
          values: theta,
          color: 'var(--series-theta)',
        },
      ]}
    />
  )
}

function formatSectorLabel(value: string): string {
  return value
    .split('_')
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
    .join(' ')
}
