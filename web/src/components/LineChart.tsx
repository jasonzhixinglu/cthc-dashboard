type ChartSeries = {
  name: string
  values: number[]
  color: string
}

type LineChartProps = {
  labels: string[]
  series: ChartSeries[]
}

const WIDTH = 760
const HEIGHT = 280
const PADDING = 28

export function LineChart({ labels, series }: LineChartProps) {
  const allValues = series.flatMap((item) => item.values).filter((value) => Number.isFinite(value))

  if (labels.length === 0 || allValues.length === 0) {
    return <div className="chart-empty">No chart data available.</div>
  }

  const minValue = Math.min(...allValues)
  const maxValue = Math.max(...allValues)
  const yRange = maxValue - minValue || 1
  const xStep = labels.length > 1 ? (WIDTH - PADDING * 2) / (labels.length - 1) : 0

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
          <path
            key={item.name}
            d={buildLinePath(item.values, minValue, yRange, xStep)}
            fill="none"
            stroke={item.color}
            strokeWidth="2.5"
            strokeLinejoin="round"
            strokeLinecap="round"
          />
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

  function buildLinePath(values: number[], localMin: number, localRange: number, localStep: number) {
    return values
      .map((value, index) => {
        const x = PADDING + index * localStep
        const y = HEIGHT - PADDING - ((value - localMin) / localRange) * (HEIGHT - PADDING * 2)
        return `${index === 0 ? 'M' : 'L'} ${x} ${y}`
      })
      .join(' ')
  }
}
