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
  sourceNote?: string
}

const WIDTH = 860
const HEIGHT = 260
const PAD = { top: 14, right: 16, bottom: 20, left: 56 }

const innerW = WIDTH - PAD.left - PAD.right
const innerH = HEIGHT - PAD.top - PAD.bottom

const N_TICKS = 5

function niceTickStep(range: number, n: number): number {
  const raw = range / (n - 1)
  const mag = Math.pow(10, Math.floor(Math.log10(raw)))
  for (const mult of [1, 2, 2.5, 5, 10]) {
    if (mag * mult >= raw) return mag * mult
  }
  return mag * 10
}

export function LineChart({ labels, series, sourceNote }: LineChartProps) {
  const allValues = [
    ...series.flatMap((item) => item.values),
    ...series.flatMap((item) => item.band95?.lower ?? []),
    ...series.flatMap((item) => item.band95?.upper ?? []),
  ].filter((value) => Number.isFinite(value))

  if (labels.length === 0 || allValues.length === 0) {
    return <div className="chart-empty">No chart data available.</div>
  }

  const dataMin = Math.min(...allValues)
  const dataMax = Math.max(...allValues)

  const step = niceTickStep(dataMax - dataMin || 1, N_TICKS)
  const axisMin = Math.floor(dataMin / step) * step
  const axisMax = Math.ceil(dataMax / step) * step
  const axisRange = axisMax - axisMin || 1

  const ticks: number[] = []
  for (let t = axisMin; t <= axisMax + step * 0.001; t += step) {
    ticks.push(parseFloat(t.toFixed(10)))
  }

  const xStep = labels.length > 1 ? innerW / (labels.length - 1) : 0

  function toX(index: number) {
    return PAD.left + index * xStep
  }

  function toY(value: number) {
    return PAD.top + innerH - ((value - axisMin) / axisRange) * innerH
  }

  // Integer percent label, no sign prefix, no decimal
  function formatTick(value: number): string {
    return String(Math.round(value * 100))
  }

  function buildLinePath(values: number[]) {
    return values
      .map((value, index) => {
        const x = toX(index)
        return `${index === 0 ? 'M' : 'L'} ${x.toFixed(1)} ${toY(value).toFixed(1)}`
      })
      .join(' ')
  }

  function buildBandPath(lower: number[], upper: number[]) {
    if (lower.length === 0 || upper.length === 0) return ''
    const forward = upper
      .map((value, index) => {
        const x = toX(index)
        return `${index === 0 ? 'M' : 'L'} ${x.toFixed(1)} ${toY(value).toFixed(1)}`
      })
      .join(' ')
    const backward = [...lower]
      .reverse()
      .map((value, index) => {
        const x = toX(lower.length - 1 - index)
        return `L ${x.toFixed(1)} ${toY(value).toFixed(1)}`
      })
      .join(' ')
    return `${forward} ${backward} Z`
  }

  // X-axis: first, last, and up to 3 evenly-spaced intermediate labels
  const labelIndices = new Set<number>([0, labels.length - 1])
  const step4 = Math.floor((labels.length - 1) / 4)
  for (let i = 1; i <= 3; i++) {
    const idx = step4 * i
    if (idx > 0 && idx < labels.length - 1) labelIndices.add(idx)
  }

  const zeroInRange = axisMin <= 0 && axisMax >= 0
  const centerY = PAD.top + innerH / 2

  const defaultSource =
    'Source: Authors\u2019 calculations. Shaded bands show 68% and 95% posterior credible intervals.'

  return (
    <div className="chart-shell">
      <svg viewBox={`0 0 ${WIDTH} ${HEIGHT}`} className="chart-svg" role="img">
        <rect x="0" y="0" width={WIDTH} height={HEIGHT} className="chart-frame" />

        {/* "Percent" rotated Y-axis label */}
        <text
          x={10}
          y={centerY}
          textAnchor="middle"
          dominantBaseline="middle"
          fontSize="10"
          fill="#9a9a9a"
          transform={`rotate(-90, 10, ${centerY})`}
        >
          Percent
        </text>

        {/* Horizontal grid lines + Y-axis tick labels */}
        {ticks.map((tick) => {
          const y = toY(tick)
          if (y < PAD.top - 4 || y > PAD.top + innerH + 4) return null
          return (
            <g key={tick}>
              <line
                x1={PAD.left}
                y1={y}
                x2={PAD.left + innerW}
                y2={y}
                className="chart-grid"
                strokeDasharray="2,3"
              />
              <text
                x={PAD.left - 5}
                y={y}
                textAnchor="end"
                dominantBaseline="middle"
                fontSize="10"
                fill="#9a9a9a"
              >
                {formatTick(tick)}
              </text>
            </g>
          )
        })}

        {/* Zero line */}
        {zeroInRange && Math.abs(toY(0) - toY(axisMin)) > 2 && Math.abs(toY(0) - toY(axisMax)) > 2 ? (
          <line
            x1={PAD.left}
            y1={toY(0)}
            x2={PAD.left + innerW}
            y2={toY(0)}
            className="chart-zero"
          />
        ) : null}

        {/* Bands and lines */}
        {series.map((item) => (
          <g key={item.name}>
            {item.band95 ? (
              <path
                d={buildBandPath(item.band95.lower, item.band95.upper)}
                fill="#808080"
                fillOpacity={0.10}
                stroke="none"
              />
            ) : null}
            {item.band68 ? (
              <path
                d={buildBandPath(item.band68.lower, item.band68.upper)}
                fill="#808080"
                fillOpacity={0.20}
                stroke="none"
              />
            ) : null}
            <path
              d={buildLinePath(item.values)}
              fill="none"
              stroke={item.color}
              strokeWidth="2"
              strokeLinejoin="round"
              strokeLinecap="round"
            />
          </g>
        ))}

        {/* X-axis date labels */}
        {Array.from(labelIndices).map((idx) => (
          <text
            key={idx}
            x={toX(idx)}
            y={PAD.top + innerH + 14}
            textAnchor={idx === 0 ? 'start' : idx === labels.length - 1 ? 'end' : 'middle'}
            fontSize="10"
            fill="#9a9a9a"
          >
            {labels[idx]}
          </text>
        ))}
      </svg>

      {/* Legend */}
      <div className="chart-legend">
        {series.map((item) => (
          <span key={item.name} className="legend-item">
            <span className="legend-swatch" style={{ backgroundColor: item.color }} />
            {item.name}
          </span>
        ))}
      </div>

      {/* Source note */}
      <p className="chart-source">{sourceNote ?? defaultSource}</p>
    </div>
  )
}
