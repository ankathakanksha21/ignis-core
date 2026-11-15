import { useEffect, useState } from 'react'
import type { ReactNode } from 'react'
import { Link, useSearchParams } from 'react-router-dom'
import { api } from '../../api/client.ts'
import { useApi } from '../../api/useApi.ts'
import { ConditionsChart } from './ConditionsChart.tsx'
import { DashboardNav } from './DashboardNav.tsx'
import { CONDITIONS, NOT_STATED, PILLAR_NAMES, gravity, range, testCount } from './format.ts'
import type { Detail, Listing, Missions, PointSeries } from './types.ts'

const DEFAULT_IDS = 'PSI-69,PSI-25,PSI-20' // a droplet study, a solid study and a gas-burner study

function conditionRange(detail: Detail, field: string, scale: number, unit: string): string {
  return range(detail.conditions[field], scale, unit)
}

function varied(detail: Detail): string {
  const columns = detail.tables.flatMap((table) => table.columns.filter((column) => column.distinct > 1))
  if (!columns.length) return NOT_STATED
  const names = [...new Set(columns.sort((a, b) => a.distinct - b.distinct).map((column) => column.name))]
  return names.slice(0, 6).join(', ') + (names.length > 6 ? ` and ${names.length - 6} more` : '')
}

const ROWS: { label: string; value: (detail: Detail) => ReactNode; text?: (detail: Detail) => string }[] = [
  { label: 'Pillar', value: (d) => PILLAR_NAMES[d.pillar] },
  { label: 'Fuel class', value: (d) => d.fuel_class ?? NOT_STATED },
  { label: 'Fuel', value: (d) => (d.fuels.length ? d.fuels.join(', ') + (d.fuel_count > d.fuels.length ? ` and ${d.fuel_count - d.fuels.length} more` : '') : NOT_STATED) },
  { label: 'Tests', value: testCount },
  { label: 'Gravity', value: gravity },
  { label: 'Hardware', value: (d) => d.shares_hardware?.hardware ?? d.hardware ?? NOT_STATED },
  ...CONDITIONS.map((c) => ({ label: c.label, value: (d: Detail) => conditionRange(d, c.field, c.scale, c.unit) })),
  { label: 'What varied', value: varied },
  { label: 'Flagged cells', value: (d) => String(d.flag_count) },
  {
    label: 'Cite as',
    text: (d) => d.doi ?? NOT_STATED,
    value: (d) => (d.doi ? <a href={`https://doi.org/${d.doi}`} target="_blank" rel="noreferrer">doi:{d.doi}</a> : NOT_STATED),
  },
]

export function ComparePage() {
  const [params, setParams] = useSearchParams()
  const ids = (params.get('ids') ?? DEFAULT_IDS).split(',').filter(Boolean).slice(0, 3)
  const missionId = params.get('mission') ?? 'moon'
  const key = ids.join(',')

  const { data: listing } = useApi<Listing>('/investigations')
  const { data: setup } = useApi<Missions>('/investigations/missions')
  const { data: points } = useApi<{ series: PointSeries[] }>(`/investigations/points?ids=${key}`)
  const [loaded, setLoaded] = useState<{ key: string; details: Detail[] } | null>(null)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    let live = true
    Promise.all(key.split(',').map((id) => api<Detail>(`/investigations/${id}`))).then(
      (details) => live && (setLoaded({ key, details }), setError(null)),
      (reason: Error) => live && setError(reason.message),
    )
    return () => {
      live = false
    }
  }, [key])

  const update = (next: { ids?: string[]; mission?: string }) =>
    setParams({ ids: (next.ids ?? ids).join(','), mission: next.mission ?? missionId }, { replace: true })
  const pick = (slot: number, id: string) => {
    const next = [...ids]
    if (id) next[slot] = id
    else next.splice(slot, 1)
    update({ ids: [...new Set(next)] })
  }

  if (error) return <p role="alert">Could not load the comparison: {error}</p>
  if (!listing || !setup) return <p>Loading…</p>
  const mission = setup.missions.find((m) => m.id === missionId) ?? setup.missions[0]
  const details = loaded?.key === key ? loaded.details : null

  return (
    <section className="dashboard compare">
      <h1>Compare investigations</h1>
      <DashboardNav />
      <p className="lede">Two or three investigations side by side, and where their tests sit against a habitat's atmosphere.</p>

      <p className="pickers">
        {[0, 1, 2].map((slot) => (
          <select key={slot} value={ids[slot] ?? ''} onChange={(event) => pick(slot, event.target.value)} aria-label={`Investigation ${slot + 1}`}>
            {slot >= 2 && <option value="">none</option>}
            {listing.investigations.map((card) => (
              <option key={card.psi_id} value={card.psi_id} disabled={ids.includes(card.psi_id) && ids[slot] !== card.psi_id}>
                {card.name}
              </option>
            ))}
          </select>
        ))}
      </p>

      {details && (
        <div className="scroll">
          <table className="side-by-side">
            <thead>
              <tr>
                <th />
                {details.map((detail) => (
                  <th key={detail.psi_id}>
                    <Link to={`/dashboard/${detail.psi_id}`}>{detail.name}</Link>
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {ROWS.map((row) => {
                const texts = details.map((detail) => (row.text ?? row.value)(detail))
                if (texts.every((text) => text === NOT_STATED)) return null // nothing to compare
                const same = details.length > 1 && texts.every((text) => text === texts[0])
                return (
                  <tr key={row.label} className={same ? 'same' : ''}>
                    <th>
                      {row.label}
                      {same && <small> same</small>}
                    </th>
                    {details.map((detail) => {
                      const value = row.value(detail)
                      return (
                        <td key={detail.psi_id} className={value === NOT_STATED ? 'missing' : ''}>
                          {value}
                        </td>
                      )
                    })}
                  </tr>
                )
              })}
            </tbody>
          </table>
        </div>
      )}

      <p className="filter">
        Habitat:{' '}
        {setup.missions.map((m) => (
          <button key={m.id} className={m.id === mission.id ? 'on' : ''} onClick={() => update({ mission: m.id })}>
            {m.label}
          </button>
        ))}
      </p>
      {mission.assumed && <p className="quiet">Assumption: {mission.assumed}</p>}
      {points && points.series.map((s) => s.psi_id).join(',') === key && <ConditionsChart series={points.series} mission={mission} />}
    </section>
  )
}
