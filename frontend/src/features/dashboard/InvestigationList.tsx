import { useState } from 'react'
import { useTitle } from '../../useTitle.ts'
import { useApi } from '../../api/useApi.ts'
import { DashboardNav } from './DashboardNav.tsx'
import { InvestigationCard } from './InvestigationCard.tsx'
import { PILLAR_NAMES } from './format.ts'
import type { Listing } from './types.ts'

export function InvestigationList() {
  const { data, error } = useApi<Listing>('/investigations')
  const [fuelClass, setFuelClass] = useState('all')
  useTitle('Experiments')

  if (error) return <p role="alert">Could not load the investigations: {error}</p>
  if (!data) return <p className="loading">Loading…</p>

  const classes = ['all', ...new Set(data.investigations.flatMap((card) => (card.fuel_class ? [card.fuel_class] : [])))]
  const shown = data.investigations.filter((card) => fuelClass === 'all' || card.fuel_class === fuelClass)

  return (
    <section className="dashboard">
      <header className="hero">
        <p className="eyebrow">{data.investigations.length} NASA experiments</p>
        <h1>
          How fire burns <span className="dim">without gravity.</span>
        </h1>
        <DashboardNav />
      </header>
      <p className="filter">
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
            <p className="quiet">{pillar.description}</p>
            <div className="cards">
              {cards.map((card) => (
                <InvestigationCard key={card.psi_id} card={card} />
              ))}
            </div>
          </section>
        )
      })}

      <p className="quiet left-out">
        The four groups are ours, not NASA's. Left out:{' '}
        {data.left_out.map((item) => `${item.title} (${item.psi_id}). ${item.reason}`).join(' ')}
      </p>
    </section>
  )
}
