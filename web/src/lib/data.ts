import type { DashboardData, SectorsPayload, SeriesPayload, SummaryPayload } from '../types'

export async function loadDashboardData(): Promise<DashboardData> {
  const base = import.meta.env.BASE_URL
  const [summary, series, sectors] = await Promise.all([
    loadJson<SummaryPayload>(`${base}data/summary.json`),
    loadJson<SeriesPayload>(`${base}data/series.json`),
    loadJson<SectorsPayload>(`${base}data/sectors.json`),
  ])

  return {
    summary: normalizeSummary(summary),
    series: normalizeSeries(series),
    sectors: normalizeSectors(sectors),
  }
}

async function loadJson<T>(url: string): Promise<T> {
  const response = await fetch(url)
  if (!response.ok) {
    throw new Error(`Failed to load ${url}: ${response.status}`)
  }
  return (await response.json()) as T
}

function normalizeSummary(payload: SummaryPayload): SummaryPayload {
  return {
    last_updated: readString(payload.last_updated) ?? 'Unavailable',
    scenario: readString(payload.scenario) ?? 'baseline',
    latest_output_gap: readNumber(payload.latest_output_gap),
    latest_potential_growth: readNumber(payload.latest_potential_growth),
    sample_end: readString(payload.sample_end) ?? null,
  }
}

function normalizeSeries(payload: SeriesPayload): SeriesPayload {
  const canonicalDates = ensureStringArray(readStringArray(payload.dates) ?? [])
  const seriesLength = canonicalDates.length

  function optionalBand(raw: number[] | undefined): number[] | undefined {
    if (!raw) return undefined
    return ensureNumberArray(readNumberArray(raw) ?? [], seriesLength)
  }

  return {
    last_updated: readString(payload.last_updated) ?? 'Unavailable',
    scenario: readString(payload.scenario) ?? 'baseline',
    dates: canonicalDates,
    output_gap:
      ensureNumberArray(
        readNumberArray(payload.output_gap) ?? [],
        seriesLength,
      ),
    output_gap_p16: optionalBand(payload.output_gap_p16),
    output_gap_p84: optionalBand(payload.output_gap_p84),
    output_gap_p025: optionalBand(payload.output_gap_p025),
    output_gap_p975: optionalBand(payload.output_gap_p975),
    potential_growth:
      ensureNumberArray(
        readNumberArray(payload.potential_growth) ?? [],
        seriesLength,
      ),
    potential_growth_p16: optionalBand(payload.potential_growth_p16),
    potential_growth_p84: optionalBand(payload.potential_growth_p84),
    potential_growth_p025: optionalBand(payload.potential_growth_p025),
    potential_growth_p975: optionalBand(payload.potential_growth_p975),
    gdp_observed:
      ensureNullableNumberArray(
        readNullableNumberArray(payload.gdp_observed) ??
          new Array(seriesLength).fill(null),
        seriesLength,
      ),
    gdp_trend:
      ensureNumberArray(
        readNumberArray(payload.gdp_trend) ?? [],
        seriesLength,
      ),
  }
}

function normalizeSectors(payload: SectorsPayload): SectorsPayload {
  const sectorNames = readStringArray(payload.sector_names) ?? []
  const canonicalDates = ensureStringArray(readStringArray(payload.dates) ?? [])
  const seriesLength = canonicalDates.length

  return {
    last_updated: readString(payload.last_updated) ?? 'Unavailable',
    scenario: readString(payload.scenario) ?? 'baseline',
    dates: canonicalDates,
    sector_names: sectorNames,
    shares:
      ensureSeriesMap(
        asNumberArrayMap(payload.shares, sectorNames) ??
          Object.fromEntries(sectorNames.map((sectorName) => [sectorName, []])),
        sectorNames,
        seriesLength,
      ),
    theta: ensureSeriesMap(
      asNumberArrayMap(payload.theta, sectorNames) ??
        Object.fromEntries(sectorNames.map((sectorName) => [sectorName, []])),
      sectorNames,
      seriesLength,
    ),
  }
}

function readString(value: unknown): string | null {
  return typeof value === 'string' ? value : null
}

function readNumber(value: unknown): number | null {
  return typeof value === 'number' && Number.isFinite(value) ? value : null
}

function readStringArray(value: unknown): string[] | null {
  return Array.isArray(value) ? value.map((item) => stringifyValue(item) ?? '') : null
}

function readNumberArray(value: unknown): number[] | null {
  if (!Array.isArray(value)) {
    return null
  }
  return value.map((item) => readNumber(item) ?? 0)
}

function readNullableNumberArray(value: unknown): Array<number | null> | null {
  if (!Array.isArray(value)) {
    return null
  }
  return value.map((item) => readNumber(item))
}

function asNumberArrayMap(
  value: unknown,
  keys: string[],
): Record<string, number[]> | null {
  if (value === null || typeof value !== 'object') {
    return null
  }
  const record = value as Record<string, unknown>
  return Object.fromEntries(
    keys.map((key) => [key, readNumberArray(record[key]) ?? []]),
  )
}

function ensureStringArray(values: string[]): string[] {
  return values.length > 0 ? values : ['Unavailable']
}

function ensureNumberArray(values: number[], length: number): number[] {
  return Array.from({ length }, (_, index) => values[index] ?? 0)
}

function ensureNullableNumberArray(values: Array<number | null>, length: number): Array<number | null> {
  return Array.from({ length }, (_, index) => values[index] ?? null)
}

function ensureSeriesMap(
  values: Record<string, number[]>,
  keys: string[],
  length: number,
): Record<string, number[]> {
  return Object.fromEntries(
    keys.map((key) => [key, ensureNumberArray(values[key] ?? [], length)]),
  )
}

function stringifyValue(value: unknown): string | null {
  if (typeof value === 'string') {
    return value
  }
  if (typeof value === 'number' || typeof value === 'boolean') {
    return String(value)
  }
  return null
}
