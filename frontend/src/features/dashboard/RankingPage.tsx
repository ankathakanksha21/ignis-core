import { useEffect, useState } from 'react'
import { useTitle } from '../../useTitle.ts'
import { Link } from 'react-router-dom'
import { NumberField } from '../../NumberField.tsx'
import { useStored } from '../../useStored.ts'
import { api } from '../../api/client.ts'
import { useApi } from '../../api/useApi.ts'
import { DashboardNav } from './DashboardNav.tsx'
import { NOT_STATED, PILLAR_NAMES } from './format.ts'
import type { Factor, Mission, Missions, Ranking } from './types.ts'

const KPA_PER_PSI = 6.894757
const FUEL_CLASSES = ['solid', 'droplet', 'gas', 'smoke', 'dust']
const points = (score: number) => Math.round(score * 100)

// flow is null until the user gives one: no mission states a flow. fuel is '' for any fuel class.
type Settings = { mission: string; oxygen: number; pressure: number; gravity: number; flow: number | null; fuel: string }

/** A mission's own atmosphere. Flow and fuel class are the user's, so they carry over when the mission changes. */
function settingsFor(mission: Mission, keep?: Settings | null): Settings {
  return {
    mission: mission.id,
    oxygen: Number((mission.o2_mole_fraction * 100).toPrecision(6)),
    pressure: mission.pressure_kpa,
    gravity: mission.gravity_g,
    flow: keep?.flow ?? null,
    fuel: keep?.fuel ?? '',
  }
}

function Meter({ score, thin = false }: { score: number; thin?: boolean }) {
  return (
    <span className={thin ? 'meter thin' : 'meter'} title={`${points(score)} of 100`}>
      <span style={{ width: `${points(score)}%` }} />
    </span>
  )
}

function FactorCell({ factor }: { factor: Factor }) {
  return (
    <div className="factor">
      <div className="factor-head">
        <span>{factor.label}</span>
        <span>{factor.unknown ? <em>{NOT_STATED}</em> : points(factor.score)}</span>
      </div>
      <Meter score={factor.score} thin />
      <p>
        {factor.detail}
        {factor.source && ` Row ${factor.source.row}, column "${factor.source.column}".`}
      </p>
    </div>
  )
}

export function RankingPage() {
  const { data: setup, error: setupError } = useApi<Missions>('/investigations/missions')
  // Kept for the tab, so the ranking is still here after a visit to Compare or Similar.
  const [settings, setSettings] = useStored<Settings | null>('rank.settings', null)
  const [pillar, setPillar] = useStored('rank.pillar', 'all')
  const [open, setOpen] = useStored('rank.open', false)
  const [ranking, setRanking] = useState<Ranking | null>(null)
  const [error, setError] = useState<string | null>(null)
  useTitle('Rank for a mission')

  const current = settings ?? (setup ? settingsFor(setup.missions[0]) : null)
  const request = current && JSON.stringify(current)

  useEffect(() => {
    if (!request) return
    const s: Settings = JSON.parse(request)
    let live = true
    api<Ranking>('/investigations/rank', {
      mission: s.mission,
      o2_mole_fraction: s.oxygen / 100,
      pressure_kpa: s.pressure,
      gravity_g: s.gravity,
      ...(s.flow === null ? {} : { flow_cm_s: s.flow }),
    }).then(
      (result) => live && (setRanking(result), setError(null)),
      (reason: Error) => live && setError(reason.message),
    )
    return () => {
      live = false
    }
  }, [request])

  if (setupError) return <p role="alert">Could not load the missions: {setupError}</p>
  if (!setup || !current) return <p className="loading">Loading…</p>

  const mission = setup.missions.find((m) => m.id === current.mission) ?? setup.missions[0]
  const shown = (ranking?.results ?? []).filter(
    (result) => (pillar === 'all' || result.pillar === pillar) && (!current.fuel || result.fuel_class === current.fuel),
  )
  const change = (patch: Partial<Settings>) => setSettings({ ...current, ...patch })
  const number = (key: 'oxygen' | 'pressure' | 'gravity', min: number, max: number, step: number) => (
    <NumberField value={current[key]} min={min} max={max} step={step} onCommit={(value) => value !== null && change({ [key]: value })} />
  )
  const own = settingsFor(mission)
  const edited =
    current.oxygen !== own.oxygen || current.pressure !== own.pressure || current.gravity !== own.gravity || current.flow !== null || current.fuel !== ''
  const weightOf = (id: string) => setup.factors.find((f) => f.id === id)?.weight ?? 0
  // The same conditions, carried to the Similar page. It searches tests, and no dust test states its conditions.
  const similar = new URLSearchParams({ o2: String(current.oxygen), pressure: String(current.pressure) })
  if (current.flow !== null) similar.set('flow', String(current.flow))
  if (current.fuel && current.fuel !== 'dust') similar.set('fuel', current.fuel)

  return (
    <section className="dashboard ranking">
      <header className="hero">
        <p className="eyebrow">Mission relevance</p>
        <h1>
          Which experiments matter <span className="dim">for your mission?</span>
        </h1>
        <p className="lede">Pick a mission. The score is ours, not a NASA rating.</p>
        <DashboardNav />
      </header>

      <p className="filter">
        {setup.missions.map((m) => (
          <button key={m.id} className={m.id === current.mission ? 'on' : ''} onClick={() => setSettings(settingsFor(m, current))}>
            {m.label}
          </button>
        ))}
      </p>

      <p className="profile">
        {current.oxygen}% oxygen · {current.pressure} kPa · {current.gravity} g
        {current.flow !== null && ` · ${current.flow} cm/s flow`}
        {current.fuel && ` · ${current.fuel} fuels only`}
        {mission.assumed && <span>. {mission.assumed}</span>}
      </p>

      <details className="adjust" open={open} onToggle={(event) => event.currentTarget.open !== open && setOpen(event.currentTarget.open)}>
        <summary>Change the habitat</summary>
        <div className="controls">
          <fieldset className="habitat">
            <legend>Habitat</legend>
            <label>Oxygen {number('oxygen', 0, 100, 1)} %</label>
            <label>
              Pressure {number('pressure', 1, 500, 0.1)} kPa <small>({(current.pressure / KPA_PER_PSI).toFixed(1)} psi)</small>
            </label>
            <label>Gravity {number('gravity', 0, 1, 0.01)} g</label>
            <label>
              Flow <NumberField value={current.flow} min={0} max={1000} step="any" optional placeholder="any" onCommit={(flow) => change({ flow })} /> cm/s
            </label>
            <label>
              Fuel class{' '}
              <select value={current.fuel} onChange={(event) => change({ fuel: event.target.value })}>
                <option value="">any</option>
                {FUEL_CLASSES.map((name) => (
                  <option key={name}>{name}</option>
                ))}
              </select>
            </label>
            <p className="quiet">
              {mission.basis} Leave flow empty to rank without it. A fuel class shows only the experiments that burned that kind of fuel.
              {edited && ' You changed this profile.'}
            </p>
            {edited && <button onClick={() => setSettings(settingsFor(mission))}>Reset to {mission.label}</button>}
          </fieldset>
        </div>

        <details className="how">
          <summary>How the score works</summary>
          <ul>
            <li>
              The score is an average of five factors, each from 0 to 100. Oxygen match and fuel type count most (weight{' '}
              {weightOf('oxygen')} each), then pressure match ({weightOf('pressure')}), then gravity and pillar ({weightOf('gravity')}{' '}
              each). The weights are fixed. They are ours, not NASA's.
            </li>
            <li>
              Oxygen and pressure compare the habitat with the nearest value the investigation tested. A match scores 100 and falls
              to 0 at {setup.tolerance.o2_mole_fraction * 100} oxygen points or {setup.tolerance.pressure_kpa} kPa away.
            </li>
            <li>
              If you give a flow, a sixth factor is added: flow match (weight {weightOf('flow')}). It falls to 0 at{' '}
              {setup.tolerance.flow_cm_s} cm/s away, and an investigation that states no flow scores 0 on it.
            </li>
            <li>Oxygen fed through a burner is not counted as the atmosphere.</li>
            <li>Fuel type: {setup.fuel_relevance.map((f) => `${f.fuel_class} ${points(f.score)}`).join(', ')}.</li>
            <li>Gravity scores 100 only when the tests ran at the mission's gravity. PSI has no partial-gravity tests.</li>
            <li>A factor the data cannot answer scores 0, so missing data never helps.</li>
          </ul>
        </details>
      </details>

      <p className="filter">
        {['all', ...Object.keys(PILLAR_NAMES)].map((name) => (
          <button key={name} className={name === pillar ? 'on' : ''} onClick={() => setPillar(name)}>
            {PILLAR_NAMES[name] ?? 'all'}
          </button>
        ))}
      </p>
      {error && <p role="alert">Could not rank: {error}</p>}
      {ranking && shown.length === 0 && (
        <p className="note">No experiment matches this fuel class and pillar together. Change one of them.</p>
      )}
      {shown.length > 0 && (
        <p className="quiet list-head">
          Click a row to see why.{' '}
          {shown.length >= 2 && (
            <>
              <Link to={`/dashboard/compare?ids=${shown.slice(0, 3).map((result) => result.psi_id).join(',')}&mission=${current.mission}`}>
                Compare the top {Math.min(3, shown.length)}
              </Link>
              {' · '}
            </>
          )}
          <Link to={`/dashboard/similar?${similar}`}>Find similar tests</Link>
        </p>
      )}
      <ol className="ranked">
        {shown.map((result, index) => (
          <li key={result.psi_id} className="reveal">
            <details open={index === 0}>
              <summary>
                <span className="place">{index + 1}</span>
                <span className="who">
                  <Link to={`/dashboard/${result.psi_id}`}>{result.name}</Link>
                  <small>
                    {PILLAR_NAMES[result.pillar]} · {result.fuel_class ?? 'no fuel class'}
                  </small>
                </span>
                <Meter score={result.score} />
                <span className="total">{points(result.score)}</span>
              </summary>
              {result.one_line && (
                <p className="one-line">
                  <span className="ai-tag">AI</span> {result.one_line}
                </p>
              )}
              <div className="factors">
                {result.factors.map((factor) => (
                  <FactorCell key={factor.id} factor={factor} />
                ))}
              </div>
            </details>
          </li>
        ))}
      </ol>
    </section>
  )
}
