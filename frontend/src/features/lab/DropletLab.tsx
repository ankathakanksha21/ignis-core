import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { api } from '../../api/client.ts'
import { useApi } from '../../api/useApi.ts'
import type { ModelCard } from '../models/types.ts'
import { DropletView } from './DropletView.tsx'
import { figure, toRequest } from './types.ts'
import type { Settings, Simulation } from './types.ts'

const AIR: Settings = { fuel: 'heptane', oxygen: 21, pressure: 101.3, co2: 0, helium: 0, diameter: 3 }
const PRESETS: { name: string; settings: Settings }[] = [
  { name: 'Heptane droplet in air', settings: AIR },
  { name: 'Moon-base atmosphere', settings: { ...AIR, oxygen: 30, pressure: 71.2 } },
  { name: 'Diluted with carbon dioxide', settings: { ...AIR, co2: 30 } },
  { name: 'Diluted with helium', settings: { ...AIR, helium: 30 } },
]
// Scenarios from the project plan that the engine has no NASA data for. Its own reason is shown.
const UNSUPPORTED = [
  { name: 'Candle on Earth against microgravity', extra: { gravity_g: 1 } },
  { name: 'A material turning flammable from 21% to 30% oxygen', extra: { scenario: 'solid', fuel: 'pmma' } },
  { name: 'Ventilation on against off', extra: { flow_cm_s: 10 } },
]
const SLIDERS = [
  { key: 'oxygen', label: 'Oxygen', unit: '%', feature: 'o2_mole_fraction', scale: 100, step: 1 },
  { key: 'pressure', label: 'Pressure', unit: 'kPa', feature: 'pressure_kpa', scale: 1, step: 0.1 },
  { key: 'co2', label: 'Carbon dioxide', unit: '%', feature: 'co2_mole_fraction', scale: 100, step: 1 },
  { key: 'helium', label: 'Helium', unit: '%', feature: 'he_mole_fraction', scale: 100, step: 1 },
  { key: 'diameter', label: 'Droplet diameter', unit: 'mm', feature: 'droplet_diameter_mm', scale: 1, step: 0.1 },
] as const

// Settings that cannot exist, such as gases adding up to more than 100%, are refused before the engine runs.
const IMPOSSIBLE: Simulation = {
  status: 'invalid_input', kind: 'simulated', state: null, nearest_tests: [], assumptions: [],
  message: 'These settings cannot exist together: the gases would add up to more than 100%, or one would be below zero.',
}
const possible = (s: Settings) => s.oxygen >= 0 && s.co2 >= 0 && s.helium >= 0 && s.oxygen + s.co2 + s.helium <= 100
const simulate = (settings: Settings, extra = {}) =>
  possible(settings) ? api<Simulation>('/simulate', toRequest(settings, extra)).catch(() => IMPOSSIBLE) : Promise.resolve(IMPOSSIBLE)
const leftOver = (sim: Simulation) => Math.sqrt(sim.state?.d2_curve?.at(-1)?.d2_mm2 ?? 0)
const leftText = (sim: Simulation) => (leftOver(sim) < 0.01 ? 'none, it burns away' : `${figure(leftOver(sim))} mm`)

function Variants({ settings }: { settings: Settings }) {
  const variants = [
    { name: 'As set', settings },
    { name: 'Oxygen 5 points lower', settings: { ...settings, oxygen: settings.oxygen - 5 } },
    { name: 'Carbon dioxide 20 points higher', settings: { ...settings, co2: settings.co2 + 20 } },
    { name: 'Helium 20 points higher', settings: { ...settings, helium: settings.helium + 20 } },
  ]
  const request = JSON.stringify(variants.map((v) => v.settings))
  const [found, setFound] = useState<{ request: string; sims: Simulation[] } | null>(null)

  useEffect(() => {
    let live = true
    Promise.all((JSON.parse(request) as Settings[]).map((s) => simulate(s))).then((sims) => live && setFound({ request, sims }))
    return () => {
      live = false
    }
  }, [request])

  if (found?.request !== request) return null
  return (
    <div className="scroll">
    <table className="variants">
      <thead>
        <tr>
          <th>Change</th>
          <th>Burning rate (mm²/s)</th>
          <th>Flame lasts (s)</th>
          <th>Droplet left</th>
        </tr>
      </thead>
      <tbody>
        {variants.map((variant, index) => {
          const sim = found.sims[index]
          return (
            <tr key={variant.name}>
              <td>{variant.name}</td>
              {sim.status === 'ok' && sim.state ? (
                <>
                  <td>{figure(sim.state.burning_rate_mm2_s ?? 0)}</td>
                  <td>{figure(sim.state.burn_time_s ?? 0)}</td>
                  <td>{leftText(sim)}</td>
                </>
              ) : (
                <td colSpan={3} className="missing">
                  Not simulated. {sim.message}
                </td>
              )}
            </tr>
          )
        })}
      </tbody>
    </table>
    </div>
  )
}

export function DropletLab() {
  const { data: cards } = useApi<ModelCard[]>('/models')
  const [settings, setSettings] = useState<Settings>(AIR)
  const [sim, setSim] = useState<{ request: string; result: Simulation } | null>(null)
  const [refused, setRefused] = useState<(string | null)[] | null>(null)
  const request = JSON.stringify(settings)

  useEffect(() => {
    let live = true
    simulate(JSON.parse(request)).then((result) => live && setSim({ request, result }))
    return () => {
      live = false
    }
  }, [request])
  useEffect(() => {
    Promise.all(UNSUPPORTED.map((item) => simulate(AIR, item.extra))).then((sims) => setRefused(sims.map((s) => (s.status === 'ok' ? null : s.message))))
  }, [])

  const features = cards?.find((card) => card.model_id === 'flex_burning_rate')?.features ?? []
  const fuels = features.find((f) => f.name === 'fuel')?.categories ?? [settings.fuel]
  const result = sim?.request === request ? sim.result : null
  const state = result?.status === 'ok' ? result.state : null
  const columns = result?.nearest_tests.length ? Object.keys(result.nearest_tests[0].values) : []

  return (
    <>
      <p className="lede">
        One fuel droplet burning in microgravity. The panels are <strong>simulated</strong> from NASA's FLEX tests. The table under them
        is <strong>measured</strong>.
      </p>
      <p className="filter">
        {PRESETS.map((preset) => (
          <button key={preset.name} className={JSON.stringify(preset.settings) === request ? 'on' : ''} onClick={() => setSettings(preset.settings)}>
            {preset.name}
          </button>
        ))}
      </p>

      <div className="bench">
        <div className="box controls">
          <h2>Settings</h2>
          <label>
            <span>Fuel</span>
            <select value={settings.fuel} onChange={(event) => setSettings({ ...settings, fuel: event.target.value })}>
              {fuels.map((name) => (
                <option key={name}>{name}</option>
              ))}
            </select>
          </label>
          {SLIDERS.map((slider) => {
            const feature = features.find((f) => f.name === slider.feature)
            const low = (feature?.tested_min ?? 0) * slider.scale
            const high = (feature?.tested_max ?? 100) * slider.scale
            return (
              <label key={slider.key}>
                <span>
                  {slider.label} <strong>{figure(settings[slider.key])}</strong> {slider.unit}
                </span>
                <input type="range" min={Math.ceil(low * 10) / 10} max={Math.floor(high * 10) / 10} step={slider.step} value={settings[slider.key]} onChange={(event) => setSettings({ ...settings, [slider.key]: event.target.valueAsNumber })} />
              </label>
            )
          })}
          <p className="quiet">Gravity is fixed at microgravity. Each slider covers the range NASA tested.</p>
        </div>

        <div className="box simulated">
          <h2>
            Simulated <span className="tag">not a measurement</span>
          </h2>
          {state && result ? (
            <>
              <DropletView key={request} state={state} />
              <dl className="tiles">
                <div>
                  <dt>Burning rate</dt>
                  <dd>{figure(state.burning_rate_mm2_s ?? 0)} mm²/s</dd>
                </div>
                <div>
                  <dt>Flame lasts</dt>
                  <dd>{figure(state.burn_time_s ?? 0)} s</dd>
                </div>
                <div>
                  <dt>Droplet left</dt>
                  <dd>{leftText(result)}</dd>
                </div>
              </dl>
              <details>
                <summary>What the simulation assumes</summary>
                <ul>
                  {result.assumptions.map((line) => (
                    <li key={line}>{line}</li>
                  ))}
                </ul>
              </details>
            </>
          ) : (
            result && (
              <p className="refused">
                <strong>Nothing is simulated.</strong> {result.message}
              </p>
            )
          )}
        </div>
      </div>

      <h2>One change at a time</h2>
      <p className="quiet">The same droplet with one setting moved. Simulated. A change NASA never tested is not simulated.</p>
      <Variants settings={settings} />

      {result && result.nearest_tests.length > 0 && (
        <div className="measured">
          <h2>
            Nearest real tests <span className="tag">measured by NASA</span>
          </h2>
          {result.status === 'ok' && <p className="quiet">{result.message?.replace(/^Simulated, not measured\.\s*/, '')}</p>}
          <div className="scroll">
            <table>
              <thead>
                <tr>
                  <th>Test</th>
                  {columns.map((column) => (
                    <th key={column}>{column}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {result.nearest_tests.map((test) => (
                  <tr key={test.row}>
                    <td>
                      <Link to={`/dashboard/${test.psi_id}`}>{test.psi_id}</Link>, row {test.row}
                    </td>
                    {columns.map((column) => (
                      <td key={column}>{test.values[column] || <em>empty</em>}</td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      <h2>What the lab cannot simulate</h2>
      <p className="quiet">These scenarios were planned. The engine refuses them because NASA's tables hold no data to fit them to.</p>
      <ul className="unsupported">
        {UNSUPPORTED.map((item, index) => (
          <li key={item.name}>
            <strong>{item.name}.</strong> {refused ? (refused[index] ?? 'Now available.') : ''}
          </li>
        ))}
      </ul>
    </>
  )
}
