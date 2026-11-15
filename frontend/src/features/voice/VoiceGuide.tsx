import { Suspense, lazy, useState } from 'react'
import { createPortal } from 'react-dom'
import icon from '../../assets/voice-guide.webp'
import './voice.css'

// The panel pulls in the ElevenLabs client, so it is loaded only when someone asks for an explanation.
const VoicePanel = lazy(() => import('./VoicePanel.tsx'))

export type VoiceKind = 'investigation' | 'compare' | 'rank' | 'gaps' | 'prediction' | 'lab' | 'similar' | 'pattern' | 'quality' | 'earth' | 'overview'

type Props = {
  kind: VoiceKind
  /** What the page is showing, in the names the page's own request uses. */
  params: Record<string, unknown>
  label?: string
}

/** A button that explains what is on the page out loud. The listener can interrupt and ask questions. */
export function VoiceGuide({ kind, params, label = 'Explain this' }: Props) {
  const [open, setOpen] = useState(false)
  return (
    <>
      <button type="button" className="voice-button" aria-haspopup="dialog" aria-expanded={open} onClick={() => setOpen(true)}>
        <img src={icon} alt="" width={26} height={26} />
        {label}
      </button>
      {open &&
        createPortal(
          <Suspense fallback={null}>
            <VoicePanel kind={kind} params={params} onClose={() => setOpen(false)} />
          </Suspense>,
          document.body,
        )}
    </>
  )
}
