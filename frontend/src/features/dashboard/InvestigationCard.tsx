import { Link } from 'react-router-dom'
import { CONDITIONS, NOT_STATED, gravity, range, testCount } from './format.ts'
import type { Card } from './types.ts'

const ON_CARD = CONDITIONS.filter((c) => ['o2_mole_fraction', 'pressure_kpa', 'flow_cm_s'].includes(c.field))

export function InvestigationCard({ card }: { card: Card }) {
  const moreFuels = card.fuel_count - card.fuels.length
  const hasTable = card.test_rows + card.summary_rows > 0
  return (
    <article className={`card pillar-${card.pillar}`}>
      <h3>
        <Link to={`/dashboard/${card.psi_id}`}>{card.name}</Link>
      </h3>
      <p className="tags">
        <span>{card.fuel_class ?? 'no fuel class'}</span>
        <span>{gravity(card)}</span>
        <span>{card.psi_id}</span>
      </p>
      {card.objective_short && <p className="objective">{card.objective_short}</p>}
      <dl>
        <dt>Tests</dt>
        <dd>{testCount(card)}</dd>
        {hasTable && (
          <>
            <dt>Fuel</dt>
            <dd>
              {card.fuels.length ? card.fuels.join(', ') : NOT_STATED}
              {moreFuels > 0 && ` and ${moreFuels} more`}
            </dd>
            {ON_CARD.map((c) => (
              <div key={c.field} className="pair">
                <dt>{c.label}</dt>
                <dd className={card.conditions[c.field] ? '' : 'missing'}>{range(card.conditions[c.field], c.scale, c.unit)}</dd>
              </div>
            ))}
          </>
        )}
      </dl>
      <p className="foot">
        {card.flag_count > 0 && <span className="flagged">{card.flag_count} flagged cells</span>}
        {card.doi && (
          <a href={`https://doi.org/${card.doi}`} target="_blank" rel="noreferrer">
            DOI
          </a>
        )}
      </p>
    </article>
  )
}
