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
import { useLevel } from './level.ts'
import { LevelToggle } from './LevelToggle.tsx'
import type { VoiceKind } from './VoiceGuide.tsx'
import { VoiceOrb } from './VoiceOrb.tsx'

// Shape returned by /api/voice/explain (backend/app/voice.py).
type Brief = {
  title: string
  script: string
  highlights: string[]
  facts: string[]
  written_by: 'model' | 'code'
  /** Questions worth asking about this page, offered as buttons. */
  questions: string[]
  /** Who the wording is for, passed on to the agent. */
  audience: string
  voice: { token: string } | null
  voice_note: string | null
}

// unchecked: numbers the guide said that are not among the page's facts.
type Line = { role: 'agent' | 'user'; text: string; unchecked: string[] }

const NUMBER = /\d+(?:\.\d+)?/g
const INTERRUPT = 'Stop there. I have a question.'
const flat = (text: string) => text.replace(/\s+/g, ' ').trim()

function Chips({ questions, onPick, disabled }: { questions: string[]; onPick: (question: string) => void; disabled: boolean }) {
  if (!questions?.length) return null
  return (
    <p className="voice-chips">
      {questions.map((question) => (
        <button key={question} type="button" disabled={disabled} onClick={() => onPick(question)}>
          {question}
        </button>
      ))}
    </p>
  )
}

/** The ElevenLabs conversation: it speaks the script first, and the listener can cut in at any point. */
function Talk({ brief, token, onFail, onAsk }: { brief: Brief; token: string; onFail: (why: string) => void; onAsk: (text: string) => void }) {
  const { startSession, endSession, sendUserMessage, sendUserActivity, getInputByteFrequencyData, getOutputByteFrequencyData } =
    useConversationControls()
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
        if (live) onFail('The microphone is blocked, so the browser reads this aloud and questions are typed. Allow the microphone and reopen to talk.')
        return
      }
      if (!live) return
      begun.current = true
      try {
        await startSession({
          conversationToken: token,
          dynamicVariables: { narration: brief.script, page: `${brief.title}. ${brief.audience}`, facts: brief.facts.join('\n') },
        })
      } catch {
        if (live) onFail('The voice did not connect, so the browser reads this aloud and questions are typed.')
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

  const connected = status === 'connected'
  const ask = (text: string) => {
    if (!text || !connected) return
    sendUserMessage(text)
    onAsk(text)
  }
  const send = (event: FormEvent) => {
    event.preventDefault()
    ask(typed.trim())
    setTyped('')
  }
  // A sure way to cut in, for when the microphone does not pick the listener up over the speakers.
  const interrupt = () => ask(INTERRUPT)
  return (
    <>
      <div className="voice-status">
        {/* The ring follows the guide's voice while it speaks, and the microphone while it listens. */}
        <VoiceOrb
          state={!connected ? 'idle' : isSpeaking ? 'speaking' : 'listening'}
          read={isSpeaking ? getOutputByteFrequencyData : isMuted ? undefined : getInputByteFrequencyData}
        />
        <p aria-live="polite">
          {!connected ? 'Connecting…' : isSpeaking ? 'Speaking. Talk over it, or press Interrupt.' : isMuted ? 'Microphone off. Type a question below.' : 'Listening. Ask a question.'}
        </p>
        {connected && isSpeaking && (
          <button type="button" className="primary" onClick={interrupt}>
            Interrupt
          </button>
        )}
      </div>
      <form className="voice-ask" onSubmit={send}>
        <input
          value={typed}
          onChange={(event) => {
            setTyped(event.target.value)
            sendUserActivity() // typing holds the voice back for a moment
          }}
          placeholder="Or type a question"
          aria-label="Question"
          disabled={!connected}
        />
        <button type="submit" disabled={!connected || !typed.trim()}>
          Ask
        </button>
        <button type="button" onClick={() => setMuted(!isMuted)} disabled={!connected} aria-pressed={isMuted}>
          {isMuted ? 'Unmute' : 'Mute'}
        </button>
      </form>
      <Chips questions={brief.questions} onPick={ask} disabled={!connected} />
    </>
  )
}

/**
 * The browser's own voice. It reads the script, and the listener can stop it at
 * any point and type a question, which the server answers from the page's facts.
 */
function Read({ brief, note, onAsk }: { brief: Brief; note: string | null; onAsk: (question: string) => Promise<string> }) {
  const [speaking, setSpeaking] = useState(false)
  const [typed, setTyped] = useState('')
  const [busy, setBusy] = useState(false)
  const [failed, setFailed] = useState<string | null>(null)
  const able = typeof window !== 'undefined' && 'speechSynthesis' in window

  const speak = (text: string = brief.script) => {
    if (!able) return
    window.speechSynthesis.cancel()
    const words = new SpeechSynthesisUtterance(text)
    words.onend = () => setSpeaking(false)
    words.onerror = () => setSpeaking(false)
    window.speechSynthesis.speak(words)
    setSpeaking(true)
  }
  const stop = () => {
    if (able) window.speechSynthesis.cancel()
    setSpeaking(false)
  }
  const ask = async (question: string) => {
    if (!question || busy) return
    stop()
    setTyped('')
    setFailed(null)
    setBusy(true)
    try {
      speak(await onAsk(question))
    } catch (reason) {
      setFailed(
        (reason as Error).message.startsWith('503')
          ? 'Questions need the language model key on the server.'
          : 'Could not get an answer. Try again.',
      )
    } finally {
      setBusy(false)
    }
  }
  const send = (event: FormEvent) => {
    event.preventDefault()
    void ask(typed.trim())
  }

  useEffect(() => {
    const timer = setTimeout(() => speak(), 0)
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
        <VoiceOrb state={busy ? 'listening' : speaking ? 'speaking' : 'idle'} />
        <p aria-live="polite">
          {busy ? 'Finding the answer…' : !able ? 'This browser cannot read aloud. The text is below.' : speaking ? 'Reading aloud. Press Interrupt to ask something.' : 'Ask a question below.'}
        </p>
        {able && (
          <button type="button" className={speaking ? 'primary' : ''} onClick={() => (speaking ? stop() : speak())}>
            {speaking ? 'Interrupt' : 'Replay'}
          </button>
        )}
      </div>
      <form className="voice-ask" onSubmit={send}>
        <input value={typed} onFocus={stop} onChange={(event) => setTyped(event.target.value)} placeholder="Type a question" aria-label="Question" />
        <button type="submit" disabled={busy || !typed.trim()}>
          Ask
        </button>
      </form>
      <Chips questions={brief.questions} onPick={(question) => void ask(question)} disabled={busy} />
      {failed && <p role="alert">{failed}</p>}
      {note && <p className="voice-note">{note}</p>}
    </>
  )
}

export default function VoicePanel({ kind, params, onClose }: { kind: VoiceKind; params: Record<string, unknown>; onClose: () => void }) {
  const level = useLevel()
  const request = JSON.stringify({ kind, params, level })
  const [loaded, setBrief] = useState<{ request: string; brief: Brief } | null>(null)
  const brief = loaded?.request === request ? loaded.brief : null
  const [error, setError] = useState<string | null>(null)
  const [heard, setHeard] = useState<Line[]>([])
  const [fallback, setFallback] = useState<string | null>(null)
  const end = useRef<HTMLLIElement>(null)

  useEffect(() => {
    let live = true
    api<Brief>('/voice/explain', JSON.parse(request)).then(
      (found) => live && (setBrief({ request, brief: found }), setHeard([]), setError(null)),
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
    setHeard((before) => {
      const last = before[before.length - 1]
      if (last && last.role === role && last.text === said) return before
      // A number the listener said themself may be repeated back, so those count as known too.
      const asked = new Set(before.filter((line) => line.role === 'user').flatMap((line) => line.text.match(NUMBER) ?? []))
      const numbers = role === 'agent' ? [...new Set(said.match(NUMBER) ?? [])] : []
      return [...before, { role, text: said, unchecked: numbers.filter((number) => !known.has(number) && !asked.has(number)) }]
    })
  }

  // A typed question, answered by the server from the same facts and checked there before it is read aloud.
  const askTyped = async (question: string) => {
    add('user', question)
    const history = heard.slice(-8).map(({ role, text }) => ({ role, text: text.slice(0, 1200) }))
    const reply = await api<{ text: string }>('/voice/answer', { ...JSON.parse(request), question, history })
    add('agent', reply.text)
    return reply.text
  }

  return (
    <aside className="voice-panel" role="dialog" aria-label="Voice guide">
      <header>
        <div>
          <p className="voice-eyebrow">Voice guide</p>
          <h2>{brief?.title ?? 'Preparing the explanation…'}</h2>
          <LevelToggle />
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
              key={brief.script}
              onMessage={(payload) => add(payload.role === 'user' ? 'user' : 'agent', payload.message)}
              onError={() => setFallback('The voice connection failed, so the browser reads this aloud and questions are typed.')}
            >
              <Talk brief={brief} token={brief.voice.token} onFail={setFallback} onAsk={(text) => add('user', text)} />
            </ConversationProvider>
          ) : (
            <Read key={brief.script} brief={brief} note={fallback ?? brief.voice_note} onAsk={askTyped} />
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
