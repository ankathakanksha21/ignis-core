import { useEffect, useState } from 'react'
import { api } from '../../api/client.ts'
import { useLevel } from './level.ts'
import { LevelToggle } from './LevelToggle.tsx'
import { VoiceGuide } from './VoiceGuide.tsx'
import type { VoiceKind } from './VoiceGuide.tsx'
import './voice.css'

type Written = { script: string; highlights: string[]; written_by: 'model' | 'code' }

/**
 * A written explanation of what the page is showing, with a button to hear it and ask about it.
 * It is the same checked text the voice guide reads: built from facts that code computed.
 */
export function AiExplain({ kind, params, heading = 'What this shows', label }: { kind: VoiceKind; params: Record<string, unknown>; heading?: string; label?: string }) {
  const level = useLevel()
  const request = JSON.stringify({ kind, params, level, speak: false })
  const [found, setFound] = useState<{ request: string; written?: Written; error?: string } | null>(null)

  useEffect(() => {
    let live = true
    // A short wait, so stepping through a menu does not ask for an explanation of every option passed.
    const timer = setTimeout(() => {
      api<Written>('/voice/explain', JSON.parse(request)).then(
        (written) => live && setFound({ request, written }),
        (reason: Error) => live && setFound({ request, error: reason.message }),
      )
    }, 350)
    return () => {
      live = false
      clearTimeout(timer)
    }
  }, [request])

  const current = found?.request === request ? found : null
  return (
    <section className="ai-explain" aria-live="polite">
      <header>
        <h3>
          <span className="ai-tag">AI</span> {heading}
        </h3>
        <LevelToggle />
      </header>
      {!current && <p className="quiet">Writing the explanation…</p>}
      {current?.error && <p className="quiet">The explanation could not be written: {current.error}</p>}
      {current?.written && (
        <>
          <p>{current.written.script}</p>
          <ul className="voice-highlights">
            {current.written.highlights.map((text) => (
              <li key={text}>{text}</li>
            ))}
          </ul>
          <p className="voice-small">
            {current.written.written_by === 'model'
              ? 'A language model wrote this from facts that code computed from the data, and code checked every number in it.'
              : 'Code wrote this from facts it computed from the data.'}{' '}
            It can still be wrong, so check it against the page.
          </p>
        </>
      )}
      <VoiceGuide kind={kind} params={params} label={label ?? 'Listen and ask'} />
    </section>
  )
}
