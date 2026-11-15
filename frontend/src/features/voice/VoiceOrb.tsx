import { useEffect, useRef } from 'react'
import icon from '../../assets/voice-guide.webp'

export type OrbState = 'idle' | 'speaking' | 'listening'

type Props = {
  state: OrbState
  /**
   * The loudness of the sound right now, by pitch: the guide's voice while it speaks and the
   * listener's microphone while it listens. Without it the bars move on their own.
   */
  read?: () => Uint8Array | undefined
}

const SIZE = 104
const BARS = 60
const INNER = 34 // just outside the 56 px icon
const REACH = 15
const TAU = Math.PI * 2
const LISTENING = '#3987e5'

/** The guide's icon inside a ring of bars that rise and fall with the voice. */
export function VoiceOrb({ state, read }: Props) {
  const canvas = useRef<HTMLCanvasElement>(null)
  const latest = useRef({ state, read })
  useEffect(() => {
    latest.current = { state, read }
  })

  useEffect(() => {
    const element = canvas.current
    const context = element?.getContext('2d')
    if (!element || !context) return
    const calm = window.matchMedia('(prefers-reduced-motion: reduce)').matches
    const levels = new Array<number>(BARS).fill(0.04)
    const style = getComputedStyle(element)
    let frame = 0

    const draw = (now: number) => {
      const { state: mode, read: sample } = latest.current
      const t = now / 1000
      const density = window.devicePixelRatio || 1
      if (element.width !== Math.round(SIZE * density)) {
        element.width = element.height = Math.round(SIZE * density)
      }
      context.setTransform(density, 0, 0, density, 0, 0)
      context.clearRect(0, 0, SIZE, SIZE)

      let heard: Uint8Array | undefined
      try {
        heard = mode === 'idle' ? undefined : sample?.()
      } catch {
        heard = undefined // the conversation is not connected yet
      }
      const live = heard && heard.length > 0 && heard.some((value) => value > 0)
      let total = 0
      for (let bar = 0; bar < BARS; bar++) {
        const mirrored = bar < BARS / 2 ? bar : BARS - 1 - bar // the same on the left as on the right
        let target = 0.04
        if (calm) target = mode === 'idle' ? 0.04 : 0.3
        else if (live && heard) target = heard[Math.floor((mirrored / (BARS / 2)) * heard.length * 0.55)] / 255
        else if (mode === 'speaking') target = 0.18 + 0.62 * Math.abs(Math.sin(t * 4.1 + mirrored * 0.55) * Math.sin(t * 2.3 + mirrored * 1.1))
        else if (mode === 'listening') target = 0.1 + 0.07 * Math.sin(t * 2 + mirrored * 0.4)
        levels[bar] += (target - levels[bar]) * (calm ? 1 : 0.32)
        total += levels[bar]
      }

      const colour = mode === 'speaking' ? style.getPropertyValue('--accent').trim() || '#ff5c03' : mode === 'listening' ? LISTENING : style.getPropertyValue('--faint').trim() || '#7c7c7c'
      const centre = SIZE / 2
      const loud = total / BARS
      if (mode !== 'idle') {
        const glow = context.createRadialGradient(centre, centre, INNER - 6, centre, centre, SIZE / 2)
        glow.addColorStop(0, colour)
        glow.addColorStop(1, 'transparent')
        context.globalAlpha = Math.min(0.5, 0.08 + loud * 0.7)
        context.fillStyle = glow
        context.beginPath()
        context.arc(centre, centre, SIZE / 2, 0, TAU)
        context.fill()
      }
      context.strokeStyle = colour
      context.lineCap = 'round'
      context.lineWidth = 2.1
      for (let bar = 0; bar < BARS; bar++) {
        const angle = (bar / BARS) * TAU - Math.PI / 2
        const [cos, sin] = [Math.cos(angle), Math.sin(angle)]
        const outer = INNER + 2 + levels[bar] * REACH
        context.globalAlpha = 0.35 + 0.65 * Math.min(1, levels[bar] * 1.4)
        context.beginPath()
        context.moveTo(centre + cos * INNER, centre + sin * INNER)
        context.lineTo(centre + cos * outer, centre + sin * outer)
        context.stroke()
      }
      context.globalAlpha = 1
      frame = requestAnimationFrame(draw)
    }
    frame = requestAnimationFrame(draw)
    return () => cancelAnimationFrame(frame)
  }, [])

  return (
    <span className={`voice-orb ${state}`}>
      <canvas ref={canvas} aria-hidden="true" />
      <img src={icon} alt="" width={56} height={56} />
    </span>
  )
}
