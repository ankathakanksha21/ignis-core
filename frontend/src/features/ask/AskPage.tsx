import { useState } from 'react'
import type { FormEvent } from 'react'
import { Link } from 'react-router-dom'
import { api } from '../../api/client.ts'
import './ask.css'

type Evidence = { n: number; text: string; source: string; psi_id: string | null; name: string | null }

type Answer = {
  question: string
  sentences: { text: string; cites: number[] }[]
  not_covered: string | null
  dropped: number
  evidence: Evidence[]
  model: string
}

const EXAMPLES = [
  'Has any solid fuel been tested near 30% oxygen?',
  'Which investigations tested fire suppression, and with what gases?',
  'What do we know about combustion at Moon gravity?',
  'How did SAME measure smoke?',
]

export function AskPage() {
  const [question, setQuestion] = useState('')
  const [answer, setAnswer] = useState<Answer | null>(null)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [lit, setLit] = useState<number[]>([])

  const ask = (text: string) => {
    if (text.trim().length < 3 || busy) return
    setQuestion(text)
    setBusy(true)
    setError(null)
    api<Answer>('/qa/ask', { question: text }).then(
      (result) => (setAnswer(result), setBusy(false)),
      (reason: Error) => (setError(reason.message), setBusy(false)),
    )
  }
  const submit = (event: FormEvent) => {
    event.preventDefault()
    ask(question)
  }

  const cited = new Set(answer?.sentences.flatMap((s) => s.cites))
  const used = answer?.evidence.filter((item) => cited.has(item.n)) ?? []
  const unused = answer?.evidence.filter((item) => !cited.has(item.n)) ?? []
  // Each source keeps the number the answer cites it by.
  const source = (item: Answer['evidence'][number]) => (
    <li key={item.n} value={item.n} id={`source-${item.n}`} className={lit.includes(item.n) ? 'lit' : ''}>
      <p>{item.text}</p>
      <small>
        {item.source}
        {item.psi_id && (
          <>
            {' · '}
            <Link to={`/dashboard/${item.psi_id}`}>{item.name}</Link>
          </>
        )}
      </small>
    </li>
  )

  return (
    <section className="ask">
      <p className="eyebrow">Answers with citations</p>
      <h1>Ask the data</h1>
      <p className="lede">A language model answers from NASA's records only. Every sentence cites its source.</p>

      <form onSubmit={submit}>
        <input value={question} onChange={(event) => setQuestion(event.target.value)} placeholder="Ask a question" maxLength={400} aria-label="Question" />
        <button className="primary" disabled={busy || question.trim().length < 3}>
          {busy ? 'Reading…' : 'Ask'}
        </button>
      </form>
      <p className="examples">
        {EXAMPLES.map((example) => (
          <button key={example} onClick={() => ask(example)} disabled={busy}>
            {example}
          </button>
        ))}
      </p>

      {error && <p role="alert">{error.startsWith('503') ? 'The language model is not set up on this server. Add the key to .env.' : `Could not answer: ${error}`}</p>}

      {answer && !busy && (
        <>
          <div className="answer">
            <h2>{answer.question}</h2>
            {answer.sentences.map((sentence) => (
              <p key={sentence.text} onPointerEnter={() => setLit(sentence.cites)} onPointerLeave={() => setLit([])}>
                {sentence.text}{' '}
                {sentence.cites.map((n) => (
                  <a key={n} href={`#source-${n}`} className="cite">
                    {n}
                  </a>
                ))}
              </p>
            ))}
            {answer.not_covered && (
              <p className="not-covered">
                <strong>Not covered by the sources.</strong> {answer.not_covered}
              </p>
            )}
            {answer.dropped > 0 && (
              <p className="quiet">
                {answer.dropped} {answer.dropped === 1 ? 'sentence was' : 'sentences were'} removed: no source, or a number the source does not contain.
              </p>
            )}
            <p className="quiet">Written by {answer.model}. It can be wrong, so check it against the sources.</p>
          </div>

          {used.length > 0 && (
            <>
              <h2>Sources cited</h2>
              <ol className="sources">{used.map(source)}</ol>
            </>
          )}
          {unused.length > 0 && (
            <details>
              <summary>
                {unused.length} more {unused.length === 1 ? 'source' : 'sources'} the model was given but did not cite
              </summary>
              <ol className="sources">{unused.map(source)}</ol>
            </details>
          )}
        </>
      )}
    </section>
  )
}
