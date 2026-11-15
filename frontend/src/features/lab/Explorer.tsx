import { useState } from 'react'
import { Link } from 'react-router-dom'
import { useApi } from '../../api/useApi.ts'
import { AiExplain } from '../voice/AiExplain.tsx'
import { figure } from './types.ts'
import type { Flex, FlexRow } from './types.ts'

const W = 720
const H = 400
const PLOT = { left: 58, right: 700, top: 16, bottom: 346 }
const GROUPS = [
  { key: 'fuel', label: 'Fuel' },
  { key: 'test_end', label: 'How the test ended' },
]

/** About five round tick values covering low to high. */
function ticks(low: number, high: number): number[] {
  const rough = (high - low) / 5 || 1
  const power = 10 ** Math.floor(Math.log10(rough))
  const step = [1, 2, 5, 10].map((m) => m * power).find((s) => s >= rough) ?? rough
  const out = []
  const last = Math.ceil(high / step - 1e-9) * step // the top tick sits at or above the largest value
  for (let v = Math.floor(low / step) * step; v <= last + step * 0.01; v += step) out.push(Number(v.toPrecision(10)))
  return out
}

function Shape({ kind, x, y }: { kind: number; x: number; y: number }) {
  if (kind === 1) return <rect x={x - 4} y={y - 4} width={8} height={8} />
  if (kind === 2) return <rect x={x - 3.8} y={y - 3.8} width={7.6} height={7.6} transform={`rotate(45 ${x} ${y})`} />
  return <circle cx={x} cy={y} r={4.5} />
}

export function Explorer() {
  const { data, error } = useApi<Flex>('/lab/flex')
  const [xKey, setX] = useState('o2_percent')
  const [yKey, setY] = useState('burning_rate')
  const [groupKey, setGroup] = useState('fuel')
  const [hover, setHover] = useState<{ row: FlexRow; x: number; y: number } | null>(null)

  if (error) return <p role="alert">Could not load the FLEX tests: {error}</p>
  if (!data) return <p className="loading">Loading…</p>

  const field = (key: string) => data.fields.find((f) => f.key === key)!
  const points = data.rows.filter((row) => typeof row[xKey] === 'number' && typeof row[yKey] === 'number')
  const groups = [...new Set(data.rows.map((row) => String(row[groupKey])))].sort()
  const xs = points.map((row) => row[xKey] as number)
  const ys = points.map((row) => row[yKey] as number)
  const xTicks = ticks(Math.min(...xs), Math.max(...xs))
  const yTicks = ticks(Math.min(0, ...ys), Math.max(...ys))
  const sx = (v: number) => PLOT.left + ((v - xTicks[0]) / (xTicks.at(-1)! - xTicks[0] || 1)) * (PLOT.right - PLOT.left)
  const sy = (v: number) => PLOT.bottom - ((v - yTicks[0]) / (yTicks.at(-1)! - yTicks[0] || 1)) * (PLOT.bottom - PLOT.top)
  const axis = (key: string) => `${field(key).label} (${field(key).unit})`
  const picker = (value: string, set: (key: string) => void, label: string) => (
    <label>
      {label}{' '}
      <select value={value} onChange={(event) => set(event.target.value)}>
        {data.fields.map((f) => (
          <option key={f.key} value={f.key}>
            {f.label}
          </option>
        ))}
      </select>
    </label>
  )

  return (
    <>
      <p className="lede center">Each point is one real NASA test.</p>
      <p className="pickers">
        {picker(xKey, setX, 'Across')}
        {picker(yKey, setY, 'Up')}
        <label>
          Colour by{' '}
          <select value={groupKey} onChange={(event) => setGroup(event.target.value)}>
            {GROUPS.map((g) => (
              <option key={g.key} value={g.key}>
                {g.label}
              </option>
            ))}
          </select>
        </label>
      </p>

      <figure className="viz">
        <figcaption>
          <strong>
            {field(yKey).label} against {field(xKey).label.toLowerCase()}
          </strong>
          <span>
            {points.length} of {data.rows.length} tests record both. Hollow marks are rows with a flagged cell.
          </span>
        </figcaption>
        <ul className="legend">
          {groups.map((name, index) => (
            <li key={name}>
              <svg viewBox="-8 -8 16 16" className={`series-${index}`} aria-hidden="true">
                <Shape kind={index} x={0} y={0} />
              </svg>
              {name}
            </li>
          ))}
        </ul>
        <div className="plot">
          <div className="plot-inner">
            <svg viewBox={`0 0 ${W} ${H}`} role="img" aria-label={`${axis(yKey)} against ${axis(xKey)} for the FLEX tests`}>
              {yTicks.map((v) => (
                <g key={v}>
                  <line className="grid" x1={PLOT.left} x2={PLOT.right} y1={sy(v)} y2={sy(v)} />
                  <text className="tick" x={PLOT.left - 8} y={sy(v)} textAnchor="end" dominantBaseline="middle">
                    {v}
                  </text>
                </g>
              ))}
              {xTicks.map((v) => (
                <text key={v} className="tick" x={sx(v)} y={PLOT.bottom + 16} textAnchor="middle">
                  {v}
                </text>
              ))}
              <line className="axis" x1={PLOT.left} x2={PLOT.right} y1={PLOT.bottom} y2={PLOT.bottom} />
              <text className="axis-title" x={(PLOT.left + PLOT.right) / 2} y={H - 10} textAnchor="middle">
                {axis(xKey)}
              </text>
              <text className="axis-title" x={14} y={(PLOT.top + PLOT.bottom) / 2} textAnchor="middle" transform={`rotate(-90 14 ${(PLOT.top + PLOT.bottom) / 2})`}>
                {axis(yKey)}
              </text>
              {points.map((row) => {
                const x = sx(row[xKey] as number)
                const y = sy(row[yKey] as number)
                return (
                  <g
                    key={row.row}
                    className={`mark series-${groups.indexOf(String(row[groupKey]))}${row.flagged ? ' flagged' : ''}`}
                    tabIndex={0}
                    onPointerEnter={() => setHover({ row, x, y })}
                    onPointerLeave={() => setHover(null)}
                    onFocus={() => setHover({ row, x, y })}
                    onBlur={() => setHover(null)}
                  >
                    <circle className="hit" cx={x} cy={y} r={11} />
                    <Shape kind={groups.indexOf(String(row[groupKey]))} x={x} y={y} />
                  </g>
                )
              })}
            </svg>
            {hover && (
              <div className="tip" style={{ left: `${(hover.x / W) * 100}%`, top: `${(hover.y / H) * 100}%` }} data-side={hover.x > W * 0.65 ? 'left' : 'right'}>
                <strong>
                  {figure(hover.row[yKey] as number)} {field(yKey).unit} at {figure(hover.row[xKey] as number)} {field(xKey).unit}
                </strong>
                <span>
                  {hover.row.fuel}, ended in {hover.row.test_end.toLowerCase()}
                </span>
                <span>
                  FLEX row {hover.row.row}
                  {hover.row.flagged && ', has a flagged cell'}
                </span>
              </div>
            )}
          </div>
        </div>
        <p className="quiet">
          Source: <Link to={`/dashboard/${data.source.psi_id}`}>{data.source.name}</Link>, {data.source.file_name}
          {data.source.doi && (
            <>
              ,{' '}
              <a href={`https://doi.org/${data.source.doi}`} target="_blank" rel="noreferrer">
                doi:{data.source.doi}
              </a>
            </>
          )}
          . {data.note}
        </p>
      </figure>
      <AiExplain kind="pattern" params={{ x: xKey, y: yKey, group: groupKey }} heading="What this plot shows" label="Listen and ask about this plot" />
    </>
  )
}
