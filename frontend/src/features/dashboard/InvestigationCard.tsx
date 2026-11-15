import { Link } from 'react-router-dom'
import { PILLAR_NAMES, gravity, range, testStat } from './format.ts'
import type { Card } from './types.ts'

/** The few facts worth a glance. Everything else, and every source, is one click away on the detail page. */
export function InvestigationCard({ card }: { card: Card }) {
  const tests = testStat(card)
  const oxygen = card.conditions.o2_mole_fraction
  const line = card.ai_summary?.one_line ?? card.objective_short
  return (
    <article className={`card pillar-${card.pillar}`}>
      <p className="card-top">
        <span className="pillar-name">{PILLAR_NAMES[card.pillar]}</span>
        <span>{card.psi_id}</span>
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
      <p className="foot">
        <span>
          {card.fuel_class ?? 'no fuel class'} · {gravity(card)}
        </span>
        {card.flag_count > 0 && (
          <span className="flagged" title="Cells this project flagged as suspect">
            {card.flag_count} flagged
          </span>
        )}
      </p>
    </article>
  )
}
