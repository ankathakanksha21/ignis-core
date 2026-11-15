import { useEffect, useRef } from 'react'

// A drawing of a droplet burning in microgravity: a liquid sphere inside a
// spherical flame, with fuel vapour drifting out to it. Only the droplet's
// size comes from the simulation. Everything else is illustration.

type Props = {
  /** Droplet diameter now, from the simulated curve. 0 once it has burned away. */
  diameterMm: number
  burning: boolean
  /** 0 to 1: how bright to draw the flame. A faster burning rate is drawn brighter. */
  intensity: number
  fuel: string
}

const W = 360
const H = 250
const CX = W / 2
const CY = H / 2
const PX_PER_MM = 26
const VAPOUR = 70
const SOOT = 46
const TAU = Math.PI * 2

type Rgb = [number, number, number]
type Particle = { angle: number; along: number; speed: number; size: number; swirl: number }

const rgba = ([r, g, b]: Rgb, alpha: number) => `rgba(${r}, ${g}, ${b}, ${Math.max(0, Math.min(1, alpha))})`

/** A slow ripple round the flame, so the sphere breathes without ever looking like a candle. */
function ripple(theta: number, t: number): number {
  return 0.55 * Math.sin(3 * theta + 1.3 * t) + 0.3 * Math.sin(5 * theta - 2.1 * t) + 0.15 * Math.sin(9 * theta + 3.7 * t)
}

function newParticle(along = 0): Particle {
  return {
    angle: Math.random() * TAU,
    along,
    speed: 0.25 + Math.random() * 0.45,
    size: 0.5 + Math.random() * 1.1,
    swirl: (Math.random() - 0.5) * 0.5,
  }
}

export function FlameCanvas(props: Props) {
  const canvas = useRef<HTMLCanvasElement>(null)
  const latest = useRef(props)
  useEffect(() => {
    latest.current = props
  })

  useEffect(() => {
    const element = canvas.current
    const context = element?.getContext('2d')
    if (!element || !context) return
    const calm = window.matchMedia('(prefers-reduced-motion: reduce)').matches
    const particles = Array.from({ length: VAPOUR }, () => newParticle(Math.random()))
    let lit = latest.current.burning ? 1 : 0 // 0 to 1, eased, so the flame fades in and out
    let puff = 1 // 0 to 1 progress of the ring that drifts off at flame-out. 1 means none
    let wasBurning = latest.current.burning
    let last = performance.now()
    let frame = 0

    const draw = (now: number) => {
      const dt = calm ? 0 : Math.min(0.05, (now - last) / 1000)
      last = now
      const t = calm ? 0 : now / 1000
      const { diameterMm, burning, intensity, fuel } = latest.current
      const sooty = fuel === 'heptane'
      const shell: Rgb = sooty ? [86, 156, 255] : [132, 130, 255]
      const core: Rgb = sooty ? [205, 230, 255] : [214, 212, 255]

      // Match the canvas to its box, at the screen's pixel density.
      const density = window.devicePixelRatio || 1
      const wide = Math.max(1, Math.round(element.clientWidth * density))
      if (element.width !== wide) {
        element.width = wide
        element.height = Math.round((wide * H) / W)
      }
      context.setTransform(element.width / W, 0, 0, element.width / W, 0, 0)

      if (burning !== wasBurning) {
        if (!burning) puff = 0
        wasBurning = burning
      }
      lit = calm ? (burning ? 1 : 0) : lit + ((burning ? 1 : 0) - lit) * Math.min(1, dt * (burning ? 6 : 2.4))
      if (puff < 1) puff = Math.min(1, puff + dt / 1.6)

      const r = Math.max(0, (diameterMm * PX_PER_MM) / 2) * (1 + 0.012 * Math.sin(t * 5))
      const flicker = 0.93 + 0.07 * Math.sin(t * 11) * Math.sin(t * 3.1)
      const glow = lit * (0.5 + 0.5 * intensity) * flicker
      // The flame sits a fixed distance outside the droplet, and swells a little as it dies.
      const reach = (r + 36 + 12 * intensity) * (1 + 0.22 * (1 - lit)) * (1 + 0.012 * Math.sin(t * 2.3))

      // The chamber.
      context.globalCompositeOperation = 'source-over'
      const room = context.createRadialGradient(CX, CY, 10, CX, CY, W * 0.62)
      room.addColorStop(0, '#0c1428')
      room.addColorStop(0.6, '#060a16')
      room.addColorStop(1, '#020308')
      context.fillStyle = room
      context.fillRect(0, 0, W, H)

      context.globalCompositeOperation = 'lighter'
      if (glow > 0.005) {
        // Light spilling into the chamber.
        const halo = context.createRadialGradient(CX, CY, reach * 0.4, CX, CY, reach * 1.75)
        halo.addColorStop(0, rgba(shell, 0))
        halo.addColorStop(0.45, rgba(shell, 0.2 * glow))
        halo.addColorStop(1, rgba(shell, 0))
        context.fillStyle = halo
        context.beginPath()
        context.arc(CX, CY, reach * 1.75, 0, TAU)
        context.fill()

        if (sooty) {
          // Heptane burns with a warm glow inside the blue.
          const warm = context.createRadialGradient(CX, CY, r, CX, CY, reach * 0.85)
          warm.addColorStop(0, rgba([255, 176, 84], 0.2 * glow))
          warm.addColorStop(1, rgba([255, 150, 60], 0))
          context.fillStyle = warm
          context.beginPath()
          context.arc(CX, CY, reach * 0.85, 0, TAU)
          context.fill()
        }

        // The flame: a thin bright shell, drawn three times from soft to sharp.
        context.beginPath()
        for (let step = 0; step <= 96; step++) {
          const theta = (step / 96) * TAU
          const radius = reach * (1 + 0.022 * ripple(theta, t))
          const [x, y] = [CX + radius * Math.cos(theta), CY + radius * Math.sin(theta)]
          if (step === 0) context.moveTo(x, y)
          else context.lineTo(x, y)
        }
        context.closePath()
        context.shadowColor = rgba(shell, 0.9)
        context.shadowBlur = 22
        context.lineWidth = 15
        context.strokeStyle = rgba(shell, 0.1 * glow)
        context.stroke()
        context.shadowBlur = 10
        context.lineWidth = 6.5
        context.strokeStyle = rgba(shell, 0.34 * glow)
        context.stroke()
        context.shadowBlur = 0
        context.lineWidth = 2
        context.strokeStyle = rgba(core, 0.85 * glow)
        context.stroke()

        if (sooty) {
          // A loose shell of glowing soot between the droplet and the flame.
          const ring = r + (reach - r) * 0.42
          for (let index = 0; index < SOOT; index++) {
            const theta = index * 2.399963 + t * 0.07
            const radius = ring + 3.5 * Math.sin(index * 12.9898)
            const twinkle = 0.5 + 0.5 * Math.sin(t * 3 + index * 1.7)
            context.fillStyle = rgba([255, 196, 104], 0.5 * glow * twinkle)
            context.beginPath()
            context.arc(CX + radius * Math.cos(theta), CY + radius * Math.sin(theta), 0.8 + 0.7 * twinkle, 0, TAU)
            context.fill()
          }
        }

        // Fuel vapour leaving the droplet and reaching the flame.
        for (const particle of particles) {
          particle.along += particle.speed * dt
          particle.angle += particle.swirl * dt
          if (particle.along >= 1) Object.assign(particle, newParticle())
          const radius = r + particle.along * Math.max(4, reach - r - 2)
          const alpha = Math.sin(Math.PI * particle.along) * 0.55 * lit
          context.fillStyle = rgba(particle.along > 0.7 ? core : [190, 214, 245], alpha)
          context.beginPath()
          context.arc(CX + radius * Math.cos(particle.angle), CY + radius * Math.sin(particle.angle), particle.size, 0, TAU)
          context.fill()
        }
      }

      if (puff < 1) {
        // Flame-out: the last of the hot gas drifts outward and fades.
        context.lineWidth = 1.5 + 5 * puff
        context.strokeStyle = rgba([170, 192, 226], 0.22 * (1 - puff))
        context.beginPath()
        context.arc(CX, CY, reach * (1 + 0.55 * puff), 0, TAU)
        context.stroke()
      }

      context.globalCompositeOperation = 'source-over'
      if (r > 0.3) {
        // The droplet: a liquid sphere lit from its upper left, with the flame's colour on its rim.
        const liquid = context.createRadialGradient(CX - r * 0.35, CY - r * 0.4, r * 0.05, CX, CY, r)
        liquid.addColorStop(0, 'rgba(255, 255, 255, 0.96)')
        liquid.addColorStop(0.22, 'rgba(202, 218, 238, 0.92)')
        liquid.addColorStop(0.7, 'rgba(98, 122, 152, 0.94)')
        liquid.addColorStop(1, 'rgba(28, 40, 58, 0.97)')
        context.fillStyle = liquid
        context.beginPath()
        context.arc(CX, CY, r, 0, TAU)
        context.fill()
        context.lineWidth = Math.min(1.6, r * 0.2)
        context.strokeStyle = rgba(sooty ? [255, 190, 120] : shell, 0.55 * lit)
        context.stroke()
        context.fillStyle = 'rgba(255, 255, 255, 0.85)'
        context.beginPath()
        context.ellipse(CX - r * 0.36, CY - r * 0.42, r * 0.17, r * 0.1, -0.6, 0, TAU)
        context.fill()
      }

      // Darker towards the edge, like a view through a chamber window.
      const edge = context.createRadialGradient(CX, CY, H * 0.35, CX, CY, W * 0.62)
      edge.addColorStop(0, 'rgba(0, 0, 0, 0)')
      edge.addColorStop(1, 'rgba(0, 0, 0, 0.6)')
      context.fillStyle = edge
      context.fillRect(0, 0, W, H)

      frame = requestAnimationFrame(draw)
    }
    frame = requestAnimationFrame(draw)
    return () => cancelAnimationFrame(frame)
  }, [])

  return <canvas ref={canvas} className="flame" role="img" aria-label="A burning droplet in microgravity, drawn as a schematic" />
}
