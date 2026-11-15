import { Link } from 'react-router-dom'
import { PILLAR_NAMES, range, testStat } from './format.ts'
import type { Card } from './types.ts'

/** A name, one line and two numbers. Everything else, and every source, is one click away. */
export function InvestigationCard({ card }: { card: Card }) {
  const tests = testStat(card)
  const oxygen = card.conditions.o2_mole_fraction
  const line = card.ai_summary?.one_line ?? card.objective_short
  return (
    <article className={`card reveal pillar-${card.pillar}`}>
      <p className="card-top">
        <span className="pillar-name">{PILLAR_NAMES[card.pillar]}</span>
        <span>{card.fuel_class ?? 'no fuel class'}</span>
        <span className="go" aria-hidden="true">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <path d="M7 17 17 7M9 7h8v8" />
          </svg>
        </span>
      </p>
      <h3>
        <Link to={`/dashboard/${card.psi_id}`}>{card.name}</Link>
      </h3>
      {line && (
        <p className="objective">
          {card.ai_summary && <span className="ai-tag">AI</span>} {line}
        </p>
      )}
      <dl className="stats">
        <div>
          <dd>{tests.value}</dd>
          <dt>{tests.label}</dt>
        </div>
        <div>
          <dd className={oxygen ? '' : 'missing'}>{range(oxygen, 100, '%')}</dd>
          <dt>oxygen</dt>
        </div>
      </dl>
    </article>
  )
}
