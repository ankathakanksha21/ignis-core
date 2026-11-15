import type { Card, Range } from './types.ts'

export const NOT_STATED = 'not stated'

export const PILLAR_NAMES: Record<string, string> = {
  prevention: 'Prevention',
  detection: 'Detection',
  suppression: 'Suppression',
  science: 'Flame science',
}

// How each condition is shown. Values arrive in contract units and are only rescaled here.
export const CONDITIONS = [
  { field: 'o2_mole_fraction', label: 'Oxygen', scale: 100, unit: '%' },
  { field: 'burner_o2_mole_fraction', label: 'Burner oxygen', scale: 100, unit: '%' },
  { field: 'pressure_kpa', label: 'Pressure', scale: 1, unit: 'kPa' },
  { field: 'flow_cm_s', label: 'Flow', scale: 1, unit: 'cm/s' },
  { field: 'n2_mole_fraction', label: 'Nitrogen', scale: 100, unit: '%' },
  { field: 'co2_mole_fraction', label: 'Carbon dioxide', scale: 100, unit: '%' },
  { field: 'he_mole_fraction', label: 'Helium', scale: 100, unit: '%' },
]

function number(value: number): string {
  return String(Number(value.toPrecision(3)))
}

export function range(found: Range | undefined | null, scale = 1, unit = ''): string {
  if (!found) return NOT_STATED
  const low = number(found.min * scale)
  const high = number(found.max * scale)
  return low === high ? `${low} ${unit}` : `${low} to ${high} ${unit}`
}

export function testCount(card: Card): string {
  if (card.test_rows && !card.summary_rows) return `${card.test_rows} tests`
  if (card.summary_rows) {
    const rows = `${card.summary_rows} summary rows`
    return card.tests_counted > card.test_rows ? `${rows} covering ${card.tests_counted} tests` : `${rows}, tests not counted`
  }
  return 'no test table'
}

/** The test count as a number and a short label. */
export function testStat(card: Card): { value: string; label: string } {
  if (card.summary_rows) {
    return card.tests_counted > card.test_rows
      ? { value: String(card.tests_counted), label: `tests in ${card.summary_rows} summary rows` }
      : { value: String(card.summary_rows), label: 'summary rows' }
  }
  return card.test_rows ? { value: String(card.test_rows), label: 'tests' } : { value: 'none', label: 'no test table' }
}

export function gravity(card: Card): string {
  if (card.gravity_g === 0) return 'microgravity'
  return card.project_type === 'Ground Investigation' ? 'ground study' : NOT_STATED
}
