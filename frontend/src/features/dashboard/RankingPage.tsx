import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { api } from '../../api/client.ts'
import { useApi } from '../../api/useApi.ts'
import { DashboardNav } from './DashboardNav.tsx'
import { NOT_STATED, PILLAR_NAMES } from './format.ts'
import type { Factor, Mission, Missions, Ranking } from './types.ts'

const KPA_PER_PSI = 6.894757
const points = (score: number) => Math.round(score * 100)

type Settings = { mission: string; oxygen: number; pressure: number; gravity: number; weights: Record<string, number> }

function settingsFor(mission: Mission, weights: Record<string, number>): Settings {
  return {
    mission: mission.id,
    oxygen: mission.o2_mole_fraction * 100,
    pressure: mission.pressure_kpa,
    gravity: mission.gravity_g,
    weights,
  }
}

function Meter({ score, thin = false }: { score: number; thin?: boolean }) {
  return (
    <div className={thin ? 'meter thin' : 'meter'} title={`${points(score)} of 100`}>
      <div style={{ width: `${points(score)}%` }} />
    </div>
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
  const [settings, setSettings] = useState<Settings | null>(null)
  const [ranking, setRanking] = useState<Ranking | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [pillar, setPillar] = useState('all')

  const defaults = setup ? Object.fromEntries(setup.factors.map((f) => [f.id, f.weight])) : {}
  const current = settings ?? (setup ? settingsFor(setup.missions[0], defaults) : null)
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
      weights: s.weights,
    }).then(
      (result) => live && (setRanking(result), setError(null)),
      (reason: Error) => live && setError(reason.message),
    )
    return () => {
      live = false
    }
  }, [request])

  if (setupError) return <p role="alert">Could not load the missions: {setupError}</p>
  if (!setup || !current) return <p>Loading…</p>

  const mission = setup.missions.find((m) => m.id === current.mission)!
  const shown = (ranking?.results ?? []).filter((result) => pillar === 'all' || result.pillar === pillar)
  const change = (patch: Partial<Settings>) => setSettings({ ...current, ...patch })
  const number = (key: 'oxygen' | 'pressure' | 'gravity', min: number, max: number, step: number) => (
    <input
      type="number"
      min={min}
      max={max}
      step={step}
      value={current[key]}
      onChange={(event) => {
        const value = event.target.valueAsNumber
        if (value >= min && value <= max) change({ [key]: value })
      }}
    />
  )

  return (
    <section className="dashboard ranking">
      <h1>Rank for a mission</h1>
      <DashboardNav />
      <p className="lede">
        Pick a mission and the investigations are ordered by how well their tests match it. The score is this project's
        heuristic, not a NASA rating.
      </p>

      <p className="filter">
        {setup.missions.map((m) => (
          <button key={m.id} className={m.id === current.mission ? 'on' : ''} onClick={() => setSettings(settingsFor(m, current.weights))}>
            {m.label}
          </button>
        ))}
      </p>

      <div className="controls">
        <fieldset>
          <legend>Habitat</legend>
          <label>Oxygen {number('oxygen', 0, 100, 1)} %</label>
          <label>
            Pressure {number('pressure', 1, 500, 0.1)} kPa <small>({(current.pressure / KPA_PER_PSI).toFixed(1)} psi)</small>
          </label>
          <label>Gravity {number('gravity', 0, 1, 0.01)} g</label>
          <p className="quiet">
            {mission.basis} {mission.assumed && <strong>Assumption: {mission.assumed}</strong>}
            {ranking && ranking.edited.length > 0 && ' You changed this profile.'}
          </p>
        </fieldset>

        <fieldset>
          <legend>Weights</legend>
          {setup.factors.map((f) => (
            <label key={f.id} className="weight">
              <span>{f.label}</span>
              <input
                type="range"
                min={0}
                max={5}
                step={1}
                value={current.weights[f.id]}
                onChange={(event) => change({ weights: { ...current.weights, [f.id]: event.target.valueAsNumber } })}
              />
              <span>{current.weights[f.id]}</span>
            </label>
          ))}
          <button onClick={() => change({ weights: defaults })}>Reset</button>
        </fieldset>
      </div>

      <details className="how">
        <summary>How the score works</summary>
        <ul>
          <li>The score is the weighted average of five factors, each from 0 to 100.</li>
          <li>
            Oxygen and pressure compare the habitat with the nearest value the investigation tested. A match scores 100 and falls
            to 0 at {setup.tolerance.o2_mole_fraction * 100} oxygen points or {setup.tolerance.pressure_kpa} kPa away.
          </li>
          <li>Oxygen fed through a burner is not counted as the atmosphere.</li>
          <li>Fuel type: {setup.fuel_relevance.map((f) => `${f.fuel_class} ${points(f.score)}`).join(', ')}.</li>
          <li>Gravity scores 100 only when the tests ran at the mission's gravity. PSI has no partial-gravity tests.</li>
          <li>A factor the data cannot answer scores 0, so missing data never helps.</li>
        </ul>
      </details>

      <p className="filter">
        Show:{' '}
        {['all', ...Object.keys(PILLAR_NAMES)].map((name) => (
          <button key={name} className={name === pillar ? 'on' : ''} onClick={() => setPillar(name)}>
            {PILLAR_NAMES[name] ?? 'all'}
          </button>
        ))}
      </p>
      {error && <p role="alert">Could not rank: {error}</p>}
      {shown.length >= 2 && (
        <p>
          <Link to={`/dashboard/compare?ids=${shown.slice(0, 3).map((result) => result.psi_id).join(',')}&mission=${current.mission}`}>
            Compare the top {Math.min(3, shown.length)}
          </Link>
        </p>
      )}
      <ol className="ranked">
        {shown.map((result, index) => (
          <li key={result.psi_id}>
            <span className="place">{index + 1}</span>
            <div className="who">
              <Link to={`/dashboard/${result.psi_id}`}>{result.name}</Link>
              <small>
                {PILLAR_NAMES[result.pillar]}, {result.fuel_class ?? 'no fuel class'}
              </small>
            </div>
            <Meter score={result.score} />
            <span className="total">{points(result.score)}</span>
            <div className="factors">
              {result.factors.map((factor) => (
                <FactorCell key={factor.id} factor={factor} />
              ))}
            </div>
          </li>
        ))}
      </ol>
    </section>
  )
}
