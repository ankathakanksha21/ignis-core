import { Fragment } from 'react'
import { useTitle } from '../../useTitle.ts'
import { Link } from 'react-router-dom'
import { useApi } from '../../api/useApi.ts'
import { DashboardNav } from './DashboardNav.tsx'
import type { EarthPanel, Who } from './types.ts'

function Names({ people }: { people: Who[] }) {
  return people.map((who, index) => (
    <Fragment key={who.psi_id}>
      {index > 0 && ', '}
      <Link to={`/dashboard/${who.psi_id}`}>{who.name}</Link>
    </Fragment>
  ))
}

export function EarthPage() {
  const { data, error } = useApi<EarthPanel>('/investigations/earth')
  useTitle('On Earth')

  return (
    <section className="dashboard earth">
      <header className="hero">
        <p className="eyebrow">On Earth</p>
        <h1>
          What it does <span className="dim">on Earth.</span>
        </h1>
        <p className="lede">In NASA's own words. Each quote links to its source.</p>
        <DashboardNav />
      </header>
      {error && <p role="alert">Could not load the Earth uses: {error}</p>}
      {!data && !error && <p className="loading">Loading…</p>}

      {data && (
        <>
          <h2>From NASA's records</h2>
          <p className="quiet">Quoted from each record's "{data.field}" text. The themes are ours.</p>
          <div className="themes">
            {data.themes.map((theme) => (
              <section key={theme.id} className="theme reveal">
                <h3>{theme.label}</h3>
                {theme.quotes.map((quote) => (
                  <figure key={quote.text}>
                    <blockquote>“{quote.text}”</blockquote>
                    <figcaption>
                      <Names people={quote.investigations} />
                    </figcaption>
                  </figure>
                ))}
              </section>
            ))}
          </div>
          {data.not_quoted.length > 0 && (
            <p className="quiet">
              We found no specific Earth use in the records of <Names people={data.not_quoted} />.
            </p>
          )}

          <h2>Products from NASA's fire-safety work</h2>
          <p className="quiet">
            NASA does not tie these to any experiment above, so we do not either. Pages read on {data.spinoffs_checked}.
          </p>
          <div className="themes">
            {data.spinoffs.map((entry) => (
              <section key={entry.product} className="theme reveal">
                <h3>{entry.product}</h3>
                {entry.sources.map((source) => (
                  <figure key={source.url}>
                    {source.quotes.map((quote) => (
                      <blockquote key={quote}>“{quote}”</blockquote>
                    ))}
                    <figcaption>
                      <a href={source.url} target="_blank" rel="noreferrer">
                        {source.title}
                      </a>
                      , {source.publication}
                    </figcaption>
                  </figure>
                ))}
              </section>
            ))}
          </div>
        </>
      )}
    </section>
  )
}
