import { Fragment } from 'react'
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

  return (
    <section className="dashboard earth">
      <p className="eyebrow">Earth applications</p>
      <h1>On Earth</h1>
      <DashboardNav />
      <p className="lede">What the research is for on the ground, in NASA's own words. Each quote links to where NASA says it.</p>
      {error && <p role="alert">Could not load the Earth uses: {error}</p>}
      {!data && !error && <p>Loading…</p>}

      {data && (
        <>
          <h2>What the investigation records say</h2>
          <p className="quiet">
            Quoted from the "{data.field}" text of each PSI record. The grouping into themes is this project's, not NASA's.
          </p>
          <div className="themes">
            {data.themes.map((theme) => (
              <section key={theme.id} className="theme">
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
              Nothing is quoted from <Names people={data.not_quoted} />. This project found no specific Earth use named in
              their records. Open one to read its full text.
            </p>
          )}

          <h2>NASA products the challenge names</h2>
          <p className="quiet">
            These come from NASA's wider fire-safety work. The pages below tie none of them to a combustion investigation in
            PSI, so this tool does not link them either. Pages read on {data.spinoffs_checked}.
          </p>
          <div className="themes">
            {data.spinoffs.map((entry) => (
              <section key={entry.product} className="theme">
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
