import { useEffect, useState } from 'react'
import type { SeriesPayload } from '../types'
import { LineChart } from './LineChart'
import { Panel } from './Panel'

type VintageEntry = {
  id: string
  label: string
  sample_end: string
  data_path: string
}

type VintagesIndex = {
  vintages: VintageEntry[]
}

export function VintagesTab() {
  const base = import.meta.env.BASE_URL
  const [index, setIndex] = useState<VintagesIndex | null>(null)
  const [selectedId, setSelectedId] = useState<string | null>(null)
  const [vintageSeries, setVintageSeries] = useState<SeriesPayload | null>(null)
  const [loadingVintage, setLoadingVintage] = useState(false)

  useEffect(() => {
    fetch(`${base}data/vintages/index.json`)
      .then((r) => (r.ok ? r.json() : Promise.reject(r.status)))
      .then((d: VintagesIndex) => setIndex(d))
      .catch(() => setIndex({ vintages: [] }))
  }, [base])

  function handleView(entry: VintageEntry) {
    setSelectedId(entry.id)
    setLoadingVintage(true)
    setVintageSeries(null)
    fetch(`${base}data/${entry.data_path}series.json`)
      .then((r) => r.json())
      .then((d: SeriesPayload) => {
        setVintageSeries(d)
        setLoadingVintage(false)
      })
      .catch(() => setLoadingVintage(false))
  }

  function handleBack() {
    setSelectedId(null)
    setVintageSeries(null)
  }

  // ── Vintage detail view ──────────────────────────────────────
  if (selectedId) {
    const entry = index?.vintages.find((v) => v.id === selectedId)
    const subtitle = entry ? `Vintage: ${entry.label} · Data through ${entry.sample_end}` : selectedId

    return (
      <section className="vintage-view">
        <button type="button" className="vintage-back" onClick={handleBack}>
          ← Back to current
        </button>
        {loadingVintage ? (
          <p className="vintage-loading">Loading vintage…</p>
        ) : vintageSeries ? (
          <>
            <Panel title="Output Gap" subtitle={subtitle}>
              <LineChart
                labels={vintageSeries.dates}
                series={[
                  {
                    name: 'Output Gap',
                    values: vintageSeries.output_gap,
                    color: 'var(--series-gap)',
                  },
                ]}
                sourceNote="Source: Authors' calculations. Posterior mean estimate."
              />
            </Panel>
            <Panel title="Potential Growth" subtitle={subtitle}>
              <LineChart
                labels={vintageSeries.dates}
                series={[
                  {
                    name: 'Potential Growth',
                    values: vintageSeries.potential_growth,
                    color: 'var(--series-growth)',
                  },
                ]}
                sourceNote="Source: Authors' calculations. Posterior mean estimate."
              />
            </Panel>
          </>
        ) : (
          <p className="vintage-loading">Could not load vintage data.</p>
        )}
      </section>
    )
  }

  // ── Vintage catalog ──────────────────────────────────────────
  const vintages = index ? [...index.vintages].reverse() : []

  return (
    <section className="vintage-catalog">
      <header className="vintage-catalog-header">
        <h2 className="vintage-catalog-title">Model Vintages</h2>
        <p className="vintage-catalog-subtitle">
          Each vintage reflects estimates as of the data release date. Select a
          vintage to view its estimates.
        </p>
      </header>
      {!index ? (
        <p className="vintage-loading">Loading vintages…</p>
      ) : vintages.length === 0 ? (
        <p className="vintage-loading">No vintages available.</p>
      ) : (
        <ul className="vintage-list">
          {vintages.map((entry) => (
            <li key={entry.id} className="vintage-item">
              <div className="vintage-item-info">
                <span className="vintage-item-label">{entry.label}</span>
                <span className="vintage-item-sample">Data through {entry.sample_end}</span>
              </div>
              <button
                type="button"
                className="vintage-item-view"
                onClick={() => handleView(entry)}
              >
                View
              </button>
            </li>
          ))}
        </ul>
      )}
    </section>
  )
}
