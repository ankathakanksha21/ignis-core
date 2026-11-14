import { useEffect, useState } from 'react'
import { api } from '../../api/client.ts'

// The fields of ModelCard (ml/src/ignis_ml/contract.py) this page uses.
type ModelCard = {
  model_id: string
  title: string
  status: 'available' | 'not_implemented'
  fuel_class: string
  task: string
  target: string
}

export function ModelsPage() {
  const [cards, setCards] = useState<ModelCard[] | null>(null)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    api<ModelCard[]>('/models').then(setCards, (reason: Error) => setError(reason.message))
  }, [])

  return (
    <section>
      <h1>Predictive models</h1>
      <p>Feature 6.3. This list comes live from the backend, which asks the ignis_ml package.</p>
      {error && <p role="alert">Could not reach the backend: {error}</p>}
      {cards && (
        <ul>
          {cards.map((card) => (
            <li key={card.model_id}>
              <strong>{card.title}</strong> ({card.fuel_class}, {card.task}, target: {card.target}):{' '}
              {card.status === 'available' ? 'available' : 'not built yet'}
            </li>
          ))}
        </ul>
      )}
    </section>
  )
}
