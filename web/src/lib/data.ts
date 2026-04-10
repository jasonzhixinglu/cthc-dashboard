import type { DashboardData, SectorsPayload, SeriesPayload, SummaryPayload } from '../types'

export async function loadDashboardData(): Promise<DashboardData> {
  const base = import.meta.env.BASE_URL
  const [summary, series, sectors] = await Promise.all([
    loadJson<SummaryPayload>(`${base}data/summary.json`),
    loadJson<SeriesPayload>(`${base}data/series.json`),
    loadJson<SectorsPayload>(`${base}data/sectors.json`),
  ])

  const normalizedSummary = normalizeSummary(summary)
  const displayStart = normalizedSummary.display_start
  const displayEnd = normalizedSummary.display_end

  let normalizedSeries = normalizeSeries(series)
  let normalizedSectors = normalizeSectors(sectors)

  if (displayStart) {
    normalizedSeries = clipSeriesFrom(normalizedSeries, displayStart)
    normalizedSectors = clipSectorsFrom(normalizedSectors, displayStart)
  }

  if (displayEnd) {
    normalizedSeries = clipSeriesTo(normalizedSeries, displayEnd)
    normalizedSectors = clipSectorsTo(normalizedSectors, displayEnd)
  }

  return {
    summary: normalizedSummary,
    series: normalizedSeries,
    sectors: normalizedSectors,
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
    display_start: readString(payload.display_start) ?? undefined,
    display_end: readString(payload.display_end) ?? undefined,
    latest_output_gap: readNumber(payload.latest_output_gap),
    latest_potential_growth: readNumber(payload.latest_potential_growth),
    sample_end: readString(payload.sample_end) ?? null,
  }
}

function clipSeriesFrom(series: SeriesPayload, startDate: string): SeriesPayload {
  const idx = series.dates.findIndex((d) => d >= startDate)
  if (idx <= 0) return series
  const sl = <T>(arr: T[]): T[] => arr.slice(idx)
  const slOpt = <T>(arr: T[] | undefined): T[] | undefined => arr ? arr.slice(idx) : undefined
  return {
    ...series,
    dates: sl(series.dates),
    output_gap: sl(series.output_gap),
    output_gap_p16: slOpt(series.output_gap_p16),
    output_gap_p84: slOpt(series.output_gap_p84),
    output_gap_p025: slOpt(series.output_gap_p025),
    output_gap_p975: slOpt(series.output_gap_p975),
    potential_growth: sl(series.potential_growth),
    potential_growth_p16: slOpt(series.potential_growth_p16),
    potential_growth_p84: slOpt(series.potential_growth_p84),
    potential_growth_p025: slOpt(series.potential_growth_p025),
    potential_growth_p975: slOpt(series.potential_growth_p975),
    gdp_observed: sl(series.gdp_observed),
    gdp_trend: sl(series.gdp_trend),
    gdp_growth_qoq: slOpt(series.gdp_growth_qoq),
    gdp_growth_yoy: slOpt(series.gdp_growth_yoy),
  }
}

function clipSectorsFrom(sectors: SectorsPayload, startDate: string): SectorsPayload {
  const idx = sectors.dates.findIndex((d) => d >= startDate)
  if (idx <= 0) return sectors
  const sl = <T>(arr: T[]): T[] => arr.slice(idx)
  const slMap = (map: Record<string, unknown[]> | undefined) =>
    map ? Object.fromEntries(Object.entries(map).map(([k, v]) => [k, sl(v)])) : undefined
  return {
    ...sectors,
    dates: sl(sectors.dates),
    shares: Object.fromEntries(Object.entries(sectors.shares).map(([k, v]) => [k, sl(v)])),
    theta: Object.fromEntries(Object.entries(sectors.theta).map(([k, v]) => [k, sl(v)])),
    cycle_agg: sectors.cycle_agg ? sl(sectors.cycle_agg) : undefined,
    observed: slMap(sectors.observed) as Record<string, Array<number | null>> | undefined,
    trend: slMap(sectors.trend) as Record<string, number[]> | undefined,
    cycle_sector: slMap(sectors.cycle_sector) as Record<string, number[]> | undefined,
    theta_p16: slMap(sectors.theta_p16) as Record<string, number[]> | undefined,
    theta_p84: slMap(sectors.theta_p84) as Record<string, number[]> | undefined,
    theta_p025: slMap(sectors.theta_p025) as Record<string, number[]> | undefined,
    theta_p975: slMap(sectors.theta_p975) as Record<string, number[]> | undefined,
  }
}

function clipSeriesTo(series: SeriesPayload, endDate: string): SeriesPayload {
  const idx = series.dates.findLastIndex((d) => d <= endDate)
  if (idx < 0 || idx === series.dates.length - 1) return series
  const sl = <T>(arr: T[]): T[] => arr.slice(0, idx + 1)
  const slOpt = <T>(arr: T[] | undefined): T[] | undefined => arr ? arr.slice(0, idx + 1) : undefined
  return {
    ...series,
    dates: sl(series.dates),
    output_gap: sl(series.output_gap),
    output_gap_p16: slOpt(series.output_gap_p16),
    output_gap_p84: slOpt(series.output_gap_p84),
    output_gap_p025: slOpt(series.output_gap_p025),
    output_gap_p975: slOpt(series.output_gap_p975),
    potential_growth: sl(series.potential_growth),
    potential_growth_p16: slOpt(series.potential_growth_p16),
    potential_growth_p84: slOpt(series.potential_growth_p84),
    potential_growth_p025: slOpt(series.potential_growth_p025),
    potential_growth_p975: slOpt(series.potential_growth_p975),
    gdp_observed: sl(series.gdp_observed),
    gdp_trend: sl(series.gdp_trend),
    gdp_growth_qoq: slOpt(series.gdp_growth_qoq),
    gdp_growth_yoy: slOpt(series.gdp_growth_yoy),
  }
}

function clipSectorsTo(sectors: SectorsPayload, endDate: string): SectorsPayload {
  const idx = sectors.dates.findLastIndex((d) => d <= endDate)
  if (idx < 0 || idx === sectors.dates.length - 1) return sectors
  const sl = <T>(arr: T[]): T[] => arr.slice(0, idx + 1)
  const slMap = (map: Record<string, unknown[]> | undefined) =>
    map ? Object.fromEntries(Object.entries(map).map(([k, v]) => [k, sl(v)])) : undefined
  return {
    ...sectors,
    dates: sl(sectors.dates),
    shares: Object.fromEntries(Object.entries(sectors.shares).map(([k, v]) => [k, sl(v)])),
    theta: Object.fromEntries(Object.entries(sectors.theta).map(([k, v]) => [k, sl(v)])),
    cycle_agg: sectors.cycle_agg ? sl(sectors.cycle_agg) : undefined,
    observed: slMap(sectors.observed) as Record<string, Array<number | null>> | undefined,
    trend: slMap(sectors.trend) as Record<string, number[]> | undefined,
    cycle_sector: slMap(sectors.cycle_sector) as Record<string, number[]> | undefined,
    theta_p16: slMap(sectors.theta_p16) as Record<string, number[]> | undefined,
    theta_p84: slMap(sectors.theta_p84) as Record<string, number[]> | undefined,
    theta_p025: slMap(sectors.theta_p025) as Record<string, number[]> | undefined,
    theta_p975: slMap(sectors.theta_p975) as Record<string, number[]> | undefined,
  }
}

function normalizeSeries(payload: SeriesPayload): SeriesPayload {
  const canonicalDates = ensureStringArray(readStringArray(payload.dates) ?? [])
  const seriesLength = canonicalDates.length

  function optionalBand(raw: number[] | undefined): number[] | undefined {
    if (!raw) return undefined
    return ensureNumberArray(readNumberArray(raw) ?? [], seriesLength)
  }

  function optionalNullableBand(raw: Array<number | null> | undefined): Array<number | null> | undefined {
    if (!raw) return undefined
    return ensureNullableNumberArray(readNullableNumberArray(raw) ?? [], seriesLength)
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
    gdp_growth_qoq: optionalNullableBand(payload.gdp_growth_qoq),
    gdp_growth_yoy: optionalNullableBand(payload.gdp_growth_yoy),
  }
}

function normalizeSectors(payload: SectorsPayload): SectorsPayload {
  const sectorNames = readStringArray(payload.sector_names) ?? []
  const canonicalDates = ensureStringArray(readStringArray(payload.dates) ?? [])
  const seriesLength = canonicalDates.length

  const optNumberMap = (raw: unknown): Record<string, number[]> | undefined => {
    const m = asNumberArrayMap(raw, sectorNames)
    return m ? ensureSeriesMap(m, sectorNames, seriesLength) : undefined
  }
  const optNullableMap = (raw: unknown): Record<string, Array<number | null>> | undefined => {
    const m = asNullableNumberArrayMap(raw, sectorNames)
    return m ? ensureNullableSeriesMap(m, sectorNames, seriesLength) : undefined
  }

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
    cycle_agg: payload.cycle_agg
      ? ensureNumberArray(readNumberArray(payload.cycle_agg) ?? [], seriesLength)
      : undefined,
    observed: optNullableMap(payload.observed),
    trend: optNumberMap(payload.trend),
    cycle_sector: optNumberMap(payload.cycle_sector),
    theta_p16: optNumberMap(payload.theta_p16),
    theta_p84: optNumberMap(payload.theta_p84),
    theta_p025: optNumberMap(payload.theta_p025),
    theta_p975: optNumberMap(payload.theta_p975),
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

function asNullableNumberArrayMap(
  value: unknown,
  keys: string[],
): Record<string, Array<number | null>> | null {
  if (value === null || typeof value !== 'object') {
    return null
  }
  const record = value as Record<string, unknown>
  return Object.fromEntries(
    keys.map((key) => [key, readNullableNumberArray(record[key]) ?? []]),
  )
}

function ensureNullableSeriesMap(
  values: Record<string, Array<number | null>>,
  keys: string[],
  length: number,
): Record<string, Array<number | null>> {
  return Object.fromEntries(
    keys.map((key) => [key, ensureNullableNumberArray(values[key] ?? [], length)]),
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
