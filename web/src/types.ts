export interface SummaryPayload {
  last_updated: string
  scenario: string
  display_start?: string
  display_end?: string
  latest_output_gap: number | null
  latest_potential_growth: number | null
  sample_end: string | null
}

export interface SeriesPayload {
  last_updated: string
  scenario: string
  dates: string[]
  output_gap: number[]
  output_gap_p16?: number[]
  output_gap_p84?: number[]
  output_gap_p025?: number[]
  output_gap_p975?: number[]
  potential_growth: number[]
  potential_growth_p16?: number[]
  potential_growth_p84?: number[]
  potential_growth_p025?: number[]
  potential_growth_p975?: number[]
  gdp_observed: Array<number | null>
  gdp_trend: number[]
}

export interface SectorsPayload {
  last_updated: string
  scenario: string
  dates: string[]
  sector_names: string[]
  shares: Record<string, number[]>
  theta: Record<string, number[]>
}

export interface DashboardData {
  summary: SummaryPayload
  series: SeriesPayload
  sectors: SectorsPayload
}
