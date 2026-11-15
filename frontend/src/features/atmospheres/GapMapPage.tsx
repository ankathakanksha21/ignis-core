import { useState } from 'react'
import { Link } from 'react-router-dom'
import { useApi } from '../../api/useApi.ts'
import { GapGrid } from './GapGrid.tsx'
import { STEPS } from './steps.ts'
import type { GapMap, Habitat, Nearest, Suggestion } from './types.ts'
import { AtmospheresNav } from './AtmospheresNav.tsx'

const KPA_PER_PSI = 6.894757
const percent = (fraction: number) => `${Number((fraction * 100).toPrecision(3))}%`

function nearestText(nearest: Nearest): string {
  const pressure = nearest.pressure_kpa === null ? 'pressure not stated' : `${nearest.pressure_kpa} kPa`
  return `${percent(nearest.o2)} oxygen, ${pressure}`
}

const FUEL_NAMES: Record<string, string> = { solid: 'Solid fuel', droplet: 'Liquid droplets', gas: 'Gas flames' }

function suggestionText(s: Suggestion): string {
  if (s.status === 'pressure_unknown') {
    return `${s.rows_without_pressure} rows at this oxygen state no pressure, so nobody can tell whether this cell was tested.`
  }
  return s.oxygen_never_tested ? 'Never tested at this oxygen, at any pressure.' : 'Tested at this oxygen, but not at this pressure.'
}

export function GapMapPage() {
  const [habitatId, setHabitatId] = useState('moon')
  const [hover, setHover] = useState<string | null>(null)
  const { data: habitats } = useApi<Habitat[]>('/atmospheres/habitats')
  const { data: map, error } = useApi<GapMap>(`/atmospheres/gaps?habitat=${habitatId}`)

  if (error) return <p role="alert">Could not load the gap map: {error}</p>
  if (!habitats || !map) return <p>Loading…</p>
  const habitat = map.habitat

  return (
    <section className="atmospheres">
      <header className="hero">
        <p className="eyebrow">Gap map</p>
        <h1>
          What has never <span className="dim">been tested?</span>
        </h1>
        <p className="lede">Pick a habitat. Empty cells are conditions NASA has not tested.</p>
        <AtmospheresNav />
      </header>

      <p className="filter">
        {habitats.map((h) => (
          <button key={h.id} className={h.id === habitatId ? 'on' : ''} onClick={() => setHabitatId(h.id)}>
            {h.label}
          </button>
        ))}
      </p>
      <dl className="habitat-tiles">
        <div>
          <dd>
            {percent(habitat.o2_mole_fraction)}
            {habitat.open_ended && <small> or more</small>}
          </dd>
          <dt>oxygen</dt>
        </div>
        <div>
          <dd>
            {habitat.pressure_kpa} kPa
            <small>
              {habitat.open_ended && ' or less'} · {(habitat.pressure_kpa / KPA_PER_PSI).toFixed(1)} psi
            </small>
          </dd>
          <dt>pressure</dt>
        </div>
        <div>
          <dd className={habitat.gravity_g === null ? 'missing' : ''}>{habitat.gravity_g === null ? 'not stated' : `${habitat.gravity_g} g`}</dd>
          <dt>gravity</dt>
        </div>
      </dl>
      <p className="quiet center">
        {habitat.basis} {habitat.assumed && `Assumption: ${habitat.assumed}`}
      </p>
      <p className={habitat.gravity_g === 0 ? 'quiet' : 'note'}>{map.gravity_note}</p>

      <h2>Tests per condition</h2>
      <p className="quiet">
        Oxygen runs across and pressure (kPa) runs up. The orange ring marks the habitat.
        {habitat.open_ended && ' Orange-edged cells also fit it.'}
      </p>
      <ul className="gap-legend">
        <li>
          <span className="gap-cell level-0" /> no tests
        </li>
        {STEPS.map((step, index) => (
          <li key={step.from}>
            <span className={`gap-cell level-${index + 1}`} /> {step.label}
          </li>
        ))}
        <li>
          <span className="gap-cell level-0 home" /> {habitat.label}
        </li>
      </ul>
      <div className="gap-maps">
        {map.classes.map((fuel) => (
          <figure key={fuel.fuel_class} className="reveal">
            <figcaption>{FUEL_NAMES[fuel.fuel_class] ?? fuel.fuel_class}</figcaption>
            <GapGrid map={map} fuel={fuel} onHover={setHover} />
          </figure>
        ))}
      </div>
      <p className="gap-detail" aria-live="polite">
        {hover ?? 'Point at a cell to see its tests.'}
      </p>
      <details>
        <summary>What is not counted</summary>
      <ul className="quiet notes">
        {map.classes.map((fuel) => {
          const parts = []
          if (fuel.rows_not_placed) parts.push(`${fuel.rows_not_placed} rows list oxygen levels and pressures separately and are not counted`)
          if (fuel.rows_burner_fed) parts.push(`${fuel.rows_burner_fed} inverse-flame rows are not counted because their oxygen is fed through the burner`)
          return parts.length ? <li key={fuel.fuel_class}>{fuel.fuel_class}: {parts.join('; ')}.</li> : null
        })}
        <li>Not mapped: {map.unmapped.join(' and ')} studies state no oxygen or pressure.</li>
      </ul>
      </details>

      <h2>Closest real test</h2>
      <table>
        <thead>
          <tr>
            <th>Fuel class</th>
            <th>Closest test</th>
            <th>Where</th>
          </tr>
        </thead>
        <tbody>
          {map.classes.map((fuel) => (
            <tr key={fuel.fuel_class}>
              <td>{FUEL_NAMES[fuel.fuel_class] ?? fuel.fuel_class}</td>
              <td>{fuel.nearest ? nearestText(fuel.nearest) : <em>none</em>}</td>
              <td>
                {fuel.nearest && (
                  <>
                    <Link to={`/dashboard/${fuel.nearest.psi_id}`}>{fuel.nearest.name}</Link>, row {fuel.nearest.row}
                    {fuel.nearest.rows > 1 && ` and ${fuel.nearest.rows - 1} more`}
                  </>
                )}
              </td>
            </tr>
          ))}
        </tbody>
      </table>

      <h2>Experiments worth running next</h2>
      <p className="quiet">
        The nearest untested conditions. Solid fuels score higher because cabin materials are solids. The score is ours, not NASA's.
      </p>
      {map.suggestions.length === 0 && <p>No empty cell lies near this habitat.</p>}
      <ol className="suggestions">
        {map.suggestions.map((s) => (
          <li key={`${s.fuel_class}-${s.column}-${s.row}`} className="reveal">
            <strong>
              {FUEL_NAMES[s.fuel_class] ?? s.fuel_class} at {s.oxygen} oxygen and {s.pressure}
            </strong>
            <span className="score">{Math.round(s.score * 100)}</span>
            <p>
              {suggestionText(s)} {s.fuel_why}
              {s.in_bounds && ` Within the ${habitat.label} bounds.`}
            </p>
          </li>
        ))}
      </ol>
    </section>
  )
}
