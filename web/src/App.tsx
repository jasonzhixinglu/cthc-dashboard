import { useEffect, useMemo, useState } from 'react'
import './App.css'
import { LineChart } from './components/LineChart'
import { MetricCard } from './components/MetricCard'
import { NavTabs, type PageKey } from './components/NavTabs'
import { Panel } from './components/Panel'
import { SectorDecompositionChart } from './components/SectorDecompositionChart'
import { loadDashboardData } from './lib/data'
import type { DashboardData } from './types'

const PAGE_LABELS: Record<PageKey, string> = {
  overview: 'Overview',
  explorer: 'Explorer',
  scenarios: 'Scenarios',
  methodology: 'Methodology',
}

function App() {
  const [page, setPage] = useState<PageKey>('overview')
  const [data, setData] = useState<DashboardData | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [selectedSector, setSelectedSector] = useState<string>('')

  useEffect(() => {
    let active = true

    loadDashboardData()
      .then((payload) => {
        if (!active) {
          return
        }
        setData(payload)
        setSelectedSector(payload.sectors.sector_names[0] ?? '')
      })
      .catch((loadError: unknown) => {
        if (!active) {
          return
        }
        setError(loadError instanceof Error ? loadError.message : 'Failed to load dashboard data.')
        setData(createEmptyDashboardData())
        setSelectedSector('')
      })

    return () => {
      active = false
    }
  }, [])

  const scenarios = useMemo(() => {
    if (!data) {
      return []
    }
    return Array.from(
      new Set([
        data.summary.scenario,
        data.series.scenario,
        data.sectors.scenario,
      ]),
    )
  }, [data])

  const sectorContribution = useMemo(() => {
    if (!data || !selectedSector) {
      return []
    }
    const shares = data.sectors.shares[selectedSector] ?? []
    return shares.map((share, index) => share * (data.series.output_gap[index] ?? 0))
  }, [data, selectedSector])

  const sectorTheta = useMemo(() => {
    if (!data || !selectedSector) {
      return []
    }
    return data.sectors.theta[selectedSector] ?? []
  }, [data, selectedSector])

  const summaryReady = Boolean(
    data &&
      (data.summary.latest_output_gap !== null ||
        data.summary.latest_potential_growth !== null),
  )
  const seriesReady = Boolean(
    data &&
      data.series.dates.length > 0 &&
      data.series.dates[0] !== 'Unavailable' &&
      (data.series.output_gap.length > 0 || data.series.potential_growth.length > 0),
  )
  const sectorsReady = Boolean(
    data &&
      data.sectors.sector_names.length > 0 &&
      data.sectors.dates.length > 0 &&
      data.sectors.dates[0] !== 'Unavailable',
  )

  return (
    <div className="app-shell">
      <header className="masthead">
        <div>
          <p className="eyebrow">CTHC Dashboard</p>
          <h1>Fixed-Parameter Replication</h1>
        </div>
        <div className="meta-block">
          <span>{data?.summary.scenario ?? 'Loading scenario'}</span>
          <span>{data?.summary.last_updated ?? 'Loading date'}</span>
        </div>
      </header>

      <NavTabs page={page} labels={PAGE_LABELS} onSelect={setPage} />

      {!data && !error ? <Panel title="Loading">Reading model output from `public/data`.</Panel> : null}
      {error ? (
        <Panel title="Data Error">
          {error}. Showing empty dashboard placeholders until model output is generated.
        </Panel>
      ) : null}

      {data ? (
        <main className="page-grid">
          {page === 'overview' ? (
            <>
              <section className="hero-grid">
                {summaryReady ? (
                  <>
                    <MetricCard
                      label="Latest Output Gap"
                      value={formatNumber(data.summary.latest_output_gap)}
                      note={`Sample end ${data.summary.sample_end ?? 'n/a'}`}
                    />
                    <MetricCard
                      label="Latest Potential Growth"
                      value={formatNumber(data.summary.latest_potential_growth)}
                      note={`Scenario ${data.summary.scenario}`}
                    />
                  </>
                ) : (
                  <>
                    <EmptyStateCard
                      title="Summary data missing"
                      message="`summary.json` is missing or does not contain current output-gap values yet."
                    />
                    <EmptyStateCard
                      title="Summary data missing"
                      message="`summary.json` is missing or does not contain current potential-growth values yet."
                    />
                  </>
                )}
              </section>

              <section className="two-column">
                <Panel
                  title="Series Snapshot"
                  subtitle="Smoothed estimates from the fixed-parameter state-space run."
                >
                  {seriesReady ? (
                    <LineChart
                      labels={data.series.dates}
                      series={[
                        {
                          name: 'Output Gap',
                          values: data.series.output_gap,
                          color: 'var(--series-gap)',
                        },
                        {
                          name: 'Potential Growth',
                          values: data.series.potential_growth,
                          color: 'var(--series-growth)',
                        },
                      ]}
                    />
                  ) : (
                    <EmptyStateCard
                      title="Series data missing"
                      message="`series.json` has not been generated yet, so no output-gap or growth chart is available."
                    />
                  )}
                </Panel>
                <Panel
                  title="Replication Scope"
                  subtitle="This dashboard reflects the constrained, fixed-parameter replication only."
                >
                  <p>
                    Parameters are loaded from the baseline YAML, the state-space system is
                    constructed deterministically, and the site reads the exported JSON payloads
                    directly from `public/data`.
                  </p>
                </Panel>
              </section>
            </>
          ) : null}

          {page === 'explorer' ? (
            <>
              <section className="two-column">
                <Panel title="Output Gap">
                  {seriesReady ? (
                    <LineChart
                      labels={data.series.dates}
                      series={[
                        {
                          name: 'Output Gap',
                          values: data.series.output_gap,
                          color: 'var(--series-gap)',
                        },
                      ]}
                    />
                  ) : (
                    <EmptyStateCard
                      title="Series data missing"
                      message="`series.json` does not contain output-gap observations yet."
                    />
                  )}
                </Panel>
                <Panel title="Potential Growth">
                  {seriesReady ? (
                    <LineChart
                      labels={data.series.dates}
                      series={[
                        {
                          name: 'Potential Growth',
                          values: data.series.potential_growth,
                          color: 'var(--series-growth)',
                        },
                      ]}
                    />
                  ) : (
                    <EmptyStateCard
                      title="Series data missing"
                      message="`series.json` does not contain potential-growth observations yet."
                    />
                  )}
                </Panel>
              </section>

              <Panel
                title="Sector Decomposition"
                subtitle="Selected sector contribution to the output gap and its latent sector component."
                actions={
                  <label className="selector">
                    <span>Sector</span>
                    <select
                      value={selectedSector}
                      onChange={(event) => setSelectedSector(event.target.value)}
                      disabled={!sectorsReady}
                    >
                      {data.sectors.sector_names.map((sectorName) => (
                        <option key={sectorName} value={sectorName}>
                          {formatSectorLabel(sectorName)}
                        </option>
                      ))}
                    </select>
                  </label>
                }
              >
                {sectorsReady && seriesReady && selectedSector ? (
                  <SectorDecompositionChart
                    labels={data.series.dates}
                    contribution={sectorContribution}
                    theta={sectorTheta}
                    sectorName={selectedSector}
                  />
                ) : (
                  <EmptyStateCard
                    title="Sector data missing"
                    message="`sectors.json` has not been generated yet, so sector decomposition is unavailable."
                  />
                )}
              </Panel>
            </>
          ) : null}

          {page === 'scenarios' ? (
            <Panel
              title="Available Scenarios"
              subtitle="Scenarios currently discoverable from the exported JSON payloads."
            >
              {scenarios.length > 0 ? (
                <div className="scenario-list">
                  {scenarios.map((scenario) => (
                    <article key={scenario} className="scenario-card">
                      <h3>{scenario}</h3>
                      <p>Last updated {data.summary.last_updated}</p>
                      <p>Sample end {data.summary.sample_end ?? 'n/a'}</p>
                    </article>
                  ))}
                </div>
              ) : (
                <EmptyStateCard
                  title="Scenario data missing"
                  message="No scenario metadata is available yet. Generate model output to populate this page."
                />
              )}
            </Panel>
          ) : null}

          {page === 'methodology' ? (
            <Panel
              title="Methodology"
              subtitle="What is in scope for this replication and what is intentionally excluded."
            >
              <div className="methodology">
                <p>
                  This site presents a fixed-parameter replication of the CTHC model using a
                  linear Gaussian state-space system with Kalman filtering and Rauch-Tung-Striebel
                  smoothing.
                </p>
                <p>
                  The implementation includes deterministic matrix construction from the baseline
                  configuration, missing-data handling through masked observations, and frontend
                  payload export for summary, series, and sector views.
                </p>
                <p>
                  Bayesian parameter estimation, Monte Carlo simulation, and broader model
                  extensions are out of scope for this replication.
                </p>
              </div>
            </Panel>
          ) : null}
        </main>
      ) : null}
    </div>
  )
}

function EmptyStateCard({ title, message }: { title: string; message: string }) {
  return (
    <article className="empty-state-card">
      <h3>{title}</h3>
      <p>{message}</p>
    </article>
  )
}

function createEmptyDashboardData(): DashboardData {
  return {
    summary: {
      last_updated: 'Unavailable',
      scenario: 'baseline',
      latest_output_gap: null,
      latest_potential_growth: null,
      sample_end: null,
    },
    series: {
      last_updated: 'Unavailable',
      scenario: 'baseline',
      dates: [],
      output_gap: [],
      potential_growth: [],
      gdp_observed: [],
      gdp_trend: [],
    },
    sectors: {
      last_updated: 'Unavailable',
      scenario: 'baseline',
      dates: [],
      sector_names: [],
      shares: {},
      theta: {},
    },
  }
}

function formatNumber(value: number | null): string {
  if (value === null || Number.isNaN(value)) {
    return 'n/a'
  }
  return value.toFixed(1)
}

function formatSectorLabel(value: string): string {
  return value
    .split('_')
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
    .join(' ')
}

export default App
