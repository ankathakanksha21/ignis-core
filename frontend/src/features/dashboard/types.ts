// Shapes returned by /api/investigations (backend/app/routers/investigations.py).

export type Range = { min: number; max: number }

export type Card = {
  psi_id: string
  name: string
  title: string | null
  pillar: string
  pillar_why: string
  fuel_class: string | null
  project_type: string | null
  platform: string | null
  gravity_g: number | null
  hardware: string | null
  doi: string | null
  objective_short: string | null
  test_rows: number
  summary_rows: number
  tests_counted: number
  fuels: string[]
  fuel_count: number
  conditions: Record<string, Range>
  flag_count: number
  brief_note: string | null
  ai_summary: AiSummary | null
}

// Written by the language model and checked by code (backend/app/summaries.py).
export type AiSummary = { one_line: string; summary: string; measurements: { name: string; quote: string }[] }

export type Listing = {
  pillars: { id: string; description: string }[]
  ai_model: string | null
  investigations: Card[]
  left_out: { psi_id: string; title: string; reason: string }[]
}

export type FieldSource = {
  source_column: string
  source_unit: string
  note: string | null
  rows_with_value: number
  min: number | null
  max: number | null
}

export type Table = {
  file_name: string
  rows: Record<string, number>
  tests_counted: number
  fields: Record<string, FieldSource>
  flags: Record<string, number>
  columns: { name: string; filled: number; distinct: number }[]
}

export type Flag = { psi_id: string; file_name: string; row: string; column: string; check: string; detail: string }

export type Detail = Card & {
  objective: string | null
  approach: string | null
  hypothesis: string | null
  research_impacts: string | null
  license: string | null
  start_date: string | null
  end_date: string | null
  related: { psi_id: string; name: string }[]
  shares_hardware: { hardware: string; with: { psi_id: string; name: string }[] } | null
  publications: { title: string | null; authors: string | null; doi: string | null }[]
  tables: Table[]
  flags: Flag[]
  ai_model: string | null
}

// Shapes returned by /api/investigations/missions and /rank (backend/app/ranking.py).

export type Mission = {
  id: string
  label: string
  o2_mole_fraction: number
  pressure_kpa: number
  gravity_g: number
  open_ended: boolean
  basis: string
  assumed: string | null
}

export type Missions = {
  missions: Mission[]
  factors: { id: string; label: string; weight: number }[]
  tolerance: { o2_mole_fraction: number; pressure_kpa: number; flow_cm_s: number }
  fuel_relevance: { fuel_class: string; score: number; why: string }[]
}

export type Factor = {
  id: string
  label: string
  score: number
  weight: number
  unknown: boolean
  detail: string
  source: { file_name: string; row: number; column: string; raw: string } | null
}

export type Ranked = {
  psi_id: string
  name: string
  pillar: string
  fuel_class: string | null
  score: number
  factors: Factor[]
  one_line: string | null
}

export type Ranking = { edited: string[]; results: Ranked[] }

// Shapes returned by /api/investigations/points.

export type Point = { o2: number; pressure_kpa?: number; rows: number[]; approximate: boolean }

export type PointSeries = {
  psi_id: string
  name: string
  points: Point[]
  oxygen_only: Point[]
  rows_not_placed: number
  rows_burner_fed: number
}

// Shape returned by /api/investigations/similar.

export type SimilarRow = {
  psi_id: string
  name: string
  file_name: string
  row: number
  row_kind: string
  fuel_class: string | null
  fuel: string | null
  values: Record<string, Range>
  not_stated: string[]
  distance: number
}

export type Similar = { results: SimilarRow[]; nothing_close: boolean; tolerance: Record<string, number> }

export type Who = { psi_id: string; name: string }

export type EarthPanel = {
  field: string
  themes: { id: string; label: string; quotes: { text: string; investigations: Who[] }[] }[]
  not_quoted: Who[]
  spinoffs: { product: string; sources: { title: string; publication: string; url: string; quotes: string[] }[] }[]
  spinoffs_checked: string
}

// Shape returned by /api/investigations/{psi_id}/rows: table rows as NASA published them.

export type RawRows = {
  psi_id: string
  name: string
  file_name: string
  doi: string | null
  columns: string[]
  rows: { row: number; cells: string[]; flagged: number[] }[]
  asked: number
  missing: number[]
}
