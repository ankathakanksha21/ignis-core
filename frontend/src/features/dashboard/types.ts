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
}

export type Listing = {
  pillars: { id: string; description: string }[]
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
}
