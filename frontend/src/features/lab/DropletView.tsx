import { useEffect, useState } from 'react'
import { FlameCanvas } from './FlameCanvas.tsx'
import { figure } from './types.ts'
import type { SimState } from './types.ts'

const W = 360
const H = 200
const PLOT = { left: 44, right: 348, top: 12, bottom: 166 }

/** Diameter squared at time t, read off the simulated curve. */
function d2At(curve: { t_s: number; d2_mm2: number }[], t: number): number {
  for (let i = 1; i < curve.length; i++) {
    if (t <= curve[i].t_s) {
      const [a, b] = [curve[i - 1], curve[i]]
      return a.d2_mm2 + ((t - a.t_s) / (b.t_s - a.t_s)) * (b.d2_mm2 - a.d2_mm2)
    }
  }
  return curve[curve.length - 1].d2_mm2
}

export function DropletView({ state, fuel }: { state: SimState; fuel: string }) {
  const curve = state.d2_curve ?? []
  const end = state.burn_time_s ?? 0
  const calm = typeof window !== 'undefined' && window.matchMedia('(prefers-reduced-motion: reduce)').matches
  const [t, setT] = useState(calm ? end : 0)
  const [playing, setPlaying] = useState(!calm)
  const [probe, setProbe] = useState<number | null>(null)

  useEffect(() => {
    if (!playing) return
    let last = performance.now()
    let frame = requestAnimationFrame(function step(now) {
      setT((before) => Math.min(end, before + (now - last) / 1000))
      last = now
      frame = requestAnimationFrame(step)
    })
    return () => cancelAnimationFrame(frame)
  }, [playing, end])

  if (curve.length < 2) return null
  const out = t >= end
  const diameter = Math.sqrt(d2At(curve, t))
  // A faster burn is drawn brighter, up to full brightness at 1 mm²/s. Illustration only.
  const intensity = Math.min(1, Math.max(0.25, state.burning_rate_mm2_s ?? 0.5))
  const sx = (time: number) => PLOT.left + (time / end) * (PLOT.right - PLOT.left)
  const sy = (d2: number) => PLOT.bottom - (d2 / curve[0].d2_mm2) * (PLOT.bottom - PLOT.top)
  const shownAt = probe ?? t

  return (
    <div className="droplet-view">
      <FlameCanvas diameterMm={diameter < 0.01 ? 0 : diameter} burning={!out} intensity={intensity} fuel={fuel} />
      <p className="caption" aria-live="off">
        {!out ? `${t.toFixed(1)} s · droplet ${figure(diameter)} mm` : diameter < 0.01 ? `The droplet burns away at ${figure(end)} s.` : `Flame out at ${figure(end)} s. Droplet left: ${figure(diameter)} mm.`}
      </p>

      <p className="transport">
        <button onClick={() => (out ? (setT(0), setPlaying(true)) : setPlaying(!playing))}>{out ? 'Replay' : playing ? 'Pause' : 'Play'}</button>
        <input type="range" min={0} max={end} step={end / 200} value={t} aria-label="Time" onChange={(event) => (setPlaying(false), setT(event.target.valueAsNumber))} />
      </p>

      <svg
        viewBox={`0 0 ${W} ${H}`}
        className="curve"
        role="img"
        aria-label="Droplet diameter squared against time"
        onPointerMove={(event) => {
          const box = event.currentTarget.getBoundingClientRect()
          const x = ((event.clientX - box.left) / box.width) * W
          setProbe(Math.min(end, Math.max(0, ((x - PLOT.left) / (PLOT.right - PLOT.left)) * end)))
        }}
        onPointerLeave={() => setProbe(null)}
      >
        {[0, 0.5, 1].map((share) => (
          <g key={share}>
            <line className="grid" x1={PLOT.left} x2={PLOT.right} y1={sy(curve[0].d2_mm2 * share)} y2={sy(curve[0].d2_mm2 * share)} />
            <text className="tick" x={PLOT.left - 6} y={sy(curve[0].d2_mm2 * share)} textAnchor="end" dominantBaseline="middle">
              {figure(curve[0].d2_mm2 * share)}
            </text>
            <text className="tick" x={sx(end * share)} y={PLOT.bottom + 14} textAnchor="middle">
              {figure(end * share)}
            </text>
          </g>
        ))}
        <polyline className="line" points={curve.map((point) => `${sx(point.t_s)},${sy(point.d2_mm2)}`).join(' ')} />
        <line className="cross" x1={sx(shownAt)} x2={sx(shownAt)} y1={PLOT.top} y2={PLOT.bottom} />
        <circle className="dot" cx={sx(shownAt)} cy={sy(d2At(curve, shownAt))} r={4.5} />
        <text className="tick" x={(PLOT.left + PLOT.right) / 2} y={H - 4} textAnchor="middle">
          Time (s)
        </text>
      </svg>
      <p className="readout">
        Diameter squared: <strong>{figure(d2At(curve, shownAt))} mm²</strong> at {shownAt.toFixed(1)} s
      </p>
      <p className="quiet">
        A schematic. The droplet's size follows the simulation. The flame's size, colour and glow are drawn for illustration, because
        FLEX records none of them.
      </p>
    </div>
  )
}
