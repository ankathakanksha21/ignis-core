import { useState } from 'react'
import { Link } from 'react-router-dom'
import { useApi } from '../../api/useApi.ts'
import { AtmospheresNav } from './AtmospheresNav.tsx'

type Flag = { psi_id: string; name: string; file_name: string; row: number; column: string; cell: string; check: string; detail: string }

type Report = {
  checks: { check: string; count: number; meaning: string }[]
  investigations: { psi_id: string; name: string; rows: number; flags: number; not_tests: number }[]
  flags: Flag[]
  not_tests: { psi_id: string; name: string; file_name: string; row: number; why: string }[]
}

const plain = (check: string) => check.replaceAll('_', ' ')

export function QualityPage() {
  const { data, error } = useApi<Report>('/atmospheres/quality')
  const [investigation, setInvestigation] = useState('all')
  const [check, setCheck] = useState('all')

  if (error) return <p role="alert">Could not load the data quality report: {error}</p>
  if (!data) return <p>Loading…</p>

  const shown = data.flags.filter((f) => (investigation === 'all' || f.psi_id === investigation) && (check === 'all' || f.check === check))
  const reasons = new Map<string, number>()
  for (const row of data.not_tests) reasons.set(row.why, (reasons.get(row.why) ?? 0) + 1)

  return (
    <section className="atmospheres">
      <h1>Exploration atmospheres</h1>
      <AtmospheresNav />
      <p className="lede">
        {data.flags.length} cells in NASA's test tables look wrong. They are flagged here and left unchanged in the data. The checks
        are this project's, not NASA's.
      </p>

      <h2>What was checked</h2>
      <table>
        <thead>
          <tr>
            <th>Check</th>
            <th>Cells</th>
            <th>What it means</th>
          </tr>
        </thead>
        <tbody>
          {data.checks.map((c) => (
            <tr key={c.check}>
              <td>{plain(c.check)}</td>
              <td>{c.count}</td>
              <td>{c.meaning}</td>
            </tr>
          ))}
        </tbody>
      </table>

      <h2>Flagged cells</h2>
      <p className="pickers">
        <select value={investigation} onChange={(event) => setInvestigation(event.target.value)} aria-label="Investigation">
          <option value="all">All investigations</option>
          {data.investigations
            .filter((i) => i.flags > 0)
            .map((i) => (
              <option key={i.psi_id} value={i.psi_id}>
                {i.name} ({i.flags})
              </option>
            ))}
        </select>
        <select value={check} onChange={(event) => setCheck(event.target.value)} aria-label="Check">
          <option value="all">All checks</option>
          {data.checks.map((c) => (
            <option key={c.check} value={c.check}>
              {plain(c.check)} ({c.count})
            </option>
          ))}
        </select>
        <span className="quiet">{shown.length} shown</span>
      </p>
      <div className="scroll">
        <table className="wide">
          <thead>
            <tr>
              <th>Investigation</th>
              <th>Row</th>
              <th>Column</th>
              <th>Cell as published</th>
              <th>Check</th>
              <th>Why</th>
            </tr>
          </thead>
          <tbody>
            {shown.map((f) => (
              <tr key={`${f.file_name}-${f.row}-${f.column}-${f.check}`}>
                <td>
                  <Link to={`/dashboard/${f.psi_id}`}>{f.name}</Link>
                </td>
                <td>{f.row}</td>
                <td>{f.column.trim()}</td>
                <td>
                  <code>{f.cell || '(empty)'}</code>
                </td>
                <td>{plain(f.check)}</td>
                <td>{f.detail}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <h2>Rows that are not tests</h2>
      <p className="quiet">
        {data.not_tests.length} rows of the tables are not tests, so they are never counted: {[...reasons].map(([why, count]) => `${count} ${why}`).join('; ')}.
      </p>

      <h2>By investigation</h2>
      <table>
        <thead>
          <tr>
            <th>Investigation</th>
            <th>Rows</th>
            <th>Flagged cells</th>
            <th>Not tests</th>
          </tr>
        </thead>
        <tbody>
          {data.investigations.map((i) => (
            <tr key={i.psi_id}>
              <td>
                <Link to={`/dashboard/${i.psi_id}`}>{i.name}</Link>
              </td>
              <td>{i.rows}</td>
              <td>{i.flags}</td>
              <td>{i.not_tests}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </section>
  )
}
