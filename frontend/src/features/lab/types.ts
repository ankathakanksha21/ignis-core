import type { TestRef } from '../models/types.ts'

// Shapes from ml/src/ignis_ml/contract.py, as served by /api/simulate.
export type SimState = {
  gravity_g: number
  sustains: boolean
  regime: string
  burning_rate_mm2_s: number | null
  burn_time_s: number | null
  d2_curve: { t_s: number; d2_mm2: number }[] | null
}

export type Simulation = {
  status: 'ok' | 'invalid_input' | 'not_implemented'
  kind: string
  state: SimState | null
  nearest_tests: TestRef[]
  assumptions: string[]
  message: string | null
}

export type Settings = { fuel: string; oxygen: number; pressure: number; co2: number; helium: number; diameter: number }

export const toRequest = (s: Settings, extra: Record<string, number | string> = {}) => ({
  scenario: 'droplet',
  fuel: s.fuel,
  gravity_g: 0,
  o2_mole_fraction: s.oxygen / 100,
  pressure_kpa: s.pressure,
  co2_mole_fraction: s.co2 / 100,
  he_mole_fraction: s.helium / 100,
  droplet_diameter_mm: s.diameter,
  ...extra,
})

export const figure = (value: number) => String(Number(value.toPrecision(3)))

// Shape returned by /api/lab/flex.
export type FlexRow = { row: number; fuel: string; test_end: string; flagged: boolean } & Record<string, number | string | boolean | null>
export type Flex = {
  source: { psi_id: string; name: string; file_name: string; doi: string | null }
  fields: { key: string; label: string; unit: string }[]
  rows: FlexRow[]
  note: string
}
