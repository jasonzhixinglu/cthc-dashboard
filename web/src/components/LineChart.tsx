type Band = {
  lower: number[]
  upper: number[]
}

type ChartSeries = {
  name: string
  values: number[]
  color: string
  band68?: Band
  band95?: Band
}

type LineChartProps = {
  labels: string[]
  series: ChartSeries[]
}

const WIDTH = 760
const HEIGHT = 280
const PADDING = 28

export function LineChart({ labels, series }: LineChartProps) {
  const allValues = [
    ...series.flatMap((item) => item.values),
    ...series.flatMap((item) => item.band95?.lower ?? []),
    ...series.flatMap((item) => item.band95?.upper ?? []),
  ].filter((value) => Number.isFinite(value))

  if (labels.length === 0 || allValues.length === 0) {
    return <div className="chart-empty">No chart data available.</div>
  }

  const minValue = Math.min(...allValues)
  const maxValue = Math.max(...allValues)
  const yRange = maxValue - minValue || 1
  const xStep = labels.length > 1 ? (WIDTH - PADDING * 2) / (labels.length - 1) : 0

  function toY(value: number) {
    return HEIGHT - PADDING - ((value - minValue) / yRange) * (HEIGHT - PADDING * 2)
  }

  function buildLinePath(values: number[]) {
    return values
      .map((value, index) => {
        const x = PADDING + index * xStep
        return `${index === 0 ? 'M' : 'L'} ${x.toFixed(1)} ${toY(value).toFixed(1)}`
      })
      .join(' ')
  }

  function buildBandPath(lower: number[], upper: number[]) {
    if (lower.length === 0 || upper.length === 0) return ''
    const forward = upper
      .map((value, index) => {
        const x = PADDING + index * xStep
        return `${index === 0 ? 'M' : 'L'} ${x.toFixed(1)} ${toY(value).toFixed(1)}`
      })
      .join(' ')
    const backward = [...lower].reverse()
      .map((value, index) => {
        const x = PADDING + (lower.length - 1 - index) * xStep
        return `L ${x.toFixed(1)} ${toY(value).toFixed(1)}`
      })
      .join(' ')
    return `${forward} ${backward} Z`
  }

  return (
    <div className="chart-shell">
      <svg viewBox={`0 0 ${WIDTH} ${HEIGHT}`} className="chart-svg" role="img">
        <rect x="0" y="0" width={WIDTH} height={HEIGHT} className="chart-frame" />
        {[0, 0.5, 1].map((tick) => {
          const y = PADDING + (HEIGHT - PADDING * 2) * tick
          return (
            <g key={tick}>
              <line x1={PADDING} y1={y} x2={WIDTH - PADDING} y2={y} className="chart-grid" />
            </g>
          )
        })}
        {series.map((item) => (
          <g key={item.name}>
            {item.band95 ? (
              <path
                d={buildBandPath(item.band95.lower, item.band95.upper)}
                fill={item.color}
                fillOpacity={0.1}
                stroke="none"
              />
            ) : null}
            {item.band68 ? (
              <path
                d={buildBandPath(item.band68.lower, item.band68.upper)}
                fill={item.color}
                fillOpacity={0.22}
                stroke="none"
              />
            ) : null}
            <path
              d={buildLinePath(item.values)}
              fill="none"
              stroke={item.color}
              strokeWidth="2.5"
              strokeLinejoin="round"
              strokeLinecap="round"
            />
          </g>
        ))}
      </svg>
      <div className="chart-legend">
        {series.map((item) => (
          <span key={item.name} className="legend-item">
            <span className="legend-swatch" style={{ backgroundColor: item.color }} />
            {item.name}
          </span>
        ))}
      </div>
      <div className="chart-axis">
        <span>{labels[0]}</span>
        <span>{labels[labels.length - 1]}</span>
      </div>
    </div>
  )
}
