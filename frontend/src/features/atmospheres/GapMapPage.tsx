import { useState } from 'react'
import { useTitle } from '../../useTitle.ts'
import { Link } from 'react-router-dom'
import { useApi } from '../../api/useApi.ts'
import { testLink } from '../../testLink.ts'
import { useStored } from '../../useStored.ts'
import { GapGrid } from './GapGrid.tsx'
import { STEPS } from './steps.ts'
import type { GapMap, Habitat, Nearest, Picked, Suggestion } from './types.ts'
import { AtmospheresNav } from './AtmospheresNav.tsx'

const KPA_PER_PSI = 6.894757
const percent = (fraction: number) => `${Number((fraction * 100).toPrecision(3))}%`
const points = (score: number) => Math.round(score * 100)

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

/** What one cell holds, with a link to every test row it counts. */
function CellDetail({ map, picked, rank, onClose }: { map: GapMap; picked: Picked; rank?: number; onClose: () => void }) {
  const fuel = map.classes.find((k) => k.fuel_class === picked.fuel_class)
  const cell = fuel?.cells.find((c) => c.column === picked.column && c.row === picked.row)
  return (
    <div className="gap-picked">
      <p>
        <strong>
          {FUEL_NAMES[picked.fuel_class] ?? picked.fuel_class}, {map.oxygen_bins[picked.column]} oxygen, pressure {map.pressure_bins[picked.row]}
        </strong>
        <button type="button" onClick={onClose} aria-label="Close this cell">
          Close
        </button>
      </p>
      {cell ? (
        <ul>
          {cell.sources.map((source) => (
            <li key={`${source.psi_id}-${source.file_name}`}>
              <Link to={testLink(source.psi_id, source.file_name, source.rows)}>
                Open the {source.rows.length} {source.rows.length === 1 ? 'row' : 'rows'}
              </Link>{' '}
              from <Link to={`/dashboard/${source.psi_id}`}>{source.name}</Link>
              <small> {source.file_name}</small>
            </li>
          ))}
        </ul>
      ) : (
        <p className="quiet">
          No test sits in this cell.{rank ? ` It is suggestion ${rank} below.` : ' It is too far from this habitat to be suggested.'}
        </p>
      )}
    </div>
  )
}

export function GapMapPage() {
  const [habitatId, setHabitatId] = useStored('gaps.habitat', 'moon')
  const [hover, setHover] = useState<string | null>(null)
  const [picked, setPicked] = useState<Picked | null>(null)
  const [lit, setLit] = useState<Picked | null>(null)
  useTitle('Gap map')
  const { data: habitats } = useApi<Habitat[]>('/atmospheres/habitats')
  const { data: map, error } = useApi<GapMap>(`/atmospheres/gaps?habitat=${habitatId}`)

  if (error) return <p role="alert">Could not load the gap map: {error}</p>
  if (!habitats || !map) return <p className="loading">Loading…</p>
  const habitat = map.habitat
  const rankOf = (cell: Picked) =>
    map.suggestions.findIndex((s) => s.fuel_class === cell.fuel_class && s.column === cell.column && s.row === cell.row) + 1 || undefined
  const ranksFor = (fuelClass: string) =>
    new Map(map.suggestions.flatMap((s, index) => (s.fuel_class === fuelClass ? [[`${s.column},${s.row}`, index + 1] as const] : [])))
  const relevance = Object.entries(map.fuel_relevance)
    .map(([fuelClass, score]) => `${fuelClass} ${points(score)}`)
    .join(', ')

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
          <button key={h.id} className={h.id === habitatId ? 'on' : ''} onClick={() => (setHabitatId(h.id), setPicked(null))}>
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
        Oxygen runs across and pressure (kPa) runs up. The orange ring marks the cell that holds the habitat's own oxygen and
        pressure.
        {habitat.open_ended &&
          ` The brief gives this habitat as bounds, ${percent(habitat.o2_mole_fraction)} oxygen or more and ${habitat.pressure_kpa} kPa or less, so every cell with at least that oxygen and at most that pressure also fits it. Those cells have a thin orange edge. An empty one is a condition this habitat could have that NASA has not tested.`}{' '}
        Click a cell to open its tests.
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
        {habitat.open_ended && (
          <li>
            <span className="gap-cell level-0 in-bounds" /> also inside the {habitat.label} bounds
          </li>
        )}
        {map.suggestions.length > 0 && (
          <li>
            <span className="gap-cell level-0 suggested">
              <span className="rank">1</span>
            </span>{' '}
            suggested next, by rank
          </li>
        )}
      </ul>
      <div className="gap-maps">
        {map.classes.map((fuel) => (
          <figure key={fuel.fuel_class} className="reveal">
            <figcaption>{FUEL_NAMES[fuel.fuel_class] ?? fuel.fuel_class}</figcaption>
            <GapGrid map={map} fuel={fuel} ranks={ranksFor(fuel.fuel_class)} picked={picked} lit={lit} onHover={setHover} onPick={setPicked} />
          </figure>
        ))}
      </div>
      {picked ? (
        <CellDetail map={map} picked={picked} rank={rankOf(picked)} onClose={() => setPicked(null)} />
      ) : (
        <p className="gap-detail" aria-live="polite">
          {hover ?? 'Point at a cell to see its tests. Click it to get links to them.'}
        </p>
      )}
      <details>
        <summary>What is not counted</summary>
        <ul className="quiet notes">
          {map.classes.map((fuel) => {
            const parts = []
            if (fuel.rows_not_placed) parts.push(`${fuel.rows_not_placed} rows list oxygen levels and pressures separately and are not counted`)
            if (fuel.rows_burner_fed) parts.push(`${fuel.rows_burner_fed} inverse-flame rows are not counted because their oxygen is fed through the burner`)
            return parts.length ? (
              <li key={fuel.fuel_class}>
                {fuel.fuel_class}: {parts.join('; ')}.
              </li>
            ) : null
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
                    <Link to={`/dashboard/${fuel.nearest.psi_id}`}>{fuel.nearest.name}</Link>,{' '}
                    <Link to={testLink(fuel.nearest.psi_id, fuel.nearest.file_name, [fuel.nearest.row])}>row {fuel.nearest.row}</Link>
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
        The nearest untested conditions, numbered as on the grids above. The score is ours, not NASA's.
      </p>
      <details className="chosen">
        <summary>How these cells are chosen</summary>
        <ol>
          <li>
            Every test row is placed in a cell by its oxygen and its pressure, separately for solid fuels, liquid droplets and gas
            flames. A cell with a number in it has been tested.
          </li>
          <li>
            An empty cell becomes a candidate when it is within one tolerance of the habitat: {map.tolerance.oxygen_points} oxygen
            points and {map.tolerance.pressure_kpa} kPa.
            {habitat.open_ended && ' This habitat is given as bounds ("or more", "or less"), so every empty cell inside the bounds is a candidate too.'}
          </li>
          <li>
            Closeness is 100 for the habitat's own cell. For any other cell it is measured from the cell's centre, on whichever of
            oxygen or pressure is further away, and falls to 0 one tolerance away.
          </li>
          <li>
            Score = closeness × fuel relevance. Fuel relevance says how close the fuel is to a cabin material: {relevance}.
          </li>
          <li>
            A cell goes to the end of the list when rows at its oxygen level state no pressure, because one of those rows may have
            been run there.
          </li>
          <li>
            {map.candidates > map.suggestions.length
              ? `${map.candidates} cells qualify for this habitat. The top ${map.suggestions.length} are shown.`
              : `${map.candidates} ${map.candidates === 1 ? 'cell qualifies' : 'cells qualify'} for this habitat.`}
          </li>
        </ol>
      </details>
      {map.suggestions.length === 0 && <p>No empty cell lies near this habitat.</p>}
      <ol className="suggestions">
        {map.suggestions.map((s, index) => (
          <li
            key={`${s.fuel_class}-${s.column}-${s.row}`}
            className="reveal"
            onPointerEnter={() => setLit(s)}
            onPointerLeave={() => setLit(null)}
          >
            <span className="rank">{index + 1}</span>
            <strong>
              {FUEL_NAMES[s.fuel_class] ?? s.fuel_class} at {s.oxygen} oxygen and {s.pressure}
            </strong>
            <span className="score">{points(s.score)}</span>
            <p>
              {suggestionText(s)} {s.fuel_why}
              {s.in_bounds && ` Within the ${habitat.label} bounds.`}
            </p>
            <p className="working">
              Closeness {points(s.closeness)} × fuel relevance {points(s.relevance)} = {points(s.score)}
            </p>
          </li>
        ))}
      </ol>
    </section>
  )
}
