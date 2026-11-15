import { Link, useParams } from 'react-router-dom'
import { useApi } from '../../api/useApi.ts'
import { CONDITIONS, NOT_STATED, PILLAR_NAMES, gravity, range, testStat } from './format.ts'
import type { Detail, Table } from './types.ts'

const HEADLINE = CONDITIONS.filter((c) => ['o2_mole_fraction', 'pressure_kpa'].includes(c.field))

function Conditions({ table }: { table: Table }) {
  return (
    <table>
      <thead>
        <tr>
          <th>Condition</th>
          <th>Range</th>
          <th>Rows stating it</th>
          <th>Read from column</th>
        </tr>
      </thead>
      <tbody>
        {CONDITIONS.filter((c) => table.fields[c.field]).map((c) => {
          const source = table.fields[c.field]
          const found = source.min === null || source.max === null ? null : { min: source.min, max: source.max }
          return (
            <tr key={c.field}>
              <td>{c.label}</td>
              <td>{range(found, c.scale, c.unit)}</td>
              <td>{source.rows_with_value}</td>
              <td>
                <code>{source.source_column.trim()}</code> ({source.source_unit}){source.note && <small> {source.note}</small>}
              </td>
            </tr>
          )
        })}
      </tbody>
    </table>
  )
}

function Text({ title, text }: { title: string; text: string | null }) {
  if (!text) return null
  return (
    <details>
      <summary>{title}</summary>
      <p className="record-text">{text}</p>
    </details>
  )
}

export function InvestigationDetail() {
  const { psiId = '' } = useParams()
  const { data, error } = useApi<Detail>(`/investigations/${psiId}`)

  if (error) return <p role="alert">Could not load {psiId}: {error}</p>
  if (!data) return <p>Loading…</p>
  const tests = testStat(data)

  return (
    <section className={`detail pillar-${data.pillar}`}>
      <p className="back">
        <Link to="/dashboard">← All experiments</Link>
      </p>
      <p className="eyebrow">
        {PILLAR_NAMES[data.pillar]} · {data.psi_id}
      </p>
      <h1>{data.name}</h1>
      {data.title !== data.name && <p className="lede">{data.title}</p>}
      <p className="tags">
        <span>{data.fuel_class ?? 'no fuel class'}</span>
        <span>{gravity(data)}</span>
      </p>
      <dl className="stats tiles">
        <div>
          <dd>{tests.value}</dd>
          <dt>{tests.label}</dt>
        </div>
        {HEADLINE.map((c) => (
          <div key={c.field}>
            <dd className={data.conditions[c.field] ? '' : 'missing'}>{range(data.conditions[c.field], c.scale, c.unit)}</dd>
            <dt>{c.label.toLowerCase()}</dt>
          </div>
        ))}
        <div>
          <dd>{data.flag_count}</dd>
          <dt>flagged cells</dt>
        </div>
      </dl>
      <p className="quiet">
        Grouped under {PILLAR_NAMES[data.pillar]} by this project. {data.pillar_why}
        {data.brief_note && ` From the challenge brief: ${data.brief_note}`}
      </p>

      {data.ai_summary && (
        <section className="ai-summary reveal">
          <p>
            <span className="ai-tag">AI summary</span>
          </p>
          <p>{data.ai_summary.summary}</p>
          {data.ai_summary.measurements.length > 0 && (
            <>
              <h3>Instruments and measurements named in the record</h3>
              <ul>
                {data.ai_summary.measurements.map((item) => (
                  <li key={item.quote}>
                    {item.name} <q>{item.quote}</q>
                  </li>
                ))}
              </ul>
            </>
          )}
          <p className="quiet">
            Written by {data.ai_model} from this record and its test table only. Code checked every number and quote against
            them. It can still be wrong, so check it against the record below.
          </p>
        </section>
      )}

      <dl className="facts">
        <dt>Platform</dt>
        <dd>{data.platform ?? NOT_STATED}</dd>
        <dt>Hardware</dt>
        <dd>{data.hardware ?? NOT_STATED}</dd>
        {data.shares_hardware && (
          <>
            <dt>Shares hardware</dt>
            <dd>
              {data.shares_hardware.hardware}, with{' '}
              {data.shares_hardware.with.map((other, index) => (
                <span key={other.psi_id}>
                  {index > 0 && ', '}
                  <Link to={`/dashboard/${other.psi_id}`}>{other.name}</Link>
                </span>
              ))}
            </dd>
          </>
        )}
        {data.related.length > 0 && (
          <>
            <dt>Related in PSI</dt>
            <dd>
              {data.related.map((other, index) => (
                <span key={other.psi_id}>
                  {index > 0 && ', '}
                  <Link to={`/dashboard/${other.psi_id}`}>{other.name}</Link>
                </span>
              ))}
            </dd>
          </>
        )}
        <dt>Dates</dt>
        <dd>
          {data.start_date ?? NOT_STATED} to {data.end_date ?? NOT_STATED}
        </dd>
        <dt>Cite as</dt>
        <dd>
          {data.doi ? (
            <a href={`https://doi.org/${data.doi}`} target="_blank" rel="noreferrer">
              doi:{data.doi}
            </a>
          ) : (
            NOT_STATED
          )}
          {data.license && ` (${data.license})`}
        </dd>
      </dl>

      {data.tables.length === 0 && <p>This investigation has no experimental table in PSI.</p>}
      {data.tables.map((table) => {
        // Fewest values first: the deliberate test variables come before ids and timestamps.
        const varied = table.columns.filter((column) => column.distinct > 1).sort((a, b) => a.distinct - b.distinct)
        const fixed = table.columns.filter((column) => column.distinct === 1)
        return (
          <section key={table.file_name} className="table-block reveal">
            <h2>{table.file_name}</h2>
            <p>
              {Object.entries(table.rows)
                .map(([kind, count]) => `${count} ${kind} rows`)
                .join(', ')}
            </p>
            {Object.keys(table.fields).length > 0 ? (
              <div className="scroll">
              <Conditions table={table} />
            </div>
            ) : (
              <p className="missing">This table states no oxygen, pressure or flow.</p>
            )}
            <h3>
              What varied between tests <small>and how many values each took</small>
            </h3>
            {varied.length ? (
              <p className="tags varied">
                {varied.map((column) => (
                  <span key={column.name} title={`${column.distinct} different values`}>
                    {column.name.trim()} <b>{column.distinct}</b>
                  </span>
                ))}
              </p>
            ) : (
              <p>Nothing varied.</p>
            )}
            {fixed.length > 0 && <p className="quiet">Same in every row: {fixed.map((column) => column.name).join(', ')}</p>}
          </section>
        )
      })}

      {data.flags.length > 0 && (
        <section>
          <h2>Flagged cells</h2>
          <p className="quiet">Checks are this project's, not NASA's. The raw data is unchanged.</p>
          <div className="scroll">
          <table>
            <thead>
              <tr>
                <th>Row</th>
                <th>Column</th>
                <th>Check</th>
                <th>Why</th>
              </tr>
            </thead>
            <tbody>
              {data.flags.map((flag) => (
                <tr key={`${flag.file_name}-${flag.row}-${flag.column}-${flag.check}`}>
                  <td>{flag.row}</td>
                  <td>{flag.column.trim()}</td>
                  <td>{flag.check.replaceAll('_', ' ')}</td>
                  <td>{flag.detail}</td>
                </tr>
              ))}
            </tbody>
          </table>
          </div>
        </section>
      )}

      <h2>From the NASA record</h2>
      <Text title="Objective" text={data.objective} />
      <Text title="Approach" text={data.approach} />
      <Text title="Hypothesis" text={data.hypothesis} />
      <Text title="Research impacts and Earth benefits" text={data.research_impacts} />
      {data.publications.length > 0 && (
        <details>
          <summary>{data.publications.length} publications</summary>
          <ul>
            {data.publications.map((paper, index) => (
              <li key={index}>
                {paper.title ?? 'Untitled'}
                {paper.authors && `. ${paper.authors}`}
                {paper.doi && (
                  <>
                    {' '}
                    <a href={`https://doi.org/${paper.doi}`} target="_blank" rel="noreferrer">
                      doi
                    </a>
                  </>
                )}
              </li>
            ))}
          </ul>
        </details>
      )}
    </section>
  )
}
