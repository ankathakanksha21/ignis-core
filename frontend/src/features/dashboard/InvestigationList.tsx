import { useState } from 'react'
import { useApi } from '../../api/useApi.ts'
import { DashboardNav } from './DashboardNav.tsx'
import { InvestigationCard } from './InvestigationCard.tsx'
import { PILLAR_NAMES } from './format.ts'
import type { Listing } from './types.ts'

export function InvestigationList() {
  const { data, error } = useApi<Listing>('/investigations')
  const [fuelClass, setFuelClass] = useState('all')

  if (error) return <p role="alert">Could not load the investigations: {error}</p>
  if (!data) return <p>Loading…</p>

  const classes = ['all', ...new Set(data.investigations.flatMap((card) => (card.fuel_class ? [card.fuel_class] : [])))]
  const shown = data.investigations.filter((card) => fuelClass === 'all' || card.fuel_class === fuelClass)

  return (
    <section className="dashboard">
      <h1>Combustion investigations</h1>
      <DashboardNav />
      <p className="lede">
        {data.investigations.length} investigations from NASA's PSI repository, grouped by fire safety pillar. The grouping is this
        project's, not NASA's. Open one to see where each value comes from.
      </p>
      <p className="filter">
        Fuel class:{' '}
        {classes.map((name) => (
          <button key={name} className={name === fuelClass ? 'on' : ''} onClick={() => setFuelClass(name)}>
            {name}
          </button>
        ))}
      </p>

      {data.pillars.map((pillar) => {
        const cards = shown.filter((card) => card.pillar === pillar.id)
        if (!cards.length) return null
        return (
          <section key={pillar.id} className="pillar">
            <h2>
              {PILLAR_NAMES[pillar.id] ?? pillar.id} <small>{cards.length}</small>
            </h2>
            <p>{pillar.description}</p>
            <div className="cards">
              {cards.map((card) => (
                <InvestigationCard key={card.psi_id} card={card} />
              ))}
            </div>
          </section>
        )
      })}

      <p className="left-out">
        Left out of the PSI search results:{' '}
        {data.left_out.map((item) => `${item.title} (${item.psi_id}). ${item.reason}`).join(' ')}
      </p>
    </section>
  )
}
