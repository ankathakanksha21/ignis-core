import { useEffect, useState } from 'react'
import { useTitle } from '../../useTitle.ts'
import { Link, useSearchParams } from 'react-router-dom'
import { testLink } from '../../testLink.ts'
import { useStored } from '../../useStored.ts'
import { api } from '../../api/client.ts'
import { useApi } from '../../api/useApi.ts'
import { DashboardNav } from './DashboardNav.tsx'
import { NOT_STATED, range } from './format.ts'
import type { Missions, Similar } from './types.ts'

const FIELDS = [
  { field: 'o2_mole_fraction', label: 'Oxygen', unit: '%', scale: 100 },
  { field: 'pressure_kpa', label: 'Pressure', unit: 'kPa', scale: 1 },
  { field: 'flow_cm_s', label: 'Flow', unit: 'cm/s', scale: 1 },
]

type Inputs = { o2_mole_fraction: string; pressure_kpa: string; flow_cm_s: string; fuel_class: string }

const FUEL_CLASSES = ['solid', 'droplet', 'gas', 'smoke']

/** Conditions carried in the address, as the Rank page's "Find similar tests" link sends them. */
function fromLink(params: URLSearchParams): Inputs | undefined {
  if (!['o2', 'pressure', 'flow', 'fuel'].some((name) => params.has(name))) return undefined
  const fuel = params.get('fuel') ?? ''
  return {
    o2_mole_fraction: params.get('o2') ?? '',
    pressure_kpa: params.get('pressure') ?? '',
    flow_cm_s: params.get('flow') ?? '',
    fuel_class: FUEL_CLASSES.includes(fuel) ? fuel : '',
  }
}

export function SimilarPage() {
  const { data: setup } = useApi<Missions>('/investigations/missions')
  const [params, setParams] = useSearchParams()
  // Kept for the tab, so the search is still here after a visit to another page. A link's own conditions win.
  const [inputs, setInputs] = useStored<Inputs>(
    'similar.inputs',
    { o2_mole_fraction: '30', pressure_kpa: '70.3', flow_cm_s: '', fuel_class: '' },
    fromLink(params),
  )
  const carried = params.toString() !== ''
  useEffect(() => {
    // Once read, drop them from the address so a reload keeps what was typed since.
    if (carried) setParams({}, { replace: true })
  }, [carried, setParams])
  const [found, setFound] = useState<Similar | null>(null)
  const [error, setError] = useState<string | null>(null)
  const request = JSON.stringify(inputs)
  useTitle('Similar tests')

  useEffect(() => {
    const typed: Inputs = JSON.parse(request)
    const body: Record<string, number | string> = {}
    for (const { field, scale } of FIELDS) {
      const value = Number(typed[field as keyof Inputs])
      if (typed[field as keyof Inputs] !== '' && Number.isFinite(value)) body[field] = value / scale
    }
    if (typed.fuel_class) body.fuel_class = typed.fuel_class
    if (Object.keys(body).filter((key) => key !== 'fuel_class').length === 0) return
    let live = true
    api<Similar>('/investigations/similar', body).then(
      (result) => live && (setFound(result), setError(null)),
      (reason: Error) => live && setError(reason.message),
    )
    return () => {
      live = false
    }
  }, [request])

  const change = (patch: Partial<Inputs>) => setInputs({ ...inputs, ...patch })

  return (
    <section className="dashboard similar">
      <header className="hero">
        <p className="eyebrow">Similar tests</p>
        <h1>
          Find the closest <span className="dim">real tests.</span>
        </h1>
        <p className="lede">Enter your conditions. Leave a box empty to skip it.</p>
        <DashboardNav />
      </header>

      {setup && (
        <p className="filter">
          Fill from:{' '}
          {setup.missions.map((m) => (
            <button key={m.id} onClick={() => change({ o2_mole_fraction: String(m.o2_mole_fraction * 100), pressure_kpa: String(m.pressure_kpa) })}>
              {m.label}
            </button>
          ))}
        </p>
      )}
      <p className="conditions">
        {FIELDS.map(({ field, label, unit }) => (
          <label key={field}>
            {label}{' '}
            <input type="number" min={0} step="any" value={inputs[field as keyof Inputs]} onChange={(event) => change({ [field]: event.target.value })} /> {unit}
          </label>
        ))}
        <label>
          Fuel class{' '}
          <select value={inputs.fuel_class} onChange={(event) => change({ fuel_class: event.target.value })}>
            <option value="">any</option>
            {FUEL_CLASSES.map((name) => (
              <option key={name}>{name}</option>
            ))}
          </select>
        </label>
      </p>

      {error && <p role="alert">Could not search: {error}</p>}
      {found?.nothing_close && (
        <p className="note">
          No real test is close to these conditions. The nearest rows are below, so you can see how far away they are.
        </p>
      )}
      {found && (
        <div className="scroll">
          <table className="side-by-side similar-table">
            <thead>
              <tr>
                <th>Test</th>
                <th>Fuel</th>
                {FIELDS.map(({ label }) => (
                  <th key={label}>{label}</th>
                ))}
                <th>Closeness</th>
              </tr>
            </thead>
            <tbody>
              {found.results.map((row) => {
                const closeness = Math.round(Math.max(0, 1 - row.distance) * 100)
                return (
                  <tr key={`${row.file_name}-${row.row}`}>
                    <td>
                      <Link to={`/dashboard/${row.psi_id}`}>{row.name}</Link>,{' '}
                      <Link to={testLink(row.psi_id, row.file_name, [row.row])}>row {row.row}</Link>
                      {row.row_kind === 'summary' && <small> summary row</small>}
                    </td>
                    <td>{row.fuel ?? NOT_STATED}</td>
                    {FIELDS.map(({ field, unit, scale }) => (
                      <td key={field} className={row.values[field] ? '' : 'missing'}>
                        {range(row.values[field], scale, unit)}
                      </td>
                    ))}
                    <td>
                      <div className="meter" title={`${closeness} of 100`}>
                        <div style={{ width: `${closeness}%` }} />
                      </div>
                      {closeness}
                      {row.not_stated.length > 0 && <small> compared without {row.not_stated.map((f) => FIELDS.find((x) => x.field === f)?.label.toLowerCase()).join(' and ')}</small>}
                    </td>
                  </tr>
                )
              })}
            </tbody>
          </table>
        </div>
      )}
      {found && (
        <p className="quiet">
          Closeness is 100 for an exact match and falls to 0 one tolerance away:{' '}
          {FIELDS.filter(({ field }) => found.tolerance[field]).map(({ field, unit, scale }) => `${found.tolerance[field] * scale} ${unit === '%' ? 'oxygen points' : unit}`).join(', ')}
          . Rows that state everything you asked for come first.
        </p>
      )}
    </section>
  )
}
