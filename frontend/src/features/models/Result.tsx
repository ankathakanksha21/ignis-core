import { Link } from 'react-router-dom'
import { label, pretty, shown, unit } from './inputs.ts'
import type { ModelCard, Prediction } from './types.ts'

const figure = (value: number) => String(Number(value.toPrecision(3)))

export function Result({ card, result }: { card: ModelCard; result: Prediction }) {
  const found = result.prediction
  const columns = result.nearest_tests.length ? Object.keys(result.nearest_tests[0].values) : []

  return (
    <div className="result">
      {result.status === 'ok' && found?.value != null && (
        <p className="headline">
          <strong>
            {figure(found.value)} {pretty(found.unit)}
          </strong>
          {found.low != null && found.high != null && (
            <span>
              {' '}
              likely between {figure(found.low)} and {figure(found.high)}
            </span>
          )}
        </p>
      )}
      {result.status === 'ok' && found?.class_probabilities && (
        <div className="classes">
          <p className="headline">
            {card.target}: <strong>{found.label}</strong>
          </p>
          {Object.entries(found.class_probabilities).map(([name, share]) => (
            <div key={name} className="class-row">
              <span>{name}</span>
              <div className="meter" title={`${Math.round(share * 100)} of 100`}>
                <div style={{ width: `${Math.round(share * 100)}%` }} />
              </div>
              <span>{Math.round(share * 100)}%</span>
            </div>
          ))}
        </div>
      )}
      {result.status === 'ok' && <p className="tag">{card.task === 'matcher' ? 'Real tests only. Nothing is predicted.' : 'Model prediction, not a measurement.'}</p>}

      {result.status === 'withheld' && (
        <div className="withheld">
          <p className="headline">
            <strong>No prediction.</strong> These conditions are outside what NASA tested.
          </p>
          <ul>
            {result.out_of_range.map((item) => (
              <li key={item.feature}>
                {label(item.feature)} of {typeof item.value === 'number' ? `${shown(item.feature, item.value)} ${unit({ name: item.feature })}` : item.value}
                {item.tested_min != null && item.tested_max != null
                  ? `: tested from ${shown(item.feature, item.tested_min)} to ${shown(item.feature, item.tested_max)} ${unit({ name: item.feature })}`
                  : item.categories
                    ? `: tested values are ${item.categories.join(', ')}`
                    : ''}
              </li>
            ))}
          </ul>
        </div>
      )}
      {result.status === 'invalid_input' && (
        <p className="headline">
          <strong>Something is missing.</strong>
        </p>
      )}
      {result.message && <p className="message">{result.message}</p>}

      {result.nearest_tests.length > 0 && (
        <>
          <h3>Nearest real tests</h3>
          <div className="scroll">
            <table>
              <thead>
                <tr>
                  <th>Test</th>
                  {columns.map((column) => (
                    <th key={column}>{column.trim()}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {result.nearest_tests.map((test) => (
                  <tr key={`${test.file_name}-${test.row}`}>
                    <td>
                      <Link to={`/dashboard/${test.psi_id}`}>{test.psi_id}</Link>, row {test.row}
                    </td>
                    {columns.map((column) => (
                      <td key={column}>{test.values[column] || <em>empty</em>}</td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <p className="quiet">Cells are shown as NASA published them.</p>
        </>
      )}
    </div>
  )
}
