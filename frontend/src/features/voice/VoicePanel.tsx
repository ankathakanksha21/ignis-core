import { useEffect, useRef, useState } from 'react'
import type { FormEvent } from 'react'
import {
  ConversationProvider,
  useConversationControls,
  useConversationInput,
  useConversationMode,
  useConversationStatus,
} from '@elevenlabs/react'
import { api } from '../../api/client.ts'
import icon from '../../assets/voice-guide.webp'
import type { VoiceKind } from './VoiceGuide.tsx'

// Shape returned by /api/voice/explain (backend/app/voice.py).
type Brief = {
  title: string
  script: string
  highlights: string[]
  facts: string[]
  written_by: 'model' | 'code'
  voice: { token: string } | null
  voice_note: string | null
}

// unchecked: numbers the guide said that are not among the page's facts.
type Line = { role: 'agent' | 'user'; text: string; unchecked: string[] }

const NUMBER = /\d+(?:\.\d+)?/g
const flat = (text: string) => text.replace(/\s+/g, ' ').trim()

function Orb({ state }: { state: 'idle' | 'speaking' | 'listening' }) {
  return (
    <span className={`voice-orb ${state}`}>
      <img src={icon} alt="" width={56} height={56} />
    </span>
  )
}

/** The ElevenLabs conversation: it speaks the script first, and the listener can cut in at any point. */
function Talk({ brief, token, onFail, onAsk }: { brief: Brief; token: string; onFail: (why: string) => void; onAsk: (text: string) => void }) {
  const { startSession, endSession, sendUserMessage } = useConversationControls()
  const { status } = useConversationStatus()
  const { isSpeaking } = useConversationMode()
  const { isMuted, setMuted } = useConversationInput()
  const [typed, setTyped] = useState('')
  const begun = useRef(false)

  useEffect(() => {
    let live = true
    // Deferred by a tick, so React's throwaway development mount never opens a conversation.
    const timer = setTimeout(async () => {
      try {
        const probe = await navigator.mediaDevices.getUserMedia({ audio: true })
        probe.getTracks().forEach((track) => track.stop())
      } catch {
        if (live) onFail('The microphone is blocked, so the browser reads this aloud and cannot answer questions. Allow the microphone and reopen to talk.')
        return
      }
      if (!live) return
      begun.current = true
      try {
        await startSession({
          conversationToken: token,
          dynamicVariables: { narration: brief.script, page: brief.title, facts: brief.facts.join('\n') },
        })
      } catch {
        if (live) onFail('The voice did not connect, so the browser reads this aloud and cannot answer questions.')
      }
    }, 0)
    return () => {
      live = false
      clearTimeout(timer)
      if (begun.current) Promise.resolve(endSession()).catch(() => undefined)
    }
    // Runs once for this panel: the brief and the token never change while it is open.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  const send = (event: FormEvent) => {
    event.preventDefault()
    const text = typed.trim()
    if (!text || status !== 'connected') return
    sendUserMessage(text)
    onAsk(text)
    setTyped('')
  }

  const connected = status === 'connected'
  return (
    <>
      <div className="voice-status">
        <Orb state={!connected ? 'idle' : isSpeaking ? 'speaking' : 'listening'} />
        <p aria-live="polite">
          {!connected ? 'Connecting…' : isSpeaking ? 'Speaking. Start talking to interrupt.' : isMuted ? 'Microphone off. Type a question below.' : 'Listening. Ask a question.'}
        </p>
      </div>
      <form className="voice-ask" onSubmit={send}>
        <input value={typed} onChange={(event) => setTyped(event.target.value)} placeholder="Or type a question" aria-label="Question" disabled={!connected} />
        <button type="submit" disabled={!connected || !typed.trim()}>
          Ask
        </button>
        <button type="button" onClick={() => setMuted(!isMuted)} disabled={!connected} aria-pressed={isMuted}>
          {isMuted ? 'Unmute' : 'Mute'}
        </button>
      </form>
    </>
  )
}

/** The browser's own voice: it reads the script and cannot answer. */
function Read({ brief, note }: { brief: Brief; note: string | null }) {
  const [speaking, setSpeaking] = useState(false)
  const able = typeof window !== 'undefined' && 'speechSynthesis' in window

  const speak = () => {
    if (!able) return
    window.speechSynthesis.cancel()
    const words = new SpeechSynthesisUtterance(brief.script)
    words.onend = () => setSpeaking(false)
    words.onerror = () => setSpeaking(false)
    window.speechSynthesis.speak(words)
    setSpeaking(true)
  }
  const stop = () => {
    window.speechSynthesis.cancel()
    setSpeaking(false)
  }

  useEffect(() => {
    const timer = setTimeout(speak, 0)
    return () => {
      clearTimeout(timer)
      if (able) window.speechSynthesis.cancel()
    }
    // Reads once when the panel opens.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  return (
    <>
      <div className="voice-status">
        <Orb state={speaking ? 'speaking' : 'idle'} />
        <p aria-live="polite">{!able ? 'This browser cannot read aloud. The explanation is below.' : speaking ? 'Reading aloud.' : 'Finished.'}</p>
        {able && (
          <button type="button" onClick={speaking ? stop : speak}>
            {speaking ? 'Stop' : 'Replay'}
          </button>
        )}
      </div>
      {note && <p className="voice-note">{note}</p>}
    </>
  )
}

export default function VoicePanel({ kind, params, onClose }: { kind: VoiceKind; params: Record<string, unknown>; onClose: () => void }) {
  const request = JSON.stringify({ kind, params })
  const [brief, setBrief] = useState<Brief | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [heard, setHeard] = useState<Line[]>([])
  const [fallback, setFallback] = useState<string | null>(null)
  const end = useRef<HTMLLIElement>(null)

  useEffect(() => {
    let live = true
    api<Brief>('/voice/explain', JSON.parse(request)).then(
      (found) => live && setBrief(found),
      (reason: Error) => live && setError(reason.message),
    )
    return () => {
      live = false
    }
  }, [request])

  useEffect(() => {
    const close = (event: KeyboardEvent) => event.key === 'Escape' && onClose()
    window.addEventListener('keydown', close)
    return () => window.removeEventListener('keydown', close)
  }, [onClose])

  useEffect(() => {
    end.current?.scrollIntoView({ block: 'nearest' })
  }, [heard.length])

  // Every number the guide may say: the ones in the page's facts and in the checked script.
  const known = new Set(brief ? [...brief.facts, brief.script, ...brief.highlights].join(' ').match(NUMBER) : [])
  const add = (role: Line['role'], text: string) => {
    const said = flat(text)
    if (!said || (brief && role === 'agent' && said === flat(brief.script))) return // the script is already shown
    const unchecked = role === 'agent' ? [...new Set(said.match(NUMBER) ?? [])].filter((number) => !known.has(number)) : []
    setHeard((before) => {
      const last = before[before.length - 1]
      return last && last.role === role && last.text === said ? before : [...before, { role, text: said, unchecked }]
    })
  }

  return (
    <aside className="voice-panel" role="dialog" aria-label="Voice guide">
      <header>
        <div>
          <p className="voice-eyebrow">Voice guide</p>
          <h2>{brief?.title ?? 'Preparing the explanation…'}</h2>
        </div>
        <button type="button" onClick={onClose} aria-label="Close the voice guide">
          Close
        </button>
      </header>

      {error && <p role="alert">Could not prepare the explanation: {error}</p>}
      {brief && (
        <>
          {brief.voice && !fallback ? (
            <ConversationProvider
              onMessage={(payload) => add(payload.role === 'user' ? 'user' : 'agent', payload.message)}
              onError={() => setFallback('The voice connection failed, so the browser reads this aloud and cannot answer questions.')}
            >
              <Talk brief={brief} token={brief.voice.token} onFail={setFallback} onAsk={(text) => add('user', text)} />
            </ConversationProvider>
          ) : (
            <Read brief={brief} note={fallback ?? brief.voice_note} />
          )}

          <ul className="voice-highlights">
            {brief.highlights.map((text) => (
              <li key={text}>{text}</li>
            ))}
          </ul>

          <ol className="voice-heard">
            <li className="agent">{brief.script}</li>
            {heard.map((line, index) => (
              <li key={index} className={line.role}>
                {line.text}
                {line.unchecked.length > 0 && (
                  <small>
                    Not checked: {line.unchecked.join(', ')} {line.unchecked.length === 1 ? 'is' : 'are'} not among the facts for this page.
                    Trust the page over the voice.
                  </small>
                )}
              </li>
            ))}
            <li ref={end} aria-hidden="true" />
          </ol>

          <details className="voice-facts">
            <summary>The {brief.facts.length} facts this is built from</summary>
            <ul>
              {brief.facts.map((text) => (
                <li key={text}>{text}</li>
              ))}
            </ul>
          </details>
          <p className="voice-small">
            {brief.written_by === 'model'
              ? 'A language model wrote the explanation from these facts, and code checked every number in it.'
              : 'Code wrote the explanation from these facts.'}{' '}
            Answers to your questions are spoken live and are checked only as they appear here.
          </p>
        </>
      )}
    </aside>
  )
}
