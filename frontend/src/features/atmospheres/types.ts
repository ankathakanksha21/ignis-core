// Shapes returned by /api/atmospheres (backend/app/gaps.py).

export type Habitat = {
  id: string
  label: string
  o2_mole_fraction: number
  pressure_kpa: number
  gravity_g: number | null
  open_ended: boolean
  basis: string
  assumed: string | null
}

export type Source = { psi_id: string; name: string; file_name: string; rows: number[] }

export type Cell = { column: number; row: number; rows: number; from: Record<string, number>; sources: Source[] }

/** A cell of one fuel class's grid, as the page points at it. */
export type Picked = { fuel_class: string; column: number; row: number }

export type Nearest = {
  psi_id: string
  name: string
  file_name: string
  row: number
  rows: number
  o2: number
  pressure_kpa: number | null
  distance: number
}

export type ClassMap = {
  fuel_class: string
  cells: Cell[]
  nearest: Nearest | null
  rows_not_placed: number
  rows_burner_fed: number
}

export type Suggestion = {
  fuel_class: string
  column: number
  row: number
  oxygen: string
  pressure: string
  score: number
  fuel_why: string
  in_bounds: boolean
  status: 'untested' | 'pressure_unknown'
  rows_without_pressure: number
  oxygen_never_tested: boolean
  closeness: number
  relevance: number
}

export type GapMap = {
  habitat: Habitat
  gravity_note: string
  oxygen_bins: string[]
  pressure_bins: string[]
  habitat_cell: { column: number; row: number }
  classes: ClassMap[]
  suggestions: Suggestion[]
  candidates: number
  tolerance: { oxygen_points: number; pressure_kpa: number }
  fuel_relevance: Record<string, number>
  unmapped: string[]
}
