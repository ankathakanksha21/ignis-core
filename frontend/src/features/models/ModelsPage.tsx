import { useEffect, useState } from 'react'
import { Link, useSearchParams } from 'react-router-dom'
import { api } from '../../api/client.ts'
import { useApi } from '../../api/useApi.ts'
import { EXAMPLES, defaults, label, pretty, shown, toRequest, unit } from './inputs.ts'
import type { Inputs } from './inputs.ts'
import { Result } from './Result.tsx'
import type { ModelCard, Prediction } from './types.ts'
import './models.css'

const figure = (value: number) => String(Number(value.toPrecision(3)))

function Panel({ card }: { card: ModelCard }) {
  const [inputs, setInputs] = useState<Inputs>(() => EXAMPLES[card.model_id]?.[0].inputs ?? defaults(card.features))
  const [result, setResult] = useState<Prediction | null>(null)
  const [error, setError] = useState<string | null>(null)
  const request = JSON.stringify(toRequest(card.features, inputs))

  useEffect(() => {
    let live = true
    api<Prediction>('/predict', { model_id: card.model_id, inputs: JSON.parse(request) }).then(
      (found) => live && (setResult(found), setError(null)),
      (reason: Error) => live && setError(reason.message),
    )
    return () => {
      live = false
    }
  }, [card.model_id, request])

  return (
    <div className="panel">
      <div className="inputs">
        <h2>Conditions</h2>
        {EXAMPLES[card.model_id] && (
          <p className="examples">
            {EXAMPLES[card.model_id].map((example) => (
              <button key={example.name} onClick={() => setInputs(example.inputs)}>
                {example.name}
              </button>
            ))}
          </p>
        )}
        {card.features.map((feature) => (
          <label key={feature.name}>
            <span>{label(feature.name)}</span>
            {feature.kind === 'categorical' ? (
              <select value={inputs[feature.name] ?? ''} onChange={(event) => setInputs({ ...inputs, [feature.name]: event.target.value })}>
                {feature.categories?.map((name) => <option key={name}>{name}</option>)}
              </select>
            ) : (
              <>
                <input type="number" step="any" value={inputs[feature.name] ?? ''} onChange={(event) => setInputs({ ...inputs, [feature.name]: event.target.value })} />
                <span className="unit">{unit(feature)}</span>
                {feature.tested_min != null && feature.tested_max != null && (
                  <small>
                    tested {shown(feature.name, feature.tested_min)} to {shown(feature.name, feature.tested_max)}
                  </small>
                )}
              </>
            )}
          </label>
        ))}
        <p className="quiet">You can enter values outside the tested range. The model will say so and give no prediction.</p>
      </div>

      <div>
        <h2>Result</h2>
        {error && <p role="alert">Could not reach the model: {error}</p>}
        {result && <Result card={card} result={result} />}
      </div>
    </div>
  )
}

function About({ card }: { card: ModelCard }) {
  return (
    <details className="about">
      <summary>How this model was built and scored</summary>
      {card.trained_on.map((table) => (
        <p key={table.file_name}>
          Built on {table.n_rows} rows of <Link to={`/dashboard/${table.psi_id}`}>{table.psi_id}</Link>, {table.file_name}
          {table.doi && (
            <>
              {' '}
              (<a href={`https://doi.org/${table.doi}`} target="_blank" rel="noreferrer">doi:{table.doi}</a>)
            </>
          )}
          .
        </p>
      ))}
      {card.evaluation.length > 0 && (
        <table>
          <thead>
            <tr>
              <th>Score</th>
              <th>Model</th>
              <th>Baseline</th>
            </tr>
          </thead>
          <tbody>
            {card.evaluation.map((metric) => (
              <tr key={metric.name}>
                <td>{metric.name.replaceAll('_', ' ')}</td>
                <td>{figure(metric.value)}</td>
                <td>{metric.baseline_value == null ? '' : `${figure(metric.baseline_value)} (${metric.baseline_name})`}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
      {card.cv_scheme && <p>Scored by: {card.cv_scheme}</p>}
      {card.notes && <p>{card.notes}</p>}
    </details>
  )
}

export function ModelsPage() {
  const { data: cards, error } = useApi<ModelCard[]>('/models')
  const [params, setParams] = useSearchParams()

  if (error) return <p role="alert">Could not reach the backend: {error}</p>
  if (!cards) return <p>Loading…</p>
  const built = cards.filter((card) => card.status === 'available')
  const chosen = built.find((card) => card.model_id === params.get('model')) ?? built[0]

  return (
    <section className="models">
      <h1>Predictive models</h1>
      <p className="lede">
        One model per fuel class, each trained on a single NASA test table. A model answers only inside the conditions NASA tested, and
        shows the real tests nearest to what you asked.
      </p>

      <div className="model-list">
        {cards.map((card) => (
          <button key={card.model_id} className={card === chosen ? 'on' : ''} disabled={card.status !== 'available'} onClick={() => setParams({ model: card.model_id }, { replace: true })}>
            <strong>{card.title}</strong>
            <span>
              {card.fuel_class}, {card.task === 'matcher' ? 'finds real tests' : card.task}
            </span>
            {card.status !== 'available' && <em>{card.notes ?? 'Not built yet.'}</em>}
          </button>
        ))}
      </div>

      {chosen ? (
        <>
          <p>
            <strong>{chosen.title}.</strong> {chosen.task === 'matcher' ? 'Finds' : 'Predicts'} {chosen.target}
            {chosen.target_unit && ` in ${pretty(chosen.target_unit)}`}.
          </p>
          <Panel key={chosen.model_id} card={chosen} />
          <About card={chosen} />
        </>
      ) : (
        <p>No model is built yet.</p>
      )}
    </section>
  )
}
