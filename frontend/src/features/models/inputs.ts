import type { Feature } from './types.ts'

const LABELS: Record<string, string> = {
  fuel: 'Fuel',
  material: 'Material',
  o2_mole_fraction: 'Oxygen',
  co2_mole_fraction: 'Carbon dioxide',
  he_mole_fraction: 'Helium',
  fuel_mole_fraction: 'Fuel in the burner gas',
  pressure_kpa: 'Pressure',
  droplet_diameter_mm: 'Droplet diameter',
  fuel_flow_mg_s: 'Fuel flow',
}

export const label = (name: string) => LABELS[name] ?? name.replaceAll('_', ' ')

// Mole fractions travel as 0 to 1 and are shown as percent. Everything else is shown as sent.
const isFraction = (name: string) => name.endsWith('_mole_fraction')
export const scale = (name: string) => (isFraction(name) ? 100 : 1)
export const unit = (feature: { name: string; unit?: string | null }) => (isFraction(feature.name) ? '%' : (feature.unit ?? ''))
export const shown = (name: string, value: number) => String(Number((value * scale(name)).toPrecision(4)))
export const pretty = (text: string | null) => (text ?? '').replace('^2', '²')

export type Inputs = Record<string, string>

/** A starting value for each input: the first category, zero for a diluent, else the middle of the tested range. */
export function defaults(features: Feature[]): Inputs {
  const inputs: Inputs = {}
  for (const feature of features) {
    if (feature.kind === 'categorical') inputs[feature.name] = feature.categories?.[0] ?? ''
    else if (feature.tested_min === 0) inputs[feature.name] = '0'
    else inputs[feature.name] = shown(feature.name, ((feature.tested_min ?? 0) + (feature.tested_max ?? 0)) / 2)
  }
  return inputs
}

/** Form text back to contract units. An empty or unreadable box is left out, so the model reports it missing. */
export function toRequest(features: Feature[], inputs: Inputs): Record<string, number | string> {
  const body: Record<string, number | string> = {}
  for (const feature of features) {
    const text = inputs[feature.name] ?? ''
    if (feature.kind === 'categorical') body[feature.name] = text
    else if (text.trim() !== '' && Number.isFinite(Number(text))) body[feature.name] = Number(text) / scale(feature.name)
  }
  return body
}

// Conditions worth trying first. Inputs only: what comes back is whatever the model says.
export const EXAMPLES: Record<string, { name: string; inputs: Inputs }[]> = {
  flex_burning_rate: [
    { name: 'Heptane in a Moon-base atmosphere', inputs: { fuel: 'heptane', o2_mole_fraction: '30', co2_mole_fraction: '0', he_mole_fraction: '0', pressure_kpa: '71.2', droplet_diameter_mm: '3' } },
    { name: 'Oxygen beyond what was tested', inputs: { fuel: 'heptane', o2_mole_fraction: '50', co2_mole_fraction: '0', he_mole_fraction: '0', pressure_kpa: '71.2', droplet_diameter_mm: '3' } },
    { name: 'Carbon dioxide and helium together', inputs: { fuel: 'heptane', o2_mole_fraction: '21', co2_mole_fraction: '20', he_mole_fraction: '20', pressure_kpa: '101.3', droplet_diameter_mm: '3' } },
  ],
  cfig_hot_ignition: [
    { name: 'Butane at 23% oxygen', inputs: { fuel: 'butane', o2_mole_fraction: '23', pressure_kpa: '101.3', fuel_mole_fraction: '50', fuel_flow_mg_s: '1.6' } },
    { name: 'Propane at 30% oxygen', inputs: { fuel: 'propane', o2_mole_fraction: '30', pressure_kpa: '101.3', fuel_mole_fraction: '30', fuel_flow_mg_s: '1' } },
  ],
  solid_flame_spread: [
    { name: 'PMMA at 21% oxygen', inputs: { material: 'pmma', o2_mole_fraction: '21' } },
    { name: 'PMMA at 30% oxygen, the Moon-base level', inputs: { material: 'pmma', o2_mole_fraction: '30' } },
  ],
}
