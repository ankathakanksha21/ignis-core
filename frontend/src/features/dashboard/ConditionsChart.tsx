import { useState } from 'react'
import type { Mission, Point, PointSeries } from './types.ts'

const KPA_PER_PSI = 6.894757
const W = 720
const H = 452
const PLOT = { left: 56, right: 700, top: 18, bottom: 300 }
const LANE = 386 // centre of the "pressure not stated" lane

function ticks(low: number, high: number, step: number): number[] {
  const out = []
  for (let v = low; v <= high + 1e-9; v += step) out.push(v)
  return out
}

function Shape({ kind, x, y, r }: { kind: number; x: number; y: number; r: number }) {
  if (kind === 1) return <rect x={x - r * 0.9} y={y - r * 0.9} width={r * 1.8} height={r * 1.8} />
  if (kind === 2) return <rect x={x - r * 0.85} y={y - r * 0.85} width={r * 1.7} height={r * 1.7} transform={`rotate(45 ${x} ${y})`} />
  return <circle cx={x} cy={y} r={r} />
}

type Hover = { x: number; y: number; point: Point; series: number }

export function ConditionsChart({ series, mission }: { series: PointSeries[]; mission: Mission }) {
  const [hover, setHover] = useState<Hover | null>(null)

  const oxygen = [mission.o2_mole_fraction, ...series.flatMap((s) => [...s.points, ...s.oxygen_only].map((p) => p.o2))].map((v) => v * 100)
  const pressure = [mission.pressure_kpa, ...series.flatMap((s) => s.points.map((p) => p.pressure_kpa ?? 0))]
  const x0 = Math.floor((Math.min(...oxygen) - 2) / 5) * 5
  const x1 = Math.ceil((Math.max(...oxygen) + 2) / 5) * 5
  const y1 = Math.ceil((Math.max(...pressure) * 1.05) / 50) * 50
  const sx = (percent: number) => PLOT.left + ((percent - x0) / (x1 - x0)) * (PLOT.right - PLOT.left)
  const sy = (kpa: number) => PLOT.bottom - (kpa / y1) * (PLOT.bottom - PLOT.top)
  const hx = sx(mission.o2_mole_fraction * 100)
  const hy = sy(mission.pressure_kpa)

  const marks = series
    .flatMap((s, index) => [
      ...s.points.map((point) => ({ point, series: index, x: sx(point.o2 * 100), y: sy(point.pressure_kpa ?? 0) })),
      ...s.oxygen_only.map((point) => ({ point, series: index, x: sx(point.o2 * 100), y: LANE + (index - (series.length - 1) / 2) * 13 })),
    ])
    .map((mark) => ({ ...mark, r: 4 + Math.min(4, (Math.sqrt(mark.point.rows.length) - 1) * 1.3) }))
    .sort((a, b) => b.r - a.r) // big marks first, so small ones stay on top

  return (
    <figure className="viz">
      <figcaption>
        <strong>Oxygen against pressure</strong>
        <span>Each mark is one tested combination. A bigger mark covers more rows of the table.</span>
      </figcaption>
      <ul className="legend">
        {series.map((s, index) => (
          <li key={s.psi_id}>
            <svg viewBox="-8 -8 16 16" className={`series-${index}`} aria-hidden="true">
              <Shape kind={index} x={0} y={0} r={5} />
            </svg>
            {s.name}
          </li>
        ))}
        <li>
          <svg viewBox="-8 -8 16 16" className="habitat" aria-hidden="true">
            <circle cx={0} cy={0} r={5} />
          </svg>
          {mission.label}: {mission.o2_mole_fraction * 100}% oxygen{mission.open_ended && ' or more'}, {mission.pressure_kpa} kPa
          {mission.open_ended && ' or less'}
        </li>
      </ul>

      <div className="plot">
        <svg viewBox={`0 0 ${W} ${H}`} role="img" aria-label={`Oxygen against pressure for ${series.map((s) => s.name).join(', ')}`}>
          {ticks(0, y1, y1 > 400 ? 100 : 50).map((kpa) => (
            <g key={kpa}>
              <line className="grid" x1={PLOT.left} x2={PLOT.right} y1={sy(kpa)} y2={sy(kpa)} />
              <text className="tick" x={PLOT.left - 8} y={sy(kpa)} textAnchor="end" dominantBaseline="middle">
                {kpa}
              </text>
            </g>
          ))}
          {ticks(x0, x1, x1 - x0 > 50 ? 10 : 5).map((percent) => (
            <text key={percent} className="tick" x={sx(percent)} y={PLOT.bottom + 16} textAnchor="middle">
              {percent}
            </text>
          ))}
          <line className="axis" x1={PLOT.left} x2={PLOT.right} y1={PLOT.bottom} y2={PLOT.bottom} />
          <text className="axis-title" x={(PLOT.left + PLOT.right) / 2} y={H - 8} textAnchor="middle">
            Oxygen in the atmosphere (%)
          </text>
          <text className="axis-title" x={14} y={(PLOT.top + PLOT.bottom) / 2} textAnchor="middle" transform={`rotate(-90 14 ${(PLOT.top + PLOT.bottom) / 2})`}>
            Pressure (kPa)
          </text>

          <line className="grid" x1={PLOT.left} x2={PLOT.right} y1={LANE - 52} y2={LANE - 52} />
          <text className="tick" x={PLOT.left} y={LANE - 36}>
            Pressure not stated or flagged
          </text>

          {mission.open_ended && <rect className="habitat-zone" x={hx} y={hy} width={PLOT.right - hx} height={PLOT.bottom - hy} />}
          <line className="habitat-line" x1={hx} x2={hx} y1={PLOT.top} y2={PLOT.bottom} />
          <line className="habitat-line" x1={hx} x2={hx} y1={LANE - 26} y2={LANE + 24} />
          <line className="habitat-line" x1={PLOT.left} x2={PLOT.right} y1={hy} y2={hy} />

          {marks.map((mark) => (
            <g
              key={`${mark.series}-${mark.point.o2}-${mark.point.pressure_kpa ?? 'none'}`}
              className={`mark series-${mark.series}`}
              tabIndex={0}
              onPointerEnter={() => setHover(mark)}
              onPointerLeave={() => setHover(null)}
              onFocus={() => setHover(mark)}
              onBlur={() => setHover(null)}
            >
              <circle className="hit" cx={mark.x} cy={mark.y} r={12} />
              <Shape kind={mark.series} x={mark.x} y={mark.y} r={mark.r} />
            </g>
          ))}

          <circle className="habitat-point" cx={hx} cy={hy} r={6} />
          <text className="habitat-label" x={hx + 10} y={hy - 9}>
            {mission.label}
          </text>
        </svg>

        {hover && (
          <div className="tip" style={{ left: `${(hover.x / W) * 100}%`, top: `${(hover.y / H) * 100}%` }} data-side={hover.x > W * 0.65 ? 'left' : 'right'}>
            <strong>
              {Number((hover.point.o2 * 100).toPrecision(3))}% oxygen
              {hover.point.pressure_kpa === undefined
                ? ', pressure not stated or flagged'
                : `, ${hover.point.pressure_kpa} kPa (${(hover.point.pressure_kpa / KPA_PER_PSI).toFixed(1)} psi)`}
            </strong>
            <span className={`key series-${hover.series}`}>{series[hover.series].name}</span>
            <span>
              {hover.point.rows.length === 1 ? 'Row' : `${hover.point.rows.length} rows:`} {hover.point.rows.slice(0, 6).join(', ')}
              {hover.point.rows.length > 6 && '…'}
              {hover.point.approximate && '. Approximate.'}
            </span>
          </div>
        )}
      </div>

      <ul className="notes">
        {series.map((s) => {
          const parts = []
          if (s.points.length) parts.push(`${s.points.length} oxygen and pressure combinations placed`)
          if (s.oxygen_only.length) {
            const levels = s.oxygen_only.length === 1 ? '1 oxygen level' : `${s.oxygen_only.length} oxygen levels`
            parts.push(`${levels} in the lower lane, with no usable pressure`)
          }
          if (!parts.length) parts.push('the table states no oxygen')
          if (s.rows_not_placed) parts.push(`${s.rows_not_placed} rows list oxygen levels and pressures separately, so they cannot be placed`)
          if (s.rows_burner_fed) parts.push(`${s.rows_burner_fed} inverse-flame rows are left out because their oxygen is fed through the burner`)
          return (
            <li key={s.psi_id}>
              {s.name}: {parts.join('; ')}.
            </li>
          )
        })}
      </ul>
    </figure>
  )
}
